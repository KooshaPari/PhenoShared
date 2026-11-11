//! Real loopback HTTP receipts; no live Discord requests or credentials.
#[path = "fixtures/discord/support.rs"]
mod support;
use reqwest::Method;
use serde_json::{json, Value};
use support::{
    client, fixture_server, fixture_server_checked, identity_replies, mapped_replies, mirror_config,
};

fn message_payload(raw: &str) -> Value {
    let body = raw.split_once("\r\n\r\n").unwrap().1;
    if raw
        .to_ascii_lowercase()
        .contains("content-type: multipart/form-data")
    {
        let payload = body
            .split_once("name=\"payload_json\"")
            .expect("multipart payload_json")
            .1;
        let json = payload
            .split_once("\r\n\r\n")
            .unwrap()
            .1
            .split("\r\n--")
            .next()
            .unwrap();
        serde_json::from_str(json).expect("valid native multipart payload_json")
    } else {
        serde_json::from_str(body).expect("valid native JSON payload")
    }
}

#[tokio::test]
async fn native_rest_retries_rate_limit_with_same_body_and_hides_credentials() {
    let tmp = tempfile::tempdir().unwrap();
    let (endpoint, requests, server) = fixture_server(vec![
        (429, json!({"retry_after":0.01})),
        (200, json!({"id":"123"})),
    ]);
    let client = client(&endpoint, tmp.path());
    assert!(!format!("{client:?}").contains("TEST-ONLY-SECRET-SENTINEL"));
    let body = json!({"content":"verbatim\n\u{03bb}","allowed_mentions":{"parse":[]}});
    let response = client
        .request(Method::PATCH, "/channels/123/messages/456", Some(&body))
        .await
        .unwrap();
    server.join().unwrap();
    assert_eq!(response["id"], "123");
    let captured = requests.lock().unwrap();
    assert_eq!(captured.len(), 2);
    for raw in captured.iter() {
        assert!(raw.starts_with("PATCH /api/v10/channels/123/messages/456 HTTP/1.1"));
        assert!(raw
            .to_ascii_lowercase()
            .contains("authorization: bot test-only-secret-sentinel"));
        assert_eq!(
            serde_json::from_str::<Value>(raw.split_once("\r\n\r\n").unwrap().1).unwrap(),
            body
        );
    }
}

#[tokio::test]
async fn forbidden_response_does_not_leak_token_or_raw_body_or_retry_as_success() {
    let tmp = tempfile::tempdir().unwrap();
    let (endpoint, requests, server) =
        fixture_server(vec![(403, json!({"private":"RAW-BODY-DO-NOT-EXPOSE"}))]);
    let client = client(&endpoint, tmp.path());
    let error = client
        .request(Method::GET, "/channels/123", None)
        .await
        .unwrap_err()
        .to_string();
    server.join().unwrap();
    assert!(error.contains("403"));
    assert!(!error.contains("RAW-BODY-DO-NOT-EXPOSE"));
    assert!(!error.contains("TEST-ONLY-SECRET-SENTINEL"));
    assert_eq!(requests.lock().unwrap().len(), 1);
}

#[tokio::test]
async fn exhausted_rate_limit_stays_failed_after_bounded_retry_count() {
    let tmp = tempfile::tempdir().unwrap();
    let (endpoint, requests, server) = fixture_server(vec![(429, json!({"retry_after":0.0})); 3]);
    let client = client(&endpoint, tmp.path());
    assert!(client
        .request(Method::GET, "/channels/123", None)
        .await
        .is_err());
    server.join().unwrap();
    assert_eq!(requests.lock().unwrap().len(), 3);
}

#[tokio::test]
async fn mirror_edits_same_starter_and_terminal_controls_before_locking() {
    use phinbox::{
        discord::Mirror,
        management::{Action, Command, Item, Store, ThreadMap},
    };
    let tmp = tempfile::tempdir().unwrap();
    let config = mirror_config(tmp.path());
    let mut replies = Vec::new();
    for _ in 0..2 {
        replies.extend(identity_replies(&config));
        replies.extend(mapped_replies(&config));
        replies.extend(vec![(200, json!({})); 3]);
    }
    let (endpoint, requests, server) = fixture_server(replies);
    let client = client(&endpoint, tmp.path());
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let original = "COMPLETE-VERBATIM-".repeat(300);
    let lane = "COMPLETE-LANE-".repeat(30);
    let eta = "COMPLETE-ETA-".repeat(30);
    let mut draft = Item::new("inbox:request-123", original.clone());
    draft.title = "Candidate".into();
    draft.lane = Some(lane.clone());
    draft.eta = Some(eta.clone());
    let item = store.create(draft).unwrap();
    store
        .bind_thread(
            &item.id,
            ThreadMap {
                guild_id: config.binding.guild_id.clone(),
                forum_id: config.binding.forum_id.clone(),
                thread_id: "700".into(),
                message_id: "701".into(),
            },
        )
        .unwrap();
    let mirror = Mirror::new(store.clone(), config, client).unwrap();
    assert_eq!(mirror.sync_once().await.unwrap(), 1);
    store
        .apply(Command {
            event_id: "close".into(),
            item_id: item.id.clone(),
            expected_revision: item.revision,
            actor: "operator:42".into(),
            action: Action::Close,
        })
        .unwrap();
    assert_eq!(mirror.sync_once().await.unwrap(), 1);
    server.join().unwrap();
    let captured = requests.lock().unwrap();
    for complete in [&original, &lane, &eta] {
        assert!(
            captured
                .iter()
                .any(|request| request.contains(complete.as_str())),
            "native wire silently dropped or clipped complete item/state text"
        );
    }
    let patches = captured
        .iter()
        .filter(|r| r.starts_with("PATCH "))
        .collect::<Vec<_>>();
    assert_eq!(patches.len(), 6);
    assert!(patches[1].starts_with("PATCH /api/v10/channels/700/messages/701 "));
    assert!(patches[4].starts_with("PATCH /api/v10/channels/700/messages/701 "));
    let status = message_payload(patches[4]);
    assert!(status["content"].as_str().unwrap().contains("Closed"));
    assert!(status["components"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|r| r["components"].as_array().unwrap())
        .all(|c| c["disabled"] == true));
    let locked: Value = serde_json::from_str(patches[5].split_once("\r\n\r\n").unwrap().1).unwrap();
    assert_eq!(locked["locked"], true);
    assert_eq!(locked["archived"], true);
    assert!(
        !captured.iter().any(|r| r.starts_with("POST ")),
        "mapped item must never create another thread"
    );
    assert!(store.pending_effects(100).unwrap().is_empty());
}

