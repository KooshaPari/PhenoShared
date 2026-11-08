//! Small filesystem helpers shared by the profile and lease stores.
//!
//! Every durable state file is written by temp-file-then-rename so a reader never
//! observes a half-written manifest, and every directory this crate creates is
//! restricted to the owner on Unix.

use std::{fs, io::Write, path::Path};

use serde::{de::DeserializeOwned, Serialize};

use crate::Result;

/// Create a directory and any missing parents, restricting it to the owner on Unix.
pub(crate) fn ensure_private_dir(path: &Path) -> Result<()> {
    fs::create_dir_all(path)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(path)?.permissions();
        perms.set_mode(0o700);
        fs::set_permissions(path, perms)?;
    }
    Ok(())
}

/// Atomically replace `path` with the serialized `value`.
pub(crate) fn write_json_atomic<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    let parent = path.parent().ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::InvalidInput, "path has no parent")
    })?;
    ensure_private_dir(parent)?;

    let body = serde_json::to_vec_pretty(value)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    let tmp = parent.join(format!(
        ".{}.tmp-{}",
        path.file_name()
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| "state".to_string()),
        std::process::id()
    ));

    {
        let mut file = fs::File::create(&tmp)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = file.metadata()?.permissions();
            perms.set_mode(0o600);
            file.set_permissions(perms)?;
        }
        file.write_all(&body)?;
        file.sync_all()?;
    }

    fs::rename(&tmp, path)?;
    Ok(())
}

/// Read and deserialize a JSON file, or `None` when it does not exist.
pub(crate) fn read_json<T: DeserializeOwned>(path: &Path) -> Result<Option<T>> {
    match fs::read(path) {
        Ok(bytes) => {
            let value = serde_json::from_slice(&bytes)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
            Ok(Some(value))
        },
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(err) => Err(err.into()),
    }
}

/// Milliseconds since the Unix epoch, saturating at `u64::MAX`.
pub(crate) fn now_unix_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

/// Recursively copy a directory tree.
///
/// Browser database branches are never merged, so a fork is a copy and nothing
/// else: there is no code path here that reads both sides and reconciles them.
pub(crate) fn copy_tree(from: &Path, to: &Path) -> Result<()> {
    ensure_private_dir(to)?;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let source = entry.path();
        let target = to.join(entry.file_name());
        let file_type = entry.file_type()?;
        if file_type.is_dir() {
            copy_tree(&source, &target)?;
        } else if file_type.is_file() {
            fs::copy(&source, &target)?;
        }
        // Symlinks are intentionally skipped: a browser data directory has no
        // legitimate need for them and following one could escape the store.
    }
    Ok(())
}
