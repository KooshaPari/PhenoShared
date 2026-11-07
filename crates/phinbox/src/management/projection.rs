use super::store::{read_u64, sql_u64};
use super::Store;
use anyhow::{bail, Result};
use rusqlite::{params, OptionalExtension, TransactionBehavior};
impl Store {
    /// Exclusive, expiring projection lease shared by all mirror processes.
    pub fn acquire_projection_lease(&self, owner: &str, now_ms: u64, ttl_ms: u64) -> Result<bool> {
        if owner.is_empty() || ttl_ms == 0 {
            bail!("owner and positive lease TTL required");
        }
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        tx.execute_batch("CREATE TABLE IF NOT EXISTS projection_lease(id INTEGER PRIMARY KEY,owner TEXT NOT NULL,expires INTEGER NOT NULL);")?;
        let old: Option<(String, u64)> = tx
            .query_row(
                "SELECT owner,expires FROM projection_lease WHERE id=1",
                [],
                |r| Ok((r.get(0)?, read_u64(r, 1)?)),
            )
            .optional()?;
        if old.is_some_and(|(old, expires)| old != owner && expires > now_ms) {
            return Ok(false);
        }
        let expiry = now_ms
            .checked_add(ttl_ms)
            .ok_or_else(|| anyhow::anyhow!("lease overflow"))?;
        tx.execute("INSERT INTO projection_lease VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,expires=excluded.expires",params![owner,sql_u64(expiry)?])?;
        tx.commit()?;
        Ok(true)
    }
    pub fn release_projection_lease(&self, owner: &str) -> Result<()> {
        self.connection()?.execute(
            "DELETE FROM projection_lease WHERE id=1 AND owner=?",
            [owner],
        )?;
        Ok(())
    }
    /// Persist transport checkpoint before a potentially ambiguous external side effect.
    pub fn set_projection_checkpoint(&self, item_id: &str, value: &str) -> Result<()> {
        let c = self.connection()?;
        c.execute_batch("CREATE TABLE IF NOT EXISTS projection_checkpoints(item_id TEXT PRIMARY KEY,value TEXT NOT NULL);")?;
        c.execute("INSERT INTO projection_checkpoints VALUES(?,?) ON CONFLICT(item_id) DO UPDATE SET value=excluded.value",params![item_id,value])?;
        Ok(())
    }
    pub fn projection_checkpoint(&self, item_id: &str) -> Result<Option<String>> {
        let c = self.connection()?;
        c.execute_batch("CREATE TABLE IF NOT EXISTS projection_checkpoints(item_id TEXT PRIMARY KEY,value TEXT NOT NULL);")?;
        Ok(c.query_row(
            "SELECT value FROM projection_checkpoints WHERE item_id=?",
            [item_id],
            |r| r.get(0),
        )
        .optional()?)
    }
    /// Ordered canonical event reader for local cockpit/ledger consumers.
    pub fn events(&self, after: u64, limit: usize) -> Result<Vec<serde_json::Value>> {
        let c = self.connection()?;
        let mut q = c.prepare(
            "SELECT seq,item_id,revision,actor,action FROM events WHERE seq>? ORDER BY seq LIMIT ?",
        )?;
        let rows=q.query_map(params![sql_u64(after)?,limit.min(1000) as i64],|r|Ok(serde_json::json!({"sequence":read_u64(r,0)?,"item_id":r.get::<_,String>(1)?,"revision":read_u64(r,2)?,"actor":r.get::<_,String>(3)?,"action":r.get::<_,String>(4)?})))?;
        Ok(rows.collect::<std::result::Result<Vec<_>, _>>()?)
    }
}

impl Store {
    pub fn acquire_ingress_lease(&self, owner: &str, now_ms: u64, ttl_ms: u64) -> Result<bool> {
        if owner.is_empty() || ttl_ms == 0 {
            bail!("owner and positive lease TTL required");
        }
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        tx.execute_batch("CREATE TABLE IF NOT EXISTS ingress_lease(id INTEGER PRIMARY KEY,owner TEXT NOT NULL,expires INTEGER NOT NULL);")?;
        let old: Option<(String, u64)> = tx
            .query_row(
                "SELECT owner,expires FROM ingress_lease WHERE id=1",
                [],
                |r| Ok((r.get(0)?, read_u64(r, 1)?)),
            )
            .optional()?;
        if old.is_some_and(|(old, expires)| old != owner && expires > now_ms) {
            return Ok(false);
        }
        let expiry = now_ms
            .checked_add(ttl_ms)
            .ok_or_else(|| anyhow::anyhow!("lease overflow"))?;
        tx.execute("INSERT INTO ingress_lease VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,expires=excluded.expires",params![owner,sql_u64(expiry)?])?;
        tx.commit()?;
        Ok(true)
    }
    pub fn release_ingress_lease(&self, owner: &str) -> Result<()> {
        self.connection()?
            .execute("DELETE FROM ingress_lease WHERE id=1 AND owner=?", [owner])?;
        Ok(())
    }
}

impl Store {
    pub fn acquire_receiver_lease(&self, owner: &str, now_ms: u64, ttl_ms: u64) -> Result<bool> {
        self.acquire_ingress_lease(owner, now_ms, ttl_ms)
    }
    pub fn release_receiver_lease(&self, owner: &str) -> Result<()> {
        self.release_ingress_lease(owner)
    }
}