#[tokio::test]
async fn failed_terminal_status_edit_never_locks_or_acknowledges_the_effect() {
    use phinbox::{
        discord::Mirror,
        management::{Action, Command, Item, Store, ThreadMap},
    };
    let tmp = tempfile::tempdir().unwrap();
    let config = mirror_config(tmp.path());
    let mut replies = identity_replies(&config);
    replies.extend(mapped_replies(&config));
    replies.push((200, json!({})));
    replies.push((500, json!({"private":"not-for-errors"})));
    let (endpoint, requests, server) = fixture_server(replies);
    let client = client(&endpoint, tmp.path());
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    let item = store.create(Item::new("work", "Original")).unwrap();
    let initial = store.pending_effects(1).unwrap().pop().unwrap();
    store.acknowledge_effect(&initial.id).unwrap();
    store
        .bind_thread(
            &item.id,
            ThreadMap {
                guild_id: config.binding.guild_id.clone(),
                forum_id: config.binding.forum_id.clone(),
                thread_id: "700".into(),
                message_id: "701".into(),
            },
        )
        .unwrap();
    store
        .apply(Command {
            event_id: "close".into(),
            item_id: item.id.clone(),
            expected_revision: item.revision,
            actor: "operator:42".into(),
            action: Action::Close,
        })
        .unwrap();
    assert!(Mirror::new(store.clone(), config, client)
        .unwrap()
        .sync_once()
        .await
        .is_err());
    server.join().unwrap();
    let pending = store.pending_effects(10).unwrap();
    assert_eq!(pending.len(), 1);
    assert_eq!(pending[0].attempts, 1);
    let captured = requests.lock().unwrap();
    assert_eq!(
        captured.iter().filter(|r| r.starts_with("PATCH ")).count(),
        2
    );
    assert!(!captured.iter().any(|r| r.contains("\"locked\":true")));
}

#[tokio::test]
async fn ambiguous_remote_create_reconciles_owned_marker_without_second_post() {
    use phinbox::{
        discord::Mirror,
        management::{Item, Store},
    };
    let tmp = tempfile::tempdir().unwrap();
    let config = mirror_config(tmp.path());
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    store.create(Item::new("work", "Candidate")).unwrap();
    let mut replies = identity_replies(&config);
    // The remote accepted creation, but its result has no usable IDs. It may
    // already exist; a restart/retry must reconcile rather than post again.
    replies.push((200, json!({})));
    replies.extend(identity_replies(&config));
    replies.push((200,json!({"threads":[{"id":"700","parent_id":config.binding.forum_id,"owner_id":config.binding.application_id,"name":"phinbox:work Candidate"}]})));
    replies.push((200, json!({"threads":[],"has_more":false})));
    replies.push((200,json!([{"id":"701","author":{"id":config.binding.application_id},"embeds":[{"footer":{"text":"phinbox:work"}}]}])));
    replies.extend(mapped_replies(&config));
    replies.extend(vec![(200, json!({})); 3]);
    let observer = store.clone();
    let (endpoint, requests, server) = fixture_server_checked(replies, move |raw| {
        if raw.starts_with("POST /api/v10/channels/1560878303286534164/threads ") {
            assert_eq!(
                observer.projection_checkpoint("work").unwrap().as_deref(),
                Some("create-inflight"),
                "creation intent must be durable BEFORE POST"
            );
        }
    });
    let client = client(&endpoint, tmp.path());
    let mirror = Mirror::new(store.clone(), config, client).unwrap();
    assert!(mirror.sync_once().await.is_err());
    assert!(store.thread("work").unwrap().is_none());
    assert_eq!(store.pending_effects(10).unwrap().len(), 1);
    assert_eq!(mirror.sync_once().await.unwrap(), 1);
    server.join().unwrap();
    let captured = requests.lock().unwrap();
    assert_eq!(
        captured
            .iter()
            .filter(|r| r.starts_with("POST /api/v10/channels/1560878303286534164/threads "))
            .count(),
        1,
        "ambiguous success must never trigger blind duplicate POST"
    );
    let map = store.thread("work").unwrap().unwrap();
    assert_eq!(map.thread_id, "700");
    assert_eq!(map.message_id, "701");
    assert!(store.pending_effects(10).unwrap().is_empty());
}
