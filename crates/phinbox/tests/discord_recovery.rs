//! Persisted outbox and mirror identities survive failed delivery/restart.
use phinbox::management::{Action, Command, EffectKind, Item, Store, ThreadMap};

fn thread(id: &str) -> ThreadMap {
    ThreadMap {
        guild_id: "1558641659778961432".into(),
        forum_id: "1560878303286534164".into(),
        thread_id: id.into(),
        message_id: format!("message-{id}"),
    }
}

#[test]
fn failed_delivery_remains_pending_across_restart_until_explicit_receipt() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("ledger.db");
    let store = Store::open(&path).unwrap();
    store.create(Item::new("item", "Exact original")).unwrap();
    let first = store.pending_effects(10).unwrap().pop().unwrap();
    assert_eq!(first.attempts, 0);
    store
        .record_attempt(&first.id, "429 retry_after=5")
        .unwrap();
    store.bind_thread("item", thread("thread-1")).unwrap();
    drop(store);

    let reopened = Store::open(&path).unwrap();
    let retry = reopened.pending_effects(10).unwrap().pop().unwrap();
    assert_eq!(retry.id, first.id);
    assert_eq!(retry.attempts, 1);
    assert_eq!(retry.last_error.as_deref(), Some("429 retry_after=5"));
    assert_eq!(retry.thread, Some(thread("thread-1")));
    reopened.acknowledge_effect(&retry.id).unwrap();
    drop(reopened);
    assert!(Store::open(path)
        .unwrap()
        .pending_effects(10)
        .unwrap()
        .is_empty());
}

#[test]
fn thread_mapping_is_idempotent_immutable_and_not_shareable_between_items() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    store.create(Item::new("a", "First")).unwrap();
    store.create(Item::new("b", "Second")).unwrap();
    let mapping = thread("thread-a");
    store.bind_thread("a", mapping.clone()).unwrap();
    store.bind_thread("a", mapping.clone()).unwrap();
    assert!(store.bind_thread("a", thread("replacement")).is_err());
    assert!(store.bind_thread("b", mapping.clone()).is_err());
    assert!(store.bind_thread("missing", thread("other")).is_err());
    assert_eq!(store.thread("a").unwrap(), Some(mapping));
    assert!(store.thread("b").unwrap().is_none());
}

#[test]
fn workflow_close_retains_ordered_unconfirmed_effects_including_terminal_revision() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let first = store
        .create(Item::new("item", "Verbatim\n@everyone \u{03bb}"))
        .unwrap();
    let updated = store
        .apply(Command {
            event_id: "eta".into(),
            item_id: first.id.clone(),
            expected_revision: first.revision,
            actor: "operator:42".into(),
            action: Action::SetEta(Some("ETA unknown; waiting".into())),
        })
        .unwrap();
    let closed = store
        .apply(Command {
            event_id: "close".into(),
            item_id: first.id.clone(),
            expected_revision: updated.revision,
            actor: "operator:42".into(),
            action: Action::Close,
        })
        .unwrap();
    let effects = store.pending_effects(10).unwrap();
    assert_eq!(
        effects.iter().map(|e| e.revision).collect::<Vec<_>>(),
        vec![first.revision, updated.revision, closed.revision]
    );
    assert_eq!(
        effects.iter().map(|e| e.kind).collect::<Vec<_>>(),
        vec![EffectKind::Upsert, EffectKind::Upsert, EffectKind::Close]
    );
    assert!(effects
        .iter()
        .all(|e| e.item.original == "Verbatim\n@everyone \u{03bb}"));
    assert_eq!(
        effects.last().unwrap().item.eta.as_deref(),
        Some("ETA unknown; waiting")
    );
    store.acknowledge_effect(&effects[0].id).unwrap();
    assert_eq!(
        store.pending_effects(10).unwrap().len(),
        2,
        "acknowledging one operation must not drop terminal work"
    );
}

