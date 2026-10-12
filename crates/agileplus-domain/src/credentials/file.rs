use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::RwLock;

use aes_gcm::aead::{Aead, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Nonce};
use argon2::Argon2;
use rand::RngCore;

use super::error::CredentialError;
use super::store::CredentialStore;

const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 12;
type Salt = [u8; SALT_LEN];
type NonceBytes = [u8; NONCE_LEN];
type EncryptedPayload = (Salt, NonceBytes, Vec<u8>);
/// Env var that must contain the passphrase used to derive the AES-256 key
/// via Argon2id. If unset, credentials are stored as plaintext JSON for
/// backward compatibility.
const ENV_PASSPHRASE: &str = "AGILEPLUS_CREDENTIAL_PASSPHRASE";

/// Credential store backed by an AES-256-GCM encrypted JSON file.
///
/// The file is stored at `~/.agileplus/credentials.enc`.
/// Key derivation uses Argon2id from a passphrase supplied via the
/// `AGILEPLUS_CREDENTIAL_PASSPHRASE` environment variable.
/// File permissions are set to 0o600 on creation (Unix only).
///
/// When the passphrase env-var is unset the store falls back to plaintext
/// JSON (backward-compatible mode).
///
/// # Traceability: FR-030, FR-031 / WP15-T088
pub struct FileCredentialStore {
    path: PathBuf,
    /// In-memory cache (service -> key -> value), protected by a RwLock.
    cache: RwLock<HashMap<String, HashMap<String, String>>>,
    loaded: RwLock<bool>,
}

impl FileCredentialStore {
    pub fn new(path: &Path) -> Self {
        Self {
            path: path.to_owned(),
            cache: RwLock::new(HashMap::new()),
            loaded: RwLock::new(false),
        }
    }

    /// Return the raw passphrase from the environment, or `None` for
    /// plaintext fallback mode.
    fn passphrase() -> Option<String> {
        match std::env::var(ENV_PASSPHRASE) {
            Ok(v) if !v.is_empty() => Some(v),
            _ => None,
        }
    }

    /// Derive a 256-bit AES key from `passphrase` using Argon2id with the
    /// given `salt`.
    fn derive_key(passphrase: &[u8], salt: &[u8; SALT_LEN]) -> [u8; 32] {
        let mut key = [0u8; 32];
        Argon2::default()
            .hash_password_into(passphrase, salt, &mut key)
            .expect("Argon2id key derivation should not fail with valid params");
        key
    }

    /// Encrypt `plaintext` bytes with AES-256-GCM using a key derived from
    /// the passphrase env-var. Returns `(salt, nonce, ciphertext)`.
    fn encrypt(plaintext: &[u8]) -> Result<EncryptedPayload, CredentialError> {
        let passphrase = Self::passphrase().ok_or_else(|| {
            CredentialError::Encryption(format!("{ENV_PASSPHRASE} not set, cannot encrypt"))
        })?;

        let mut salt = [0u8; SALT_LEN];
        OsRng.fill_bytes(&mut salt);
        let key = Self::derive_key(passphrase.as_bytes(), &salt);

        let cipher = Aes256Gcm::new_from_slice(&key)
            .map_err(|e| CredentialError::Encryption(format!("AES-256-GCM init: {e}")))?;

        let mut nonce_bytes = [0u8; NONCE_LEN];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher
            .encrypt(nonce, plaintext)
            .map_err(|e| CredentialError::Encryption(format!("AES-256-GCM encrypt: {e}")))?;

        Ok((salt, nonce_bytes, ciphertext))
    }

    /// Decrypt `ciphertext` using the key derived from the passphrase env-var
    /// with the given `salt` and `nonce`.
    fn decrypt(
        ciphertext: &[u8],
        salt: &[u8; SALT_LEN],
        nonce: &[u8; NONCE_LEN],
    ) -> Result<Vec<u8>, CredentialError> {
        let passphrase = Self::passphrase().ok_or_else(|| {
            CredentialError::Encryption(format!("{ENV_PASSPHRASE} not set, cannot decrypt"))
        })?;

        let key = Self::derive_key(passphrase.as_bytes(), salt);

        let cipher = Aes256Gcm::new_from_slice(&key)
            .map_err(|e| CredentialError::Encryption(format!("AES-256-GCM init: {e}")))?;

        let nonce = Nonce::from_slice(nonce);

        let plaintext = cipher
            .decrypt(nonce, ciphertext)
            .map_err(|e| CredentialError::Encryption(format!("AES-256-GCM decrypt: {e}")))?;

        Ok(plaintext)
    }

    /// Detect whether the file on disk is encrypted (binary header) or
    /// plaintext JSON (starts with `{`).
    fn is_encrypted(data: &[u8]) -> bool {
        data.len() > SALT_LEN + NONCE_LEN && data[0] != b'{'
    }

