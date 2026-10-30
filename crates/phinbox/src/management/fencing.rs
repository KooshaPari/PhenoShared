//! Fencing for projection workers: verify the live owner inside each protected write.
use super::store::read_u64;
use super::{Store, ThreadMap};
use anyhow::{bail, Result};
use rusqlite::{params, OptionalExtension, Transaction, TransactionBehavior};

fn check(tx: &Transaction<'_>, owner: &str) -> Result<()> {
    let lease: Option<(String, u64)> = tx
        .query_row(
            "SELECT owner,expires FROM projection_lease WHERE id=1",
            [],
            |r| Ok((r.get(0)?, read_u64(r, 1)?)),
        )
        .optional()?;
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_millis();
    if !lease.is_some_and(|(current, expires)| current == owner && u128::from(expires) > now) {
        bail!("projection lease lost or expired");
    }
    Ok(())
}
impl Store {
    /// Check before every REST operation; owner must be a fresh per-worker UUID.
    pub fn verify_projection_lease(&self, owner: &str) -> Result<()> {
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        check(&tx, owner)?;
        tx.commit()?;
        Ok(())
    }
    pub fn bind_thread_fenced(&self, item_id: &str, map: ThreadMap, owner: &str) -> Result<()> {
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        check(&tx, owner)?;
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
    pub fn set_projection_checkpoint_fenced(
        &self,
        item_id: &str,
        value: &str,
        owner: &str,
    ) -> Result<()> {
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        check(&tx, owner)?;
        tx.execute_batch("CREATE TABLE IF NOT EXISTS projection_checkpoints(item_id TEXT PRIMARY KEY,value TEXT NOT NULL);")?;
        tx.execute("INSERT INTO projection_checkpoints VALUES(?,?) ON CONFLICT(item_id) DO UPDATE SET value=excluded.value",params![item_id,value])?;
        tx.commit()?;
        Ok(())
    }
    pub fn acknowledge_effect_fenced(&self, id: &str, owner: &str) -> Result<()> {
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        check(&tx, owner)?;
        if tx.execute("UPDATE outbox SET done=1,error=NULL WHERE id=?", [id])? != 1 {
            bail!("unknown effect");
        }
        tx.commit()?;
        Ok(())
    }
}

impl Store {
    /// Renew only the still-held, unexpired token. Never reacquire within an effect pass.
    pub fn renew_projection_lease(&self, owner: &str, ttl_ms: u64) -> Result<()> {
        if ttl_ms == 0 {
            bail!("positive lease TTL required");
        }
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        check(&tx, owner)?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_millis();
        let expiry = now
            .checked_add(u128::from(ttl_ms))
            .ok_or_else(|| anyhow::anyhow!("lease overflow"))?;
        let expiry = i64::try_from(expiry)?;
        tx.execute(
            "UPDATE projection_lease SET expires=? WHERE id=1 AND owner=?",
            params![expiry, owner],
        )?;
        tx.commit()?;
        Ok(())
    }
}
