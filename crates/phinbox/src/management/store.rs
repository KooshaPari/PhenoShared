use super::{Effect, EffectKind, Item, ThreadMap};
use anyhow::{bail, Context, Result};
use rusqlite::{params, Connection, TransactionBehavior};
use std::{
    path::{Path, PathBuf},
    time::Duration,
};

/// Connections are opened per operation; SQLite serializes cross-process writers.
#[derive(Debug, Clone)]
pub struct Store {
    pub(super) path: PathBuf,
}
impl Store {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent)?;
        }
        let store = Self { path };
        let conn = store.connection()?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&store.path, std::fs::Permissions::from_mode(0o600))?;
        }
        let version: u32 = conn.query_row("PRAGMA user_version", [], |r| r.get(0))?;
        if version > 1 {
            bail!("unsupported management database schema");
        }
        conn.execute_batch("PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, command TEXT NOT NULL, result TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, item_id TEXT NOT NULL, revision INTEGER NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, error TEXT);
          CREATE TABLE IF NOT EXISTS threads(item_id TEXT PRIMARY KEY, thread_id TEXT NOT NULL UNIQUE, body TEXT NOT NULL);
          PRAGMA user_version=1;")?;
        Ok(store)
    }
    pub(super) fn connection(&self) -> Result<Connection> {
        let c = Connection::open(&self.path)?;
        c.busy_timeout(Duration::from_secs(5))?;
        Ok(c)
    }
    pub fn path(&self) -> &Path {
        &self.path
    }
    pub fn get(&self, id: &str) -> Result<Option<Item>> {
        let c = self.connection()?;
        let mut q = c.prepare("SELECT body FROM items WHERE id=?")?;
        let mut rows = q.query([id])?;
        match rows.next()? {
            Some(r) => Ok(Some(serde_json::from_str(&r.get::<_, String>(0)?)?)),
            None => Ok(None),
        }
    }
    pub fn list(&self) -> Result<Vec<Item>> {
        let c = self.connection()?;
        let mut q = c.prepare("SELECT body FROM items ORDER BY id")?;
        let rows = q.query_map([], |r| r.get::<_, String>(0))?;
        rows.map(|r| Ok(serde_json::from_str(&r?)?)).collect()
    }
    pub fn create(&self, mut item: Item) -> Result<Item> {
        if item.id.is_empty() || item.original.is_empty() {
            bail!("item id and original are required");
        }
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let existing: Option<String> = tx
            .query_row("SELECT body FROM items WHERE id=?", [&item.id], |r| {
                r.get(0)
            })
            .optional()?;
        if let Some(body) = existing {
            let old: Item = serde_json::from_str(&body)?;
            if old.original != item.original || old.source_request_id != item.source_request_id {
                bail!("item id already bound to different source");
            }
            return Ok(old);
        }
        item.revision = 1;
        let body = serde_json::to_string(&item)?;
        tx.execute(
            "INSERT INTO items VALUES(?,?,?)",
            params![item.id, sql_u64(item.revision)?, body],
        )?;
        tx.execute(
            "INSERT INTO events(item_id,revision,actor,action) VALUES(?,?,'native','create')",
            params![item.id, sql_u64(item.revision)?],
        )?;
        enqueue_effect(&tx, &item)?;
        tx.commit()?;
        Ok(item)
    }
    pub fn thread(&self, id: &str) -> Result<Option<ThreadMap>> {
        let c = self.connection()?;
        let body: Option<String> = c
            .query_row("SELECT body FROM threads WHERE item_id=?", [id], |r| {
                r.get(0)
            })
            .optional()?;
        body.map(|b| serde_json::from_str(&b).context("thread mapping"))
            .transpose()
    }
    pub fn bind_thread(&self, item_id: &str, map: ThreadMap) -> Result<()> {
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let exists: bool = tx.query_row(
            "SELECT EXISTS(SELECT 1 FROM items WHERE id=?)",
            [item_id],
            |r| r.get(0),
        )?;
        if !exists {
            bail!("unknown item");
        }
        let old: Option<String> = tx
            .query_row("SELECT body FROM threads WHERE item_id=?", [item_id], |r| {
                r.get(0)
            })
            .optional()?;
        let body = serde_json::to_string(&map)?;
        if let Some(old) = old {
            if old != body {
                bail!("thread mapping is immutable");
            }
        } else {
            tx.execute(
                "INSERT INTO threads VALUES(?,?,?)",
                params![item_id, map.thread_id, body],
            )?;
        }
        tx.commit()?;
        Ok(())
    }
    /// Ordered, durable effects. Only the elected projection worker may execute them.
    pub fn pending_effects(&self, limit: usize) -> Result<Vec<Effect>> {
        let c = self.connection()?;
        let mut q=c.prepare("SELECT id,item_id,revision,kind,body,attempts,error FROM outbox WHERE done=0 ORDER BY rowid LIMIT ?")?;
        let rows = q.query_map([i64::try_from(limit.min(1000))?], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                read_u64(r, 2)?,
                r.get::<_, String>(3)?,
                r.get::<_, String>(4)?,
                r.get::<_, u32>(5)?,
                r.get::<_, Option<String>>(6)?,
            ))
        })?;
        let mut effects = Vec::new();
        for row in rows {
            let (id, item_id, revision, kind, body, attempts, last_error) = row?;
            let thread = self.thread(&item_id)?;
            effects.push(Effect {
                id,
                item_id,
                revision,
                kind: serde_json::from_str(&kind)?,
                item: serde_json::from_str(&body)?,
                thread,
                attempts,
                last_error,
            });
        }
        Ok(effects)
    }
    pub fn acknowledge_effect(&self, id: &str) -> Result<()> {
        let c = self.connection()?;
        if c.execute("UPDATE outbox SET done=1,error=NULL WHERE id=?", [id])? != 1 {
            bail!("unknown effect");
        }
        Ok(())
    }
    pub fn record_attempt(&self, id: &str, error: &str) -> Result<()> {
        let c = self.connection()?;
        c.execute(
            "UPDATE outbox SET attempts=attempts+1,error=? WHERE id=? AND done=0",
            params![error, id],
        )?;
        Ok(())
    }
}
use rusqlite::OptionalExtension;
pub(super) fn enqueue_effect(tx: &rusqlite::Transaction<'_>, item: &Item) -> Result<()> {
    let kind = if item.status == super::Status::Closed {
        EffectKind::Close
    } else {
        EffectKind::Upsert
    };
    tx.execute(
        "INSERT INTO outbox(id,item_id,revision,kind,body) VALUES(?,?,?,?,?)",
        params![
            format!("{}:{}", item.id, item.revision),
            item.id,
            sql_u64(item.revision)?,
            serde_json::to_string(&kind)?,
            serde_json::to_string(item)?
        ],
    )?;
    Ok(())
}

pub(super) fn sql_u64(value: u64) -> Result<i64> {
    i64::try_from(value).context("value exceeds SQLite signed integer range")
}
pub(super) fn read_u64(row: &rusqlite::Row<'_>, index: usize) -> rusqlite::Result<u64> {
    let value: i64 = row.get(index)?;
    u64::try_from(value).map_err(|_| rusqlite::Error::IntegralValueOutOfRange(index, value))
}
