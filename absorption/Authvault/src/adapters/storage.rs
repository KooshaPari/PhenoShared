//! In-memory storage adapter.

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};

use async_trait::async_trait;

use crate::domain::ports::{SessionStorage, UserStorage};
use crate::domain::{Session, SessionId, User, UserId};

/// In-memory user storage.
pub struct InMemoryUserStorage {
    users: Arc<RwLock<HashMap<String, User>>>,
    by_email: Arc<RwLock<HashMap<String, String>>>,
}

impl InMemoryUserStorage {
    pub fn new() -> Self {
        Self {
            users: Arc::new(RwLock::new(HashMap::new())),
            by_email: Arc::new(RwLock::new(HashMap::new())),
        }
    }
}

impl Default for InMemoryUserStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl UserStorage for InMemoryUserStorage {
    async fn create(&self, user: &User) -> Result<(), String> {
        let mut users = self.users.write().map_err(|e| e.to_string())?;
        let mut by_email = self.by_email.write().map_err(|e| e.to_string())?;

        users.insert(user.id.to_string(), user.clone());
        by_email.insert(user.email.clone(), user.id.to_string());

        Ok(())
    }

    async fn get_by_id(&self, id: &UserId) -> Result<Option<User>, String> {
        let users = self.users.read().map_err(|e| e.to_string())?;
        Ok(users.get(&id.to_string()).cloned())
    }

    async fn get_by_email(&self, email: &str) -> Result<Option<User>, String> {
        let by_email = self.by_email.read().map_err(|e| e.to_string())?;
        let users = self.users.read().map_err(|e| e.to_string())?;

        Ok(by_email.get(email).and_then(|id| users.get(id).cloned()))
    }

    async fn update(&self, user: &User) -> Result<(), String> {
        let mut users = self.users.write().map_err(|e| e.to_string())?;
        users.insert(user.id.to_string(), user.clone());
        Ok(())
    }

    async fn delete(&self, id: &UserId) -> Result<(), String> {
        let mut users = self.users.write().map_err(|e| e.to_string())?;
        let user = users.remove(&id.to_string());

        if let Some(user) = user {
            let mut by_email = self.by_email.write().map_err(|e| e.to_string())?;
            by_email.remove(&user.email);
        }

        Ok(())
    }

    async fn list(&self) -> Result<Vec<User>, String> {
        let users = self.users.read().map_err(|e| e.to_string())?;
        Ok(users.values().cloned().collect())
    }
}

/// In-memory session storage.
pub struct InMemorySessionStorage {
    sessions: Arc<RwLock<HashMap<String, Session>>>,
    by_user: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

impl InMemorySessionStorage {
    pub fn new() -> Self {
        Self {
            sessions: Arc::new(RwLock::new(HashMap::new())),
            by_user: Arc::new(RwLock::new(HashMap::new())),
        }
    }
}

impl Default for InMemorySessionStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl SessionStorage for InMemorySessionStorage {
    async fn create(&self, session: &Session) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        let mut by_user = self.by_user.write().map_err(|e| e.to_string())?;

        sessions.insert(session.id.to_string(), session.clone());
        by_user.entry(session.user_id.clone()).or_default().push(session.id.to_string());

        Ok(())
    }

    async fn get_by_id(&self, id: &SessionId) -> Result<Option<Session>, String> {
        let sessions = self.sessions.read().map_err(|e| e.to_string())?;
        Ok(sessions.get(&id.to_string()).cloned())
    }

    async fn update(&self, session: &Session) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        sessions.insert(session.id.to_string(), session.clone());
        Ok(())
    }

    async fn delete(&self, id: &SessionId) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        let session = sessions.remove(&id.to_string());
        if let Some(session) = session {
            let mut by_user = self.by_user.write().map_err(|e| e.to_string())?;
            if let Some(ids) = by_user.get_mut(&session.user_id) {
                ids.retain(|s_id| s_id != &id.to_string());
                if ids.is_empty() {
                    by_user.remove(&session.user_id);
                }
            }
        }
        Ok(())
    }

    async fn delete_by_user(&self, user_id: &str) -> Result<(), String> {
        let mut by_user = self.by_user.write().map_err(|e| e.to_string())?;
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;

        if let Some(ids) = by_user.remove(user_id) {
            for id in ids {
                sessions.remove(&id);
            }
        }

        Ok(())
    }

    async fn delete_expired(&self) -> Result<usize, String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        let mut by_user = self.by_user.write().map_err(|e| e.to_string())?;
        let now = chrono::Utc::now();
        let mut expired_ids: Vec<(String, String)> = Vec::new();

        for (id, session) in sessions.iter() {
            if session.expires_at < now
                || session.state != crate::domain::session::SessionState::Active
            {
                expired_ids.push((id.clone(), session.user_id.clone()));
            }
        }

        let count = expired_ids.len();
        for (id, user_id) in expired_ids {
            sessions.remove(&id);
            if let Some(ids) = by_user.get_mut(&user_id) {
                ids.retain(|s_id| s_id != &id);
                if ids.is_empty() {
                    by_user.remove(&user_id);
                }
            }
        }

        Ok(count)
    }
}