#[test]
fn projection_lease_excludes_other_connections_and_expires_at_the_boundary() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("ledger.db");
    let first = Store::open(&path).unwrap();
    let second = Store::open(&path).unwrap();
    assert!(first.acquire_projection_lease("worker-a", 100, 50).unwrap());
    assert!(!second
        .acquire_projection_lease("worker-b", 149, 50)
        .unwrap());
    second.release_projection_lease("not-the-owner").unwrap();
    assert!(!second
        .acquire_projection_lease("worker-b", 149, 50)
        .unwrap());
    assert!(second
        .acquire_projection_lease("worker-b", 150, 50)
        .unwrap());
    // The expired owner must not release its replacement's lease.
    first.release_projection_lease("worker-a").unwrap();
    assert!(!first.acquire_projection_lease("worker-a", 151, 50).unwrap());
    assert!(second
        .acquire_projection_lease("worker-b", 175, 50)
        .unwrap());
    assert!(!first.acquire_projection_lease("worker-a", 224, 50).unwrap());
    assert!(first.acquire_projection_lease("worker-a", 225, 50).unwrap());
}

#[test]
fn simultaneous_projector_lease_acquisition_has_one_winner() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("ledger.db");
    let first = Store::open(&path).unwrap();
    let second = Store::open(&path).unwrap();
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let mut handles = Vec::new();
    for (owner, store) in [("a", first), ("b", second)] {
        let barrier = barrier.clone();
        handles.push(std::thread::spawn(move || {
            barrier.wait();
            store.acquire_projection_lease(owner, 100, 100).unwrap()
        }));
    }
    assert_eq!(
        handles
            .into_iter()
            .map(|h| usize::from(h.join().unwrap()))
            .sum::<usize>(),
        1
    );
}

#[test]
fn projection_checkpoint_is_durable_per_item_and_does_not_acknowledge_delivery() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("ledger.db");
    let store = Store::open(&path).unwrap();
    store.create(Item::new("a", "First")).unwrap();
    store.create(Item::new("b", "Second")).unwrap();
    store
        .set_projection_checkpoint("a", "create-sent:nonce-123")
        .unwrap();
    assert!(store.projection_checkpoint("b").unwrap().is_none());
    drop(store);
    let reopened = Store::open(path).unwrap();
    assert_eq!(
        reopened.projection_checkpoint("a").unwrap().as_deref(),
        Some("create-sent:nonce-123")
    );
    assert_eq!(reopened.pending_effects(10).unwrap().len(), 2);
    reopened
        .set_projection_checkpoint("a", "thread-found:thread-1")
        .unwrap();
    assert_eq!(
        reopened.projection_checkpoint("a").unwrap().as_deref(),
        Some("thread-found:thread-1")
    );
}

#[test]
fn expired_or_replaced_projector_cannot_checkpoint_bind_or_acknowledge() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    store.create(Item::new("item", "Original")).unwrap();
    let effect = store.pending_effects(1).unwrap().pop().unwrap();
    assert!(store
        .acquire_projection_lease("expired-owner", 0, 1)
        .unwrap());
    assert!(store.verify_projection_lease("expired-owner").is_err());
    assert!(store
        .set_projection_checkpoint_fenced("item", "stale-create", "expired-owner")
        .is_err());
    assert!(store
        .bind_thread_fenced("item", thread("stale-thread"), "expired-owner")
        .is_err());
    assert!(store
        .acknowledge_effect_fenced(&effect.id, "expired-owner")
        .is_err());
    assert!(store.projection_checkpoint("item").unwrap().is_none());
    assert!(store.thread("item").unwrap().is_none());
    assert_eq!(store.pending_effects(10).unwrap().len(), 1);

    let now = u64::try_from(
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis(),
    )
    .unwrap();
    assert!(store
        .acquire_projection_lease("replacement-owner", now, 30_000)
        .unwrap());
    store.verify_projection_lease("replacement-owner").unwrap();
    store
        .set_projection_checkpoint_fenced("item", "new-create", "replacement-owner")
        .unwrap();
    assert!(store
        .set_projection_checkpoint_fenced("item", "overwrite", "expired-owner")
        .is_err());
    store
        .bind_thread_fenced("item", thread("new-thread"), "replacement-owner")
        .unwrap();
    store
        .acknowledge_effect_fenced(&effect.id, "replacement-owner")
        .unwrap();
    assert_eq!(
        store.projection_checkpoint("item").unwrap().as_deref(),
        Some("new-create")
    );
    assert_eq!(store.thread("item").unwrap(), Some(thread("new-thread")));
    assert!(store.pending_effects(10).unwrap().is_empty());
}
