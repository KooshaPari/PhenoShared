use phinbox::discord::DiscordClient;
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Read, Write},
    net::TcpListener,
    sync::{Arc, Mutex},
};
pub fn fixture_server(
    replies: Vec<(u16, Value)>,
) -> (String, Arc<Mutex<Vec<String>>>, std::thread::JoinHandle<()>) {
    fixture_server_checked(replies, |_| {})
}

pub fn fixture_server_checked(
    replies: Vec<(u16, Value)>,
    check: impl Fn(&str) + Send + 'static,
) -> (String, Arc<Mutex<Vec<String>>>, std::thread::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.set_nonblocking(true).unwrap();
    let endpoint = format!("http://{}/api/v10", listener.local_addr().unwrap());
    let requests = Arc::new(Mutex::new(Vec::new()));
    let captured = requests.clone();
    let handle = std::thread::spawn(move || {
        for (status, body) in replies {
            let deadline = std::time::Instant::now() + std::time::Duration::from_secs(15);
            let mut stream = loop {
                match listener.accept() {
                    Ok((s, _)) => break s,
                    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                        assert!(
                            std::time::Instant::now() < deadline,
                            "expected HTTP request never arrived"
                        );
                        std::thread::sleep(std::time::Duration::from_millis(5));
                    },
                    Err(e) => panic!("accept: {e}"),
                }
            };
            // macOS accepted sockets inherit the nonblocking listener flag.
            stream.set_nonblocking(false).unwrap();
            stream
                .set_read_timeout(Some(std::time::Duration::from_secs(5)))
                .unwrap();
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut raw = String::new();
            let mut length = 0;
            loop {
                let mut line = String::new();
                assert_ne!(reader.read_line(&mut line).unwrap(), 0);
                if let Some((key, value)) = line.split_once(':') {
                    if key.eq_ignore_ascii_case("content-length") {
                        length = value.trim().parse().unwrap();
                    }
                }
                raw.push_str(&line);
                if line == "\r\n" {
                    break;
                }
            }
            let mut bytes = vec![0; length];
            reader.read_exact(&mut bytes).unwrap();
            raw.push_str(std::str::from_utf8(&bytes).unwrap());
            check(&raw);
            captured.lock().unwrap().push(raw);
            let payload = if status == 204 {
                String::new()
            } else {
                body.to_string()
            };
            write!(stream, "HTTP/1.1 {status} Fixture\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{payload}", payload.len()).unwrap();
            stream.flush().unwrap();
        }
    });
    (endpoint, requests, handle)
}

pub fn client(endpoint: &str, root: &std::path::Path) -> DiscordClient {
    let token = root.join("fake-discord-token");
    std::fs::write(&token, "TEST-ONLY-SECRET-SENTINEL").unwrap();
    DiscordClient::with_endpoint(endpoint, &token).unwrap()
}

pub fn mirror_config(root: &std::path::Path) -> phinbox::discord::Config {
    use std::collections::{BTreeMap, BTreeSet};
    phinbox::discord::Config {
        binding: phinbox::discord::Binding {
            persona_reference: "existing-instinct-fixture".into(),
            application_id: "1558640911297028147".into(),
            guild_id: "1558641659778961432".into(),
            forum_id: "1560878303286534164".into(),
            allowed_users: BTreeSet::from(["42".into()]),
            allowed_roles: BTreeSet::new(),
        },
        credential_file: root.join("fake-discord-token"),
        board_map_file: root.join("board.json"),
        receiver_owner: "fixture-owner".into(),
        tags: [
            "open", "running", "waiting", "deferred", "partial", "blocked",
        ]
        .into_iter()
        .enumerate()
        .map(|(i, s)| (s.into(), (100 + i).to_string()))
        .collect::<BTreeMap<_, _>>(),
    }
}

pub fn identity_replies(config: &phinbox::discord::Config) -> Vec<(u16, Value)> {
    vec![
        (200, json!({"id":config.binding.application_id,"bot":true})),
        (200, json!({"id":config.binding.application_id})),
        (
            200,
            json!({"type":15,"guild_id":config.binding.guild_id,"available_tags":config.tags.iter().map(|(name,id)|json!({"name":name,"id":id})).collect::<Vec<_>>()}),
        ),
    ]
}
pub fn mapped_replies(config: &phinbox::discord::Config) -> Vec<(u16, Value)> {
    vec![
        (
            200,
            json!({"guild_id":config.binding.guild_id,"parent_id":config.binding.forum_id,"owner_id":config.binding.application_id}),
        ),
        (200, json!({"author":{"id":config.binding.application_id}})),
    ]
}