/// File-backed session storage.
///
/// Sessions are serialized as JSON and written atomically (temp file plus
/// rename) so a crash during a write cannot leave a truncated store. The file
/// is loaded on [`FileSessionStorage::open`], so sessions survive a restart.
pub struct FileSessionStorage {
    path: PathBuf,
    sessions: RwLock<HashMap<String, Session>>,
}

impl FileSessionStorage {
    /// Open (or create) a session store at `path`.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, String> {
        let path = path.as_ref().to_path_buf();
        let sessions = if path.exists() {
            let bytes = fs::read(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
            if bytes.is_empty() {
                HashMap::new()
            } else {
                serde_json::from_slice(&bytes)
                    .map_err(|e| format!("parse {}: {e}", path.display()))?
            }
        } else {
            HashMap::new()
        };
        Ok(Self { path, sessions: RwLock::new(sessions) })
    }

    fn flush(&self, sessions: &HashMap<String, Session>) -> Result<(), String> {
        let json = serde_json::to_vec_pretty(sessions).map_err(|e| e.to_string())?;
        let tmp = self.path.with_extension("tmp");
        fs::write(&tmp, &json).map_err(|e| format!("write {}: {e}", tmp.display()))?;
        fs::rename(&tmp, &self.path).map_err(|e| format!("rename {}: {e}", self.path.display()))?;
        Ok(())
    }
}

#[async_trait]
impl SessionStorage for FileSessionStorage {
    async fn create(&self, session: &Session) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        sessions.insert(session.id.to_string(), session.clone());
        self.flush(&sessions)
    }

    async fn get_by_id(&self, id: &SessionId) -> Result<Option<Session>, String> {
        let sessions = self.sessions.read().map_err(|e| e.to_string())?;
        Ok(sessions.get(&id.to_string()).cloned())
    }

    async fn update(&self, session: &Session) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        sessions.insert(session.id.to_string(), session.clone());
        self.flush(&sessions)
    }

    async fn delete(&self, id: &SessionId) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        if sessions.remove(&id.to_string()).is_some() {
            self.flush(&sessions)?;
        }
        Ok(())
    }

    async fn delete_by_user(&self, user_id: &str) -> Result<(), String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        let before = sessions.len();
        sessions.retain(|_, session| session.user_id != user_id);
        if sessions.len() != before {
            self.flush(&sessions)?;
        }
        Ok(())
    }

    async fn delete_expired(&self) -> Result<usize, String> {
        let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
        let now = chrono::Utc::now();
        let before = sessions.len();
        sessions.retain(|_, session| {
            session.expires_at >= now
                && session.state == crate::domain::session::SessionState::Active
        });
        let removed = before - sessions.len();
        if removed > 0 {
            self.flush(&sessions)?;
        }
        Ok(removed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::User;

    #[tokio::test]
    async fn test_user_storage() {
        let storage = InMemoryUserStorage::new();
        let user = User::new("test@example.com");

        storage.create(&user).await.unwrap();

        let found = storage.get_by_id(&user.id).await.unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().email, "test@example.com");

        let found_by_email = storage.get_by_email("test@example.com").await.unwrap();
        assert!(found_by_email.is_some());
    }

    #[tokio::test]
    async fn test_session_storage() {
        let storage = InMemorySessionStorage::new();
        let session = crate::domain::Session::new("user-123");

        storage.create(&session).await.unwrap();

        let found = storage.get_by_id(&session.id).await.unwrap();
        assert!(found.is_some());
        assert_eq!(found.unwrap().user_id, "user-123");
    }

    #[tokio::test]
    async fn file_session_storage_survives_reopen() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("sessions.json");
        let session = crate::domain::Session::new("user-persist");

        {
            let store = FileSessionStorage::open(&path).unwrap();
            store.create(&session).await.unwrap();
        }

        let reopened = FileSessionStorage::open(&path).unwrap();
        let found = reopened.get_by_id(&session.id).await.unwrap();
        let found = found.expect("session must survive reopen");
        assert_eq!(found.user_id, "user-persist");
    }

    #[tokio::test]
    async fn file_session_storage_deletes_expired_and_by_user() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("sessions.json");
        let store = FileSessionStorage::open(&path).unwrap();

        let active = crate::domain::Session::new("user-a");
        let mut expired = crate::domain::Session::new("user-a");
        expired.expires_at = chrono::Utc::now() - chrono::Duration::hours(1);
        let other = crate::domain::Session::new("user-b");

        store.create(&active).await.unwrap();
        store.create(&expired).await.unwrap();
        store.create(&other).await.unwrap();

        assert_eq!(store.delete_expired().await.unwrap(), 1);
        assert!(store.get_by_id(&expired.id).await.unwrap().is_none());

        store.delete_by_user("user-a").await.unwrap();
        assert!(store.get_by_id(&active.id).await.unwrap().is_none());
        assert!(store.get_by_id(&other.id).await.unwrap().is_some());
    }
}
