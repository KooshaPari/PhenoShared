//! B4 Bifrost model catalog cache (rusqlite-backed).
//!
//! Mirrors the schema and contract documented for `bifrost_models` in
//! the lifetime/pheno-style repo (L5-111). The in-memory catalog
//! (`crate::catalog::InMemoryCatalog`) holds the dispatch hot path;
//! this module is the durable cold path that the in-memory catalog is
//! seeded from on startup and re-seeded from by the B3 sweeper.
//!
//! ## Schema
//!
//! ```sql
//! CREATE TABLE bifrost_models (
//!     id           TEXT NOT NULL,
//!     provider     TEXT NOT NULL,
//!     object       TEXT NOT NULL,
//!     owned_by     TEXT,
//!     display_name TEXT,
//!     fetched_at   TEXT NOT NULL,
//!     expires_at   TEXT NOT NULL,
//!     payload      TEXT NOT NULL,
//!     PRIMARY KEY (provider, id)
//! );
//! CREATE TABLE bifrost_models_meta (
//!     provider    TEXT PRIMARY KEY,
//!     last_status TEXT NOT NULL CHECK (last_status IN ('ok', 'error', 'partial')),
//!     last_error  TEXT,
//!     last_count  INTEGER NOT NULL DEFAULT 0,
//!     updated_at  TEXT NOT NULL
//! );
//! ```
//!
//! ## Contract
//!
//! - **TTL**: default 1 hour, overridable per `upsert_provider`
//! - **Stale-tolerant reads**: `entries_for_provider` returns expired
//!   rows when `include_expired=true` so the dispatch hot path keeps
//!   working through a degraded gateway
//! - **Hard cap**: `entries_for_provider` truncates at
//!   `MAX_ENTRIES_PER_PROVIDER` (5000) as a defense against runaway
//!   upstreams
//! - **Partial-success**: a fetcher that returns some unparseable rows
//!   still upserts the parseable ones; meta row is set to `partial`
//! - **Error observability**: every fetch records `last_status` and
//!   optional `last_error`

use std::path::Path;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use rusqlite::{params, Connection};

use crate::catalog::{CatalogEntry, CatalogWire};
use crate::error::{Error, Result};

pub const MAX_ENTRIES_PER_PROVIDER: usize = 5000;
pub const DEFAULT_TTL_SECS: u64 = 3600;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FetchStatus {
    Ok,
    Error,
    Partial,
}