    /// Load credentials from the encrypted file using AES-256-GCM.
    fn ensure_loaded(&self) -> Result<(), CredentialError> {
        {
            let loaded = self.loaded.read().unwrap();
            if *loaded {
                return Ok(());
            }
        }
        let mut loaded = self.loaded.write().unwrap();
        if *loaded {
            return Ok(());
        }
        if self.path.exists() {
            let raw = std::fs::read(&self.path)?;

            let map = if Self::is_encrypted(&raw) {
                // Encrypted format: salt || nonce || ciphertext
                if raw.len() < SALT_LEN + NONCE_LEN + 1 {
                    return Err(CredentialError::Serialization(
                        "credential file too short for encrypted format".into(),
                    ));
                }
                let mut salt = [0u8; SALT_LEN];
                let mut nonce = [0u8; NONCE_LEN];
                salt.copy_from_slice(&raw[..SALT_LEN]);
                nonce.copy_from_slice(&raw[SALT_LEN..SALT_LEN + NONCE_LEN]);
                let ciphertext = &raw[SALT_LEN + NONCE_LEN..];

                let plaintext = Self::decrypt(ciphertext, &salt, &nonce)?;
                serde_json::from_slice(&plaintext)
                    .map_err(|e| CredentialError::Serialization(e.to_string()))?
            } else {
                // Plaintext JSON (backward-compatible mode)
                let text = String::from_utf8(raw)
                    .map_err(|e| CredentialError::Serialization(format!("invalid UTF-8: {e}")))?;
                serde_json::from_str(&text)
                    .map_err(|e| CredentialError::Serialization(e.to_string()))?
            };

            *self.cache.write().unwrap() = map;
        }
        *loaded = true;
        Ok(())
    }

    fn persist(&self) -> Result<(), CredentialError> {
        if let Some(parent) = self.path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let cache = self.cache.read().unwrap();
        let raw = serde_json::to_vec(&*cache)
            .map_err(|e| CredentialError::Serialization(e.to_string()))?;

        let data: Vec<u8> = if let Some((salt, nonce, ciphertext)) = Self::try_encrypt(&raw)? {
            // Encrypted format: salt || nonce || ciphertext
            let mut buf = Vec::with_capacity(SALT_LEN + NONCE_LEN + ciphertext.len());
            buf.extend_from_slice(&salt);
            buf.extend_from_slice(&nonce);
            buf.extend_from_slice(&ciphertext);
            buf
        } else {
            raw
        };

        std::fs::write(&self.path, &data)?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let perms = std::fs::Permissions::from_mode(0o600);
            std::fs::set_permissions(&self.path, perms)?;
        }
        Ok(())
    }

    /// Encrypt raw bytes if a passphrase is configured. Returns `None` if
    /// the passphrase env-var is not set (plaintext mode).
    fn try_encrypt(raw: &[u8]) -> Result<Option<EncryptedPayload>, CredentialError> {
        if Self::passphrase().is_some() {
            let (salt, nonce, ciphertext) = Self::encrypt(raw)?;
            Ok(Some((salt, nonce, ciphertext)))
        } else {
            Ok(None)
        }
    }
}

impl CredentialStore for FileCredentialStore {
    fn get(&self, service: &str, key: &str) -> Result<String, CredentialError> {
        self.ensure_loaded()?;
        let cache = self.cache.read().unwrap();
        cache
            .get(service)
            .and_then(|m| m.get(key))
            .cloned()
            .ok_or_else(|| CredentialError::NotFound(key.to_string()))
    }

    fn set(&self, service: &str, key: &str, value: &str) -> Result<(), CredentialError> {
        self.ensure_loaded()?;
        {
            let mut cache = self.cache.write().unwrap();
            cache
                .entry(service.to_string())
                .or_default()
                .insert(key.to_string(), value.to_string());
        }
        self.persist()
    }

    fn delete(&self, service: &str, key: &str) -> Result<(), CredentialError> {
        self.ensure_loaded()?;
        {
            let mut cache = self.cache.write().unwrap();
            if let Some(svc) = cache.get_mut(service) {
                if svc.remove(key).is_none() {
                    return Err(CredentialError::NotFound(key.to_string()));
                }
            } else {
                return Err(CredentialError::NotFound(key.to_string()));
            }
        }
        self.persist()
    }

    fn list_keys(&self, service: &str) -> Result<Vec<String>, CredentialError> {
        self.ensure_loaded()?;
        let cache = self.cache.read().unwrap();
        Ok(cache
            .get(service)
            .map(|m| m.keys().cloned().collect())
            .unwrap_or_default())
    }
}

#[cfg(test)]
mod tests {
    use std::sync::{Mutex, OnceLock};

    use super::*;

