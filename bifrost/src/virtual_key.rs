//! B5: Virtual key minting and revocation for Bifrost gateway access.
//!
//! Virtual keys are short-lived bearer tokens that allow the Bifrost gateway
//! to authenticate requests on behalf of a caller without exposing long-lived
//! API credentials. This module provides the durable store for minted keys.
//!
//! ## Schema
//!
//! ```sql
//! CREATE TABLE virtual_keys (
//!     id         TEXT PRIMARY KEY,
//!     provider   TEXT NOT NULL,
//!     issued_at  TEXT NOT NULL,
//!     expires_at TEXT NOT NULL,
//!     revoked_at TEXT,
//!     status     TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired'))
//! );
//! CREATE INDEX idx_virtual_keys_provider   ON virtual_keys(provider);
//! CREATE INDEX idx_virtual_keys_expires_at ON virtual_keys(expires_at);
//! CREATE INDEX idx_virtual_keys_status     ON virtual_keys(status);
//! ```
//!
//! ## Contract
//!
//! - **Mint**: generates a new UUIDv4 key with `status='active'`, `revoked_at=NULL`.
//! - **Revoke**: sets `revoked_at` to now and `status='revoked'` (idempotent).
//! - **Expiry**: keys past `expires_at` are `status='expired'` on read.
//! - **TTL**: default 24h, configurable per mint call.
//! - **Hard cap**: 10,000 active keys per provider.
//!
//! The store is used by the Bifrost gateway's authentication middleware to
//! validate incoming `Authorization: Bearer <token>` headers.

#![cfg(feature = "virtual-keys")]

use std::path::Path;
use std::time::{Duration, SystemTime};

use rusqlite::{params, Connection};
use tracing::debug;
use uuid::Uuid;

use crate::error::{Error, Result};

/// Maximum active keys per provider (defense against runaway key generation).
const MAX_KEYS_PER_PROVIDER: u32 = 10_000;

/// Valid statuses for a virtual key.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TokenStatus {
    Active,
    Revoked,
    Expired,
}

impl TokenStatus {
    fn as_str(self) -> &'static str {
        match self {
            TokenStatus::Active => "active",
            TokenStatus::Revoked => "revoked",
            TokenStatus::Expired => "expired",
        }
    }

    fn parse(s: &str) -> Result<Self> {
        match s {
            "active" => Ok(TokenStatus::Active),
            "revoked" => Ok(TokenStatus::Revoked),
            "expired" => Ok(TokenStatus::Expired),
            other => Err(Error::Invalid(format!(
                "unknown token status '{other}' (expected active|revoked|expired)"
            ))),
        }
    }
}

/// A minted virtual key.
#[derive(Debug, Clone)]
pub struct VirtualKey {
    pub id: Uuid,
    pub provider: String,
    pub issued_at: SystemTime,
    pub expires_at: SystemTime,
    pub revoked_at: Option<SystemTime>,
    pub status: TokenStatus,
}

impl VirtualKey {
    pub fn is_valid(&self, now: SystemTime) -> bool {
        self.status == TokenStatus::Active && now <= self.expires_at
    }
}

/// Durable store for virtual keys, backed by SQLite.
pub struct VirtualKeyStore {
    conn: Connection,
}