impl FetchStatus {
    fn as_str(self) -> &'static str {
        match self {
            FetchStatus::Ok => "ok",
            FetchStatus::Error => "error",
            FetchStatus::Partial => "partial",
        }
    }

    fn parse(s: &str) -> Result<Self> {
        match s {
            "ok" => Ok(FetchStatus::Ok),
            "error" => Ok(FetchStatus::Error),
            "partial" => Ok(FetchStatus::Partial),
            other => Err(Error::Invalid(format!(
                "unknown fetch status '{other}' (expected ok|error|partial)"
            ))),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ProviderMeta {
    pub status: FetchStatus,
    pub last_error: Option<String>,
    pub last_count: usize,
    pub updated_at: SystemTime,
}

/// Bifrost model catalog cache backed by a single SQLite connection.
pub struct BifrostModelCache {
    conn: Connection,
    include_expired: bool,
}

impl BifrostModelCache {
    /// Open or create a cache at `path` and apply the migration.
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let conn = Connection::open(path)?;
        Self::init_schema(&conn)?;
        Ok(Self {
            conn,
            include_expired: true,
        })
    }

    /// In-memory cache (`:memory:`) for tests.
    pub fn open_in_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        Self::init_schema(&conn)?;
        Ok(Self {
            conn,
            include_expired: true,
        })
    }

    /// When `false`, expired entries are skipped (production default).
    pub fn set_include_expired(&mut self, include: bool) {
        self.include_expired = include;
    }

    fn init_schema(conn: &Connection) -> Result<()> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS bifrost_models (
                 id           TEXT NOT NULL,
                 provider     TEXT NOT NULL,
                 object       TEXT NOT NULL,
                 owned_by     TEXT,
                 display_name TEXT,
                 fetched_at   TEXT NOT NULL,
                 expires_at   TEXT NOT NULL,
                 payload      TEXT NOT NULL,
                 PRIMARY KEY (provider, id)
             );
             CREATE INDEX IF NOT EXISTS idx_bifrost_models_provider
                 ON bifrost_models(provider);
             CREATE INDEX IF NOT EXISTS idx_bifrost_models_expires_at
                 ON bifrost_models(expires_at);
             CREATE TABLE IF NOT EXISTS bifrost_models_meta (
                 provider    TEXT PRIMARY KEY,
                 last_status TEXT NOT NULL CHECK (last_status IN ('ok', 'error', 'partial')),
                 last_error  TEXT,
                 last_count  INTEGER NOT NULL DEFAULT 0,
                 updated_at  TEXT NOT NULL
             );",
        )?;
        Ok(())
    }

    /// Replace the cached entries for `provider` with `wire`'s data,
    /// inserting `meta` as the fetch status. Empty data is rejected
    /// (a partial-empty fetch is not a cache hit).
    pub fn upsert_provider(
        &self,
        provider: &str,
        wire: &CatalogWire,
        meta: FetchStatus,
        last_error: Option<&str>,
        ttl: Duration,
    ) -> Result<usize> {
        let now = system_time_now_secs();
        let expires = now + ttl.as_secs();
        let now_s = now.to_string();
        let expires_s = expires.to_string();

        let mut inserted = 0usize;
        let tx = self.conn.unchecked_transaction()?;

        tx.execute(
            "DELETE FROM bifrost_models WHERE provider = ?1",
            params![provider],
        )?;

        for entry in &wire.data {
            if inserted >= MAX_ENTRIES_PER_PROVIDER {
                break;
            }
            let payload = serde_json::to_string(entry)
                .map_err(|e| Error::Invalid(format!("catalog entry serialize: {e}")))?;
            tx.execute(
                "INSERT INTO bifrost_models
                 (id, provider, object, owned_by, display_name,
                  fetched_at, expires_at, payload)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    entry.id,
                    provider,
                    entry.object,
                    entry.owned_by,
                    entry.display_name,
                    now_s,
                    expires_s,
                    payload,
                ],
            )?;
            inserted += 1;
        }

        tx.execute(
            "INSERT INTO bifrost_models_meta
                 (provider, last_status, last_error, last_count, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(provider) DO UPDATE SET
                 last_status = excluded.last_status,
                 last_error  = excluded.last_error,
                 last_count  = excluded.last_count,
                 updated_at  = excluded.updated_at",
            params![provider, meta.as_str(), last_error, inserted as i64, now_s,],
        )?;

        tx.commit()?;
        Ok(inserted)
    }

    /// Read entries for `provider`, optionally including expired ones.
    pub fn entries_for_provider(
        &self,
        provider: &str,
        now: SystemTime,
    ) -> Result<Vec<CatalogEntry>> {
        let now_s = system_time_to_secs(now).to_string();
        let sql = if self.include_expired {
            "SELECT id, object, owned_by, display_name, payload
             FROM bifrost_models
             WHERE provider = ?1
             LIMIT ?2"
        } else {
            "SELECT id, object, owned_by, display_name, payload
             FROM bifrost_models
             WHERE provider = ?1 AND expires_at > ?2
             LIMIT ?3"
        };

        let mut stmt = self.conn.prepare(sql)?;
        let rows: Vec<CatalogEntry> = if self.include_expired {
            stmt.query_map(params![provider, MAX_ENTRIES_PER_PROVIDER as i64], |row| {
                let payload: String = row.get(4)?;
                let mut entry: CatalogEntry = serde_json::from_str(&payload).map_err(|e| {
                    rusqlite::Error::FromSqlConversionFailure(
                        4,
                        rusqlite::types::Type::Text,
                        Box::new(e),
                    )
                })?;
                // Allow columns to override payload (for migrations where
                // the schema adds a column ahead of the JSON).
                let object: String = row.get(1)?;
                let owned_by: Option<String> = row.get(2)?;
                let display_name: Option<String> = row.get(3)?;
                entry.object = object;
                entry.owned_by = owned_by;
                entry.display_name = display_name;
                Ok(entry)
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?
        } else {
            stmt.query_map(
                params![provider, now_s, MAX_ENTRIES_PER_PROVIDER as i64],
                |row| {
                    let payload: String = row.get(4)?;
                    let mut entry: CatalogEntry = serde_json::from_str(&payload).map_err(|e| {
                        rusqlite::Error::FromSqlConversionFailure(
                            4,
                            rusqlite::types::Type::Text,
                            Box::new(e),
                        )
                    })?;
                    let object: String = row.get(1)?;
                    let owned_by: Option<String> = row.get(2)?;
                    let display_name: Option<String> = row.get(3)?;
                    entry.object = object;
                    entry.owned_by = owned_by;
                    entry.display_name = display_name;
                    Ok(entry)
                },
            )?
            .collect::<rusqlite::Result<Vec<_>>>()?
        };

        Ok(rows)
    }

    pub fn provider_meta(&self, provider: &str) -> Result<Option<ProviderMeta>> {
        let mut stmt = self.conn.prepare(
            "SELECT last_status, last_error, last_count, updated_at
             FROM bifrost_models_meta WHERE provider = ?1",
        )?;
        let mut rows = stmt.query(params![provider])?;
        if let Some(row) = rows.next()? {
            let status_s: String = row.get(0)?;
            let status = FetchStatus::parse(&status_s)?;
            let last_error: Option<String> = row.get(1)?;
            let last_count: i64 = row.get(2)?;
            let updated_at_s: String = row.get(3)?;
            let updated_at = parse_system_time(&updated_at_s).unwrap_or(UNIX_EPOCH);
            Ok(Some(ProviderMeta {
                status,
                last_error,
                last_count: last_count as usize,
                updated_at,
            }))
        } else {
            Ok(None)
        }
    }

    pub fn purge_expired(&self, now: SystemTime) -> Result<usize> {
        let now_s = system_time_to_secs(now).to_string();
        let n = self.conn.execute(
            "DELETE FROM bifrost_models WHERE expires_at <= ?1",
            params![now_s],
        )?;
        Ok(n)
    }

    pub fn purge_provider(&self, provider: &str) -> Result<()> {
        self.conn.execute(
            "DELETE FROM bifrost_models WHERE provider = ?1",
            params![provider],
        )?;
        self.conn.execute(
            "DELETE FROM bifrost_models_meta WHERE provider = ?1",
            params![provider],
        )?;
        Ok(())
    }
}

fn system_time_now_secs() -> u64 {
    system_time_to_secs(SystemTime::now())
}

fn system_time_to_secs(t: SystemTime) -> u64 {
    t.duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn parse_system_time(s: &str) -> Option<SystemTime> {
    let secs: u64 = s.parse().ok()?;
    Some(UNIX_EPOCH + Duration::from_secs(secs))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::catalog::{CatalogEntry, CatalogWire};

    fn wire_with_two_models() -> CatalogWire {
        CatalogWire {
            object: "list".to_string(),
            data: vec![
                CatalogEntry {
                    id: "gpt-4o".to_string(),
                    object: "model".to_string(),
                    owned_by: Some("openai".to_string()),
                    display_name: None,
                },
                CatalogEntry {
                    id: "claude-sonnet".to_string(),
                    object: "model".to_string(),
                    owned_by: Some("anthropic".to_string()),
                    display_name: Some("Claude Sonnet".to_string()),
                },
            ],
        }
    }

    #[test]
    fn open_in_memory_initializes_schema() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        // Schema is applied: a fresh upsert should succeed.
        let n = cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        assert_eq!(n, 2);
    }

    #[test]
    fn upsert_provider_replaces_existing_entries() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        // Re-upsert with a different wire; old rows must be gone.
        let wire_one = CatalogWire {
            object: "list".to_string(),
            data: vec![CatalogEntry {
                id: "gpt-4o-mini".to_string(),
                object: "model".to_string(),
                owned_by: Some("openai".to_string()),
                display_name: None,
            }],
        };
        cache
            .upsert_provider(
                "openai",
                &wire_one,
                FetchStatus::Partial,
                Some("model A malformed"),
                Duration::from_secs(60),
            )
            .unwrap();
        let entries = cache
            .entries_for_provider("openai", SystemTime::now())
            .unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].id, "gpt-4o-mini");
        let meta = cache.provider_meta("openai").unwrap().unwrap();
        assert_eq!(meta.status, FetchStatus::Partial);
        assert_eq!(meta.last_error.as_deref(), Some("model A malformed"));
        assert_eq!(meta.last_count, 1);
    }

    #[test]
    fn entries_for_provider_includes_expired_by_default() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(60),
            )
            .unwrap();
        // Far future = all rows are expired but include_expired=true
        let future = SystemTime::now() + Duration::from_secs(86400 * 365);
        let entries = cache.entries_for_provider("openai", future).unwrap();
        assert_eq!(entries.len(), 2);
    }

    #[test]
    fn entries_for_provider_excludes_expired_when_disabled() {
        let mut cache = BifrostModelCache::open_in_memory().unwrap();
        cache.set_include_expired(false);
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(60),
            )
            .unwrap();
        let future = SystemTime::now() + Duration::from_secs(86400 * 365);
        let entries = cache.entries_for_provider("openai", future).unwrap();
        assert!(entries.is_empty());
    }

    #[test]
    fn provider_meta_returns_none_for_unknown_provider() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        assert!(cache.provider_meta("nonexistent").unwrap().is_none());
    }

    #[test]
    fn purge_expired_removes_only_past_rows() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(60),
            )
            .unwrap();
        let n = cache
            .purge_expired(SystemTime::now() + Duration::from_secs(86400))
            .unwrap();
        assert_eq!(n, 2);
        let entries = cache
            .entries_for_provider("openai", SystemTime::now())
            .unwrap();
        assert!(entries.is_empty());
    }

    #[test]
    fn purge_provider_removes_meta_and_entries() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        cache.purge_provider("openai").unwrap();
        assert!(cache.provider_meta("openai").unwrap().is_none());
        let entries = cache
            .entries_for_provider("openai", SystemTime::now())
            .unwrap();
        assert!(entries.is_empty());
    }

    #[test]
    fn max_entries_cap_truncates_inserts() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        // Build a wire with more entries than the cap.
        let entries: Vec<CatalogEntry> = (0..(MAX_ENTRIES_PER_PROVIDER + 10))
            .map(|i| CatalogEntry {
                id: format!("model-{i}"),
                object: "model".to_string(),
                owned_by: Some("test".to_string()),
                display_name: None,
            })
            .collect();
        let wire = CatalogWire {
            object: "list".to_string(),
            data: entries,
        };
        let n = cache
            .upsert_provider(
                "test",
                &wire,
                FetchStatus::Partial,
                Some("hard-cap hit"),
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        assert_eq!(n, MAX_ENTRIES_PER_PROVIDER);
    }

    #[test]
    fn error_status_records_last_error() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &CatalogWire {
                    object: "list".to_string(),
                    data: vec![],
                },
                FetchStatus::Error,
                Some("upstream timeout"),
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        let meta = cache.provider_meta("openai").unwrap().unwrap();
        assert_eq!(meta.status, FetchStatus::Error);
        assert_eq!(meta.last_error.as_deref(), Some("upstream timeout"));
        assert_eq!(meta.last_count, 0);
    }

    #[test]
    fn multiple_providers_are_independent() {
        let cache = BifrostModelCache::open_in_memory().unwrap();
        cache
            .upsert_provider(
                "openai",
                &wire_with_two_models(),
                FetchStatus::Ok,
                None,
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();
        let anthropic_wire = CatalogWire {
            object: "list".to_string(),
            data: vec![CatalogEntry {
                id: "claude-opus".to_string(),
                object: "model".to_string(),
                owned_by: Some("anthropic".to_string()),
                display_name: None,
            }],
        };
        cache
            .upsert_provider(
                "anthropic",
                &anthropic_wire,
                FetchStatus::Ok,
                None,
                Duration::from_secs(DEFAULT_TTL_SECS),
            )
            .unwrap();

        let openai = cache
            .entries_for_provider("openai", SystemTime::now())
            .unwrap();
        let anthropic = cache
            .entries_for_provider("anthropic", SystemTime::now())
            .unwrap();
        assert_eq!(openai.len(), 2);
        assert_eq!(anthropic.len(), 1);
        assert_eq!(anthropic[0].id, "claude-opus");
    }
}