    fn test_lock() -> &'static Mutex<()> {
        static TEST_LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        TEST_LOCK.get_or_init(|| Mutex::new(()))
    }

    fn with_env_override<F>(value: Option<&str>, f: F)
    where
        F: FnOnce(),
    {
        let _guard = test_lock().lock().unwrap();
        let previous = std::env::var(ENV_PASSPHRASE).ok();
        unsafe {
            // SAFETY: guarded by test_lock, so env access is serialized in this test module.
            match value {
                Some(passphrase) if !passphrase.is_empty() => {
                    std::env::set_var(ENV_PASSPHRASE, passphrase);
                },
                _ => {
                    std::env::remove_var(ENV_PASSPHRASE);
                },
            }
        }
        f();
        unsafe {
            match previous {
                Some(previous) => std::env::set_var(ENV_PASSPHRASE, previous),
                None => std::env::remove_var(ENV_PASSPHRASE),
            }
        }
    }

    /// Helper: set the passphrase env var for the duration of a test.
    fn with_passphrase<F>(passphrase: &str, f: F)
    where
        F: FnOnce(),
    {
        with_env_override(Some(passphrase), f);
    }

    fn with_plaintext_mode<F>(f: F)
    where
        F: FnOnce(),
    {
        with_env_override(None, f);
    }

    // ── Plaintext (no passphrase) tests ──────────────────────────────

    #[test]
    fn file_store_set_get_plaintext() {
        with_plaintext_mode(|| {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.json");
            let store = FileCredentialStore::new(&path);
            store.set("svc", "tok", "abc123").unwrap();
            assert!(path.exists());
            assert_eq!(store.get("svc", "tok").unwrap(), "abc123");
            // File should be plaintext JSON
            let content = std::fs::read_to_string(&path).unwrap();
            assert!(
                content.starts_with('{'),
                "expected plaintext JSON, got: {content:?}"
            );
        });
    }

    #[test]
    fn file_store_delete() {
        with_plaintext_mode(|| {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.json");
            let store = FileCredentialStore::new(&path);
            store.set("svc", "tok", "abc123").unwrap();
            store.delete("svc", "tok").unwrap();
            assert!(matches!(
                store.get("svc", "tok"),
                Err(CredentialError::NotFound(_))
            ));
        });
    }

    #[test]
    fn file_store_list_keys() {
        with_plaintext_mode(|| {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.json");
            let store = FileCredentialStore::new(&path);
            store.set("svc", "a", "1").unwrap();
            store.set("svc", "b", "2").unwrap();
            let mut keys = store.list_keys("svc").unwrap();
            keys.sort();
            assert_eq!(keys, vec!["a", "b"]);
        });
    }

    #[test]
    fn file_store_not_found() {
        with_plaintext_mode(|| {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.json");
            let store = FileCredentialStore::new(&path);
            assert!(matches!(
                store.get("svc", "missing"),
                Err(CredentialError::NotFound(_))
            ));
        });
    }

    // ── Encrypted (with passphrase) tests ────────────────────────────

    #[test]
    fn encrypted_file_store_set_get() {
        with_passphrase("test-passphrase-123", || {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.enc");
            let store = FileCredentialStore::new(&path);
            store.set("svc", "tok", "abc123").unwrap();
            assert!(path.exists());
            assert_eq!(store.get("svc", "tok").unwrap(), "abc123");
        });
    }

    #[test]
    fn encrypted_file_is_binary_not_json() {
        with_passphrase("another-passphrase", || {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.enc");
            let store = FileCredentialStore::new(&path);
            store.set("svc", "key", "val").unwrap();

            let raw = std::fs::read(&path).unwrap();
            assert!(
                !raw.starts_with(b"{"),
                "encrypted file must not be plaintext JSON"
            );
            // Must have salt + nonce prefix
            assert!(
                raw.len() >= SALT_LEN + NONCE_LEN + 16,
                "file too short for encrypted format: {} bytes",
                raw.len()
            );
        });
    }

    #[test]
    fn encrypted_file_persistence_across_store_reopens() {
        with_passphrase("persist-test-key", || {
            let dir = tempfile::tempdir().unwrap();
            let path = dir.path().join("creds.enc");

            // Write with passphrase
            let store = FileCredentialStore::new(&path);
            store.set("svc", "tok", "secret123").unwrap();

            // Read back with same passphrase (new store instance)
            let store = FileCredentialStore::new(&path);
            assert_eq!(store.get("svc", "tok").unwrap(), "secret123");
        });
    }

    // ── Key derivation unit tests ───────────────────────────────────

    #[test]
    fn derive_key_is_deterministic_with_same_salt() {
        let _guard = test_lock().lock().unwrap();
        let passphrase = b"test-passphrase";
        let salt = [0xabu8; SALT_LEN];
        let key1 = FileCredentialStore::derive_key(passphrase, &salt);
        let key2 = FileCredentialStore::derive_key(passphrase, &salt);
        assert_eq!(key1, key2);
    }

    #[test]
    fn derive_key_differs_with_different_salt() {
        let _guard = test_lock().lock().unwrap();
        let passphrase = b"test-passphrase";
        let salt1 = [0xabu8; SALT_LEN];
        let mut salt2 = [0xfeu8; SALT_LEN];
        salt2[0] = 0x01;
        let key1 = FileCredentialStore::derive_key(passphrase, &salt1);
        let key2 = FileCredentialStore::derive_key(passphrase, &salt2);
        assert_ne!(key1, key2);
    }

    #[test]
    fn derive_key_differs_with_different_passphrase() {
        let _guard = test_lock().lock().unwrap();
        let salt = [0xcdu8; SALT_LEN];
        let key1 = FileCredentialStore::derive_key(b"pass-one", &salt);
        let key2 = FileCredentialStore::derive_key(b"pass-two", &salt);
        assert_ne!(key1, key2);
    }
}
