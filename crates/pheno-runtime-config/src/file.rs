//! File-based reloadable config watcher.
//!
//! Uses [`notify`] v6 to watch a config file for changes, parses it as
//! TOML or JSON (based on extension), and swaps it into an [`ArcReloadable`].

use std::path::PathBuf;
use std::sync::Arc;

use notify::{Event, EventKind, RecursiveMode, Watcher};
use tokio::sync::watch;

use crate::{ArcReloadable, ReloadError, Reloadable};

/// A file-based reloadable configuration.
pub struct FileConfig<T> {
    inner: ArcReloadable<T>,
    path: PathBuf,
}

impl<T: Send + Sync + 'static> Clone for FileConfig<T> {
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.clone(),
            path: self.path.clone(),
        }
    }
}

impl<T: serde::de::DeserializeOwned + Send + Sync + 'static> FileConfig<T> {
    /// Create a new `FileConfig` watching `path`.
    ///
    /// Reads the initial value synchronously, then spawns a file watcher that
    /// calls `reload()` on every modification event.
    pub async fn new(path: impl Into<PathBuf>) -> Result<Self, ReloadError> {
        let path = path.into();
        let initial = Self::read_file(&path)?;
        let config = Self {
            inner: ArcReloadable::new(initial),
            path,
        };
        config.start_watcher()?;
        Ok(config)
    }

    fn read_file(path: &PathBuf) -> Result<T, ReloadError> {
        let content = std::fs::read_to_string(path)?;
        match path.extension().and_then(|e| e.to_str()) {
            Some("json") => Ok(serde_json::from_str(&content)?),
            _ => Ok(toml::from_str(&content)?),
        }
    }

    fn start_watcher(&self) -> Result<(), ReloadError> {
        let path = self.path.clone();
        let watch_root = path.parent().unwrap_or(&path).to_path_buf();
        let inner = self.inner.clone();

        let mut watcher = notify::recommended_watcher(move |res: Result<Event, notify::Error>| {
            if let Ok(event) = res {
                if matches!(event.kind, EventKind::Modify(_) | EventKind::Create(_)) {
                    if let Ok(new) = Self::read_file(&path) {
                        let _ = inner.reload(new);
                    }
                }
            }
        })?;

        watcher.watch(&watch_root, RecursiveMode::NonRecursive)?;
        // Keep watcher alive — store in self
        std::mem::forget(watcher);
        Ok(())
    }
}

impl<T: Send + Sync + 'static> Reloadable<T> for FileConfig<T> {
    fn reload(&self, new: T) -> Result<(), ReloadError> {
        self.inner.reload(new)
    }

    fn current(&self) -> Arc<T> {
        self.inner.current()
    }

    fn watch(&self) -> watch::Receiver<Arc<T>> {
        self.inner.watch()
    }
}
