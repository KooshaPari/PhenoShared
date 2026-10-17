//! Native Gateway loopback protocol plus actual HTTP interaction acknowledgement.
#[path = "fixtures/discord/support.rs"]
#[allow(dead_code)]
mod support;
use futures_util::{SinkExt, StreamExt};
use phinbox::{
    discord::{custom_id, run_gateway, InteractionHandler},
    inbox::{enqueue, load, PendingRequest, RequestOrigin, RequestState},
    management::{Store, ThreadMap},
    ToolApproval,
};
use serde_json::{json, Value};
use std::time::Duration;
use tokio_tungstenite::tungstenite::{
    protocol::{frame::coding::CloseCode, CloseFrame},
    Message,
};

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn native_gateway_identifies_heartbeats_and_acks_management_without_answering_permission() {
    let tmp = tempfile::tempdir().unwrap();
    let mut config = support::mirror_config(tmp.path());
    config.receiver_owner = "phinbox".into();
    std::fs::write(
        &config.board_map_file,
        json!({"forum_id":config.binding.forum_id,"tag_ids":config.tags}).to_string(),
    )
    .unwrap();
    let root = tmp.path().join("inbox");
    let mut spec = ToolApproval::new("protected-test-operation").to_prompt_spec();
    spec.request_id = Some("gateway".into());
    let request = PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: "test".into(),
            process: "test-harness".into(),
            pid: 1,
            callback: None,
        },
    );
    let permission_path = enqueue(&root, &request).unwrap();
    let permission_bytes = std::fs::read(&permission_path).unwrap();
    let store = Store::open(tmp.path().join("management.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    let item = store.get("inbox:gateway").unwrap().unwrap();
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
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let websocket_url = format!("ws://{}", listener.local_addr().unwrap());
    let mut replies = support::identity_replies(&config);
    replies.push((
        200,
        json!({"id":config.binding.application_id,"interactions_endpoint_url":null}),
    ));
    replies.push((
        200,
        json!({"url":websocket_url,"session_start_limit":{"remaining":1}}),
    ));
    replies.push((204, Value::Null));
    replies.push((200, json!({})));
    let (endpoint, requests, http_server) = support::fixture_server(replies);
    let client = support::client(&endpoint, tmp.path());
    let handler = InteractionHandler::new(store.clone(), config.clone(), client).unwrap();
    let gateway = tokio::spawn(run_gateway(handler));
    let server = tokio::spawn(async move {
        let (stream, _) = listener.accept().await.unwrap();
        let mut socket = tokio_tungstenite::accept_async(stream).await.unwrap();
        socket
            .send(Message::Text(
                json!({"op":10,"d":{"heartbeat_interval":1000}})
                    .to_string()
                    .into(),
            ))
            .await
            .unwrap();
        let identify = socket.next().await.unwrap().unwrap();
        let identify: Value = serde_json::from_str(identify.to_text().unwrap()).unwrap();
        assert_eq!(identify["op"], 2);
        assert_eq!(identify["d"]["token"], "TEST-ONLY-SECRET-SENTINEL");
        socket.send(Message::Text(json!({"op":0,"t":"READY","s":1,"d":{
            "user":{"id":config.binding.application_id},"session_id":"fixture-session","resume_gateway_url":websocket_url
        }}).to_string().into())).await.unwrap();
        let heartbeat = socket.next().await.unwrap().unwrap();
        let heartbeat: Value = serde_json::from_str(heartbeat.to_text().unwrap()).unwrap();
        assert_eq!(heartbeat["op"], 1);
        socket
            .send(Message::Text(json!({"op":11}).to_string().into()))
            .await
            .unwrap();
        let millis = u64::try_from(chrono::Utc::now().timestamp_millis()).unwrap();
        let interaction_id = (((millis - 1_420_070_400_000) << 22) | 1).to_string();
        socket.send(Message::Text(json!({"op":0,"t":"INTERACTION_CREATE","s":2,"d":{
            "id":interaction_id,"application_id":config.binding.application_id,"guild_id":config.binding.guild_id,
            "channel_id":"700","type":3,"token":"fixture-interaction-token",
            "data":{"custom_id":custom_id(&item,"ack").unwrap(),"component_type":2,"values":[]},
            "member":{"user":{"id":"42","bot":false},"roles":[]},
            "message":{"id":"701","author":{"id":config.binding.application_id,"bot":true}}
        }}).to_string().into())).await.unwrap();
        let deadline = tokio::time::Instant::now() + Duration::from_secs(20);
        loop {
            if store.get(&item.id).unwrap().unwrap().acknowledged
                && requests.lock().unwrap().len() == 7
            {
                break;
            }
            assert!(
                tokio::time::Instant::now() < deadline,
                "Gateway interaction never reached actual HTTP ACK and Store CAS"
            );
            tokio::select! {
                _ = tokio::time::sleep(Duration::from_millis(10)) => {},
                incoming = socket.next() => {
                    let incoming = incoming.unwrap().unwrap();
                    if let Message::Text(text) = incoming {
                        let value: Value = serde_json::from_str(&text).unwrap();
                        assert_eq!(value["op"], 1, "unexpected native Gateway frame");
                        socket.send(Message::Text(json!({"op":11}).to_string().into())).await.unwrap();
                    }
                }
            }
        }
        {
            let captured = requests.lock().unwrap();
            let callback = captured
                .iter()
                .find(|r| r.contains("/callback "))
                .expect("native HTTP callback missing");
            assert_eq!(
                serde_json::from_str::<Value>(callback.split_once("\r\n\r\n").unwrap().1).unwrap()
                    ["type"],
                6
            );
        }
        // A permanent native authentication close must stop, not identify-loop.
        socket
            .send(Message::Close(Some(CloseFrame {
                code: CloseCode::Library(4004),
                reason: "fixture permanent close".into(),
            })))
            .await
            .unwrap();
    });
    tokio::time::timeout(Duration::from_secs(35), server)
        .await
        .unwrap()
        .unwrap();
    let stopped = tokio::time::timeout(Duration::from_secs(5), gateway)
        .await
        .unwrap()
        .unwrap();
    assert!(
        stopped.is_err(),
        "permanent Gateway close must stop receiver"
    );
    http_server.join().unwrap();
    assert_eq!(std::fs::read(permission_path).unwrap(), permission_bytes);
    let permission = load(&root, "gateway").unwrap();
    assert_eq!(permission.state, RequestState::Pending);
    assert!(permission.response.is_none());
}