impl VirtualKeyStore {
    /// Open or create a key store at `path` and apply the migration.
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let conn = Connection::open(path.as_ref())?;
        let store = Self { conn };
        store.apply_migration()?;
        Ok(store)
    }

    /// Apply the schema migration (idempotent).
    fn apply_migration(&self) -> Result<()> {
        self.conn
            .execute_batch(include_str!("virtual_key_schema.sql"))?;
        Ok(())
    }

    /// Mint a new virtual key with the given TTL (default 24h if None).
    ///
    /// Returns the newly created [`VirtualKey`] or an error if the provider
    /// already has MAX_KEYS_PER_PROVIDER active keys.
    pub fn mint(&self, provider: &str, ttl: Option<Duration>) -> Result<VirtualKey> {
        let now = SystemTime::now();
        let ttl = ttl.unwrap_or(Duration::from_secs(86400)); // 24h default
        let id = Uuid::new_v4();

        // Check hard cap before inserting.
        let active_count: u32 = self.conn.query_row(
            "SELECT COUNT(*) FROM virtual_keys WHERE provider = ?1 AND status = 'active'",
            params![provider],
            |row| row.get(0),
        )?;

        if active_count >= MAX_KEYS_PER_PROVIDER {
            return Err(Error::Invalid(format!(
                "provider '{provider}' has {active_count} active keys (max {MAX_KEYS_PER_PROVIDER})"
            )));
        }

        let now_s = rfc3339(now);
        let expires_at_s = rfc3339(now + ttl);

        self.conn.execute(
            "INSERT INTO virtual_keys (id, provider, issued_at, expires_at, status) VALUES (?1, ?2, ?3, ?4, 'active')",
            params![id.to_string(), provider, now_s, expires_at_s],
        )?;

        debug!(key_id = %id, provider = %provider, ttl_secs = %ttl.as_secs(), "minted virtual key");

        Ok(VirtualKey {
            id,
            provider: provider.to_string(),
            issued_at: now,
            expires_at: now + ttl,
            revoked_at: None,
            status: TokenStatus::Active,
        })
    }

    /// Revoke a key by ID. Idempotent: already-revoked keys are no-ops.
    pub fn revoke(&self, key_id: &Uuid) -> Result<bool> {
        let now_s = rfc3339(SystemTime::now());
        let rows = self.conn.execute(
            "UPDATE virtual_keys SET revoked_at = ?1, status = 'revoked' WHERE id = ?2 AND status = 'active'",
            params![now_s, key_id.to_string()],
        )?;

        if rows > 0 {
            debug!(key_id = %key_id, "revoked virtual key");
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Find a key by ID, returning it only if still valid (not revoked/expired).
    ///
    /// Returns `None` if the key does not exist, is revoked, or is expired.
    pub fn find(&self, key_id: &Uuid, now: SystemTime) -> Result<Option<VirtualKey>> {
        let now_s = rfc3339(now);

        let mut stmt = self.conn.prepare(
            "SELECT id, provider, issued_at, expires_at, revoked_at, status \
             FROM virtual_keys WHERE id = ?1",
        )?;

        let mut rows = stmt.query(params![key_id.to_string()])?;
        let row = match rows.next()? {
            Some(r) => r,
            None => return Ok(None),
        };

        let id_str: String = row.get(0)?;
        let provider: String = row.get(1)?;
        let issued_at_s: String = row.get(2)?;
        let expires_at_s: String = row.get(3)?;
        let revoked_at_s: Option<String> = row.get(4)?;
        let status_s: String = row.get(5)?;

        let issued_at = parse_rfc3339(&issued_at_s)
            .map_err(|e| Error::Invalid(format!("issued_at parse: {e}")))?;
        let expires_at = parse_rfc3339(&expires_at_s)
            .map_err(|e| Error::Invalid(format!("expires_at parse: {e}")))?;
        let revoked_at = revoked_at_s
            .as_deref()
            .map(parse_rfc3339)
            .transpose()
            .map_err(|e| Error::Invalid(format!("revoked_at parse: {e}")))?;
        let status = TokenStatus::parse(&status_s)?;

        let id = Uuid::parse_str(&id_str).map_err(|e| Error::Invalid(format!("id parse: {e}")))?;

        let key = VirtualKey {
            id,
            provider,
            issued_at,
            expires_at,
            revoked_at,
            status,
        };

        // Return the key only if it is still valid at `now`.
        if key.is_valid(now) {
            Ok(Some(key))
        } else {
            // Auto-expire if past expiry so the DB is gradually repaired.
            if key.expires_at < now && key.status == TokenStatus::Active {
                self.expire_impl(&id_str, &now_s)?;
            }
            Ok(None)
        }
    }

    /// Purge expired keys from the store. Returns count of purged rows.
    pub fn purge_expired(&self, now: SystemTime) -> Result<u32> {
        let now_s = rfc3339(now);
        let rows = self.conn.execute(
            "UPDATE virtual_keys SET status = 'expired' WHERE expires_at < ?1 AND status = 'active'",
            params![now_s],
        )?;
        Ok(rows as u32)
    }

    /// Check store health by executing a lightweight query.
    pub fn health_check(&self) -> Result<()> {
        self.conn
            .query_row("SELECT 1 WHERE 1 = 1", [], |_| Ok(()))?;
        Ok(())
    }

    // --- helpers -----------------------------------------------------------

    fn expire_impl(&self, id_str: &str, now_s: &str) -> Result<()> {
        self.conn.execute(
            "UPDATE virtual_keys SET status = 'expired', revoked_at = ?1 WHERE id = ?2",
            params![now_s, id_str],
        )?;
        Ok(())
    }
}

/// Format a SystemTime as an RFC 3339 string (UTC).
fn rfc3339(t: SystemTime) -> String {
    let dt: chrono::DateTime<chrono::Utc> = t.into();
    dt.to_rfc3339()
}

/// Parse an RFC 3339 string back into a SystemTime.
fn parse_rfc3339(s: &str) -> std::result::Result<SystemTime, chrono::ParseError> {
    chrono::DateTime::parse_from_rfc3339(s).map(|dt| dt.with_timezone(&chrono::Utc).into())
}
