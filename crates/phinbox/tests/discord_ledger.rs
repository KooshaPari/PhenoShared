//! Durable authority regressions independent of any Discord network connection.
use phinbox::management::{Action, Command, Item, Status, Store};

fn command(event: &str, item: &Item, action: Action) -> Command {
    Command {
        event_id: event.into(),
        item_id: item.id.clone(),
        expected_revision: item.revision,
        actor: "operator:42".into(),
        action,
    }
}

#[test]
fn replay_returns_original_receipt_without_rewinding_current_state_or_outbox() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("management.db");
    let store = Store::open(&path).unwrap();
    let initial = store
        .create(Item::new("item", "Original\nUnicode: \u{03bb}"))
        .unwrap();
    let ack = command("interaction:ack", &initial, Action::Ack);
    let receipt = store.apply(ack.clone()).unwrap();
    let current = store
        .apply(command(
            "interaction:assign",
            &receipt,
            Action::Assign("staff:7".into()),
        ))
        .unwrap();
    let before = store.pending_effects(100).unwrap().len();
    drop(store);

    let reopened = Store::open(&path).unwrap();
    assert_eq!(reopened.apply(ack).unwrap(), receipt);
    assert_eq!(reopened.get("item").unwrap().unwrap(), current);
    assert_eq!(reopened.pending_effects(100).unwrap().len(), before);
    assert_eq!(current.original, "Original\nUnicode: \u{03bb}");
}

#[test]
fn stale_revision_and_reused_event_with_changed_payload_have_no_effect() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let initial = store.create(Item::new("item", "Work")).unwrap();
    let ack = command("event", &initial, Action::Ack);
    let current = store.apply(ack.clone()).unwrap();
    let count = store.pending_effects(100).unwrap().len();

    assert!(store
        .apply(command("stale", &initial, Action::Close))
        .is_err());
    for altered in [
        Command {
            actor: "forged:other".into(),
            ..ack.clone()
        },
        Command {
            action: Action::Close,
            ..ack.clone()
        },
        Command {
            item_id: "different-item".into(),
            ..ack.clone()
        },
    ] {
        assert!(
            store.apply(altered).is_err(),
            "event identity must bind the full command"
        );
    }
    assert_eq!(store.get("item").unwrap().unwrap(), current);
    assert_eq!(store.pending_effects(100).unwrap().len(), count);
}

#[test]
fn competing_store_connections_cannot_both_accept_the_same_revision() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("ledger.db");
    let store = Store::open(&path).unwrap();
    let item = store.create(Item::new("item", "Work")).unwrap();
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let mut workers = Vec::new();
    for (id, action) in [("a", Action::Ack), ("b", Action::Defer)] {
        let writer = Store::open(&path).unwrap();
        let barrier = barrier.clone();
        let cmd = command(id, &item, action);
        workers.push(std::thread::spawn(move || {
            barrier.wait();
            writer.apply(cmd)
        }));
    }
    let successes = workers
        .into_iter()
        .map(|w| w.join().unwrap())
        .filter(Result::is_ok)
        .count();
    assert_eq!(
        successes, 1,
        "CAS must serialize independent store connections"
    );
    assert_eq!(
        store.get("item").unwrap().unwrap().revision,
        item.revision + 1
    );
    assert_eq!(store.pending_effects(100).unwrap().len(), 2);
}

#[test]
fn closed_workflow_cannot_be_reopened_by_a_fresh_command() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let item = store.create(Item::new("item", "Work")).unwrap();
    let closed = store.apply(command("close", &item, Action::Close)).unwrap();
    assert_eq!(closed.status, Status::Closed);
    assert!(store
        .apply(command("reopen", &closed, Action::SetStatus(Status::Open)))
        .is_err());
    assert!(store
        .apply(command("late-ack", &closed, Action::Ack))
        .is_err());
    assert_eq!(store.get("item").unwrap().unwrap(), closed);
}

#[test]
fn create_is_idempotent_but_source_identity_collisions_are_rejected() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let mut candidate = Item::new("stable", "Exact original");
    candidate.source_request_id = Some("request-1".into());
    let initial = store.create(candidate.clone()).unwrap();
    assert_eq!(store.create(candidate.clone()).unwrap(), initial);
    assert_eq!(store.pending_effects(100).unwrap().len(), 1);
    candidate.original.push_str(" changed");
    assert!(store.create(candidate).is_err());
    let mut other = Item::new("stable", "Exact original");
    other.source_request_id = Some("request-2".into());
    assert!(store.create(other).is_err());
    assert_eq!(store.get("stable").unwrap().unwrap(), initial);
}

#[test]
fn invalid_actor_event_or_assignment_does_not_write_a_receipt_or_effect() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let item = store.create(Item::new("item", "Work")).unwrap();
    let valid = command("event", &item, Action::Ack);
    for invalid in [
        Command {
            actor: String::new(),
            ..valid.clone()
        },
        Command {
            event_id: String::new(),
            ..valid.clone()
        },
        command("empty-assignee", &item, Action::Assign("  ".into())),
    ] {
        assert!(store.apply(invalid).is_err());
    }
    assert_eq!(store.get("item").unwrap().unwrap(), item);
    assert_eq!(store.pending_effects(100).unwrap().len(), 1);
    assert!(
        store.apply(valid).is_ok(),
        "rejected commands must not consume receipt IDs"
    );
}
