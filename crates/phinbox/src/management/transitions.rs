use super::store::sql_u64;
use super::{store::enqueue_effect, Action, Command, Item, Status, Store};
use anyhow::{bail, Result};
use rusqlite::{params, OptionalExtension, TransactionBehavior};

impl Store {
    /// Atomically compare revision, apply workflow action, record receipt/event/outbox.
    pub fn apply(&self, command: Command) -> Result<Item> {
        if command.event_id.is_empty() || command.actor.is_empty() {
            bail!("event and actor required");
        }
        let encoded = serde_json::to_string(&command)?;
        let mut c = self.connection()?;
        let tx = c.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let prior: Option<(String, String)> = tx
            .query_row(
                "SELECT command,result FROM receipts WHERE id=?",
                [&command.event_id],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .optional()?;
        if let Some((old, result)) = prior {
            if old != encoded {
                bail!("event id collision");
            }
            return Ok(serde_json::from_str(&result)?);
        }
        let body: Option<String> = tx
            .query_row(
                "SELECT body FROM items WHERE id=?",
                [&command.item_id],
                |r| r.get(0),
            )
            .optional()?;
        let mut item: Item =
            serde_json::from_str(&body.ok_or_else(|| anyhow::anyhow!("unknown item"))?)?;
        if item.revision != command.expected_revision {
            bail!(
                "revision conflict: expected {}, current {}",
                command.expected_revision,
                item.revision
            );
        }
        if item.status == Status::Closed {
            bail!("closed item is immutable");
        }
        match &command.action {
            Action::Ack => item.acknowledged = true,
            Action::Assign(actor) => {
                if actor.trim().is_empty() {
                    bail!("assignee required");
                }
                item.assignee = Some(actor.clone());
                item.status = Status::Running;
            },
            Action::Defer => item.status = Status::Deferred,
            Action::Close => item.status = Status::Closed,
            Action::SetStatus(status) => item.status = *status,
            Action::SetLane(lane) => item.lane = lane.clone(),
            Action::SetEta(eta) => item.eta = eta.clone(),
        }
        item.revision = item
            .revision
            .checked_add(1)
            .ok_or_else(|| anyhow::anyhow!("revision exhausted"))?;
        let body = serde_json::to_string(&item)?;
        tx.execute(
            "UPDATE items SET revision=?,body=? WHERE id=?",
            params![sql_u64(item.revision)?, body, item.id],
        )?;
        tx.execute(
            "INSERT INTO receipts VALUES(?,?,?)",
            params![command.event_id, encoded, body],
        )?;
        tx.execute(
            "INSERT INTO events(item_id,revision,actor,action) VALUES(?,?,?,?)",
            params![
                item.id,
                sql_u64(item.revision)?,
                command.actor,
                serde_json::to_string(&command.action)?
            ],
        )?;
        enqueue_effect(&tx, &item)?;
        tx.commit()?;
        Ok(item)
    }
}
