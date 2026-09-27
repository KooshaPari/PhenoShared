//! Integration tests for the inbox daemon.

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::{Ipv4Addr, TcpListener, TcpStream},
    sync::atomic::Ordering,
    thread,
    time::Duration,
};

use super::*;
use crate::inbox::unix_now_ms;

#[test]
fn start_stop_roundtrip() {
    let tmp = tempfile::tempdir().unwrap();
    // Bind port 0 and use the port the daemon actually got. Picking a port by
    // binding and immediately releasing it is a TOCTOU race against every
    // other process on the box ("is it free?" is answered before the daemon
    // rebinds it); an ephemeral bind inside `start_daemon` has no such window.
    let cfg = DaemonConfig {
        inbox_root: tmp.path().to_path_buf(),
        port: 0,
        bind: IpAddr::V4(Ipv4Addr::LOCALHOST),
        notify: NotifyChannels::default(),
        enable_tray: false,
    };
    let handle = start_daemon(cfg).unwrap();
    assert_ne!(handle.port, 0, "daemon must report the port it bound");
    // Health check. `start_daemon` binds the listener before returning, so the
    // kernel queues this connection even before the accept thread runs; the
    // retry loop is only a safety net for a partially started daemon.
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), handle.port);
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    let mut stream = None;
    while std::time::Instant::now() < deadline {
        match TcpStream::connect(addr) {
            Ok(s) => {
                stream = Some(s);
                break;
            },
            Err(_) => thread::sleep(Duration::from_millis(50)),
        }
    }
    let mut stream = stream.expect("daemon did not start listening within 5s");
    stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        .unwrap();
    stream.flush().unwrap();
    let mut reader = BufReader::new(&stream);
    let mut status = String::new();
    let n = reader.read_line(&mut status).unwrap();
    assert!(n > 0, "no response from daemon: empty read");
    assert!(
        status.contains("200"),
        "expected HTTP/1.1 200, got: {status}"
    );
    handle.stop().unwrap();
    thread::sleep(Duration::from_millis(200));
}

/// Deterministic regression for the intermittent `start_stop_roundtrip`
/// failure (`ConnectionReset` / "empty read").
///
/// The accept loop needs a non-blocking listener to poll `shutdown`, and on
/// BSD/macOS `accept()` makes the accepted socket *inherit* `O_NONBLOCK`
/// (Linux's `accept()` does not). A non-blocking socket ignores
/// `SO_RCVTIMEO`, so the handler's first `read()` returned `EAGAIN` whenever
/// the client's request bytes had not landed yet: the connection was dropped
/// with no response and the client observed EOF or ECONNRESET. Whether that
/// happened depended on winning a millisecond-scale race against the client's
/// `write()`, which is why it only showed up intermittently.
///
/// A client that connects and then waits before sending makes the race
/// deterministic — this fails 100% of the time against the defect.
#[test]
fn slow_client_still_gets_a_response() {
    let tmp = tempfile::tempdir().unwrap();
    let handle = start_daemon_on(tmp.path());
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), handle.port);

    let mut stream = TcpStream::connect(addr).expect("connect daemon");
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    // Give the accept loop time to accept the connection *before* any request
    // bytes exist, which is exactly the window the flake depended on.
    thread::sleep(Duration::from_millis(300));
    stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        .expect("write request");
    stream.flush().unwrap();

    let mut reader = BufReader::new(&stream);
    let mut status = String::new();
    let n = reader
        .read_line(&mut status)
        .expect("a slow client must not be dropped");
    assert!(n > 0, "no response from daemon: empty read");
    assert!(
        status.contains("200"),
        "expected HTTP/1.1 200, got: {status}"
    );

    let _ = handle.stop();
    thread::sleep(Duration::from_millis(200));
}

// ---- v0.9.1: HTTP status / answer-integrity regressions ----
//
// Three defects were audited live against a running daemon:
//   1. every route answered `200 OK` because the status was computed and then discarded
//      (`write_response(&mut stream, 200, ...)` hardcoded);
//   2. a second POST silently overwrote an answer that was already recorded;
//   3. an empty or partial body was recorded as a successful answer.
// The tests below pin the wire behaviour, not the internals.

/// Start a daemon on a free port over `root` and wait until it accepts.
fn start_daemon_on(root: &std::path::Path) -> DaemonHandle {
    // `port: 0` lets the kernel pick; the daemon reports what it bound. See
    // `start_stop_roundtrip` for why picking a port first is racy.
    let cfg = DaemonConfig {
        inbox_root: root.to_path_buf(),
        port: 0,
        bind: IpAddr::V4(Ipv4Addr::LOCALHOST),
        notify: NotifyChannels::default(),
        enable_tray: false,
    };
    let handle = start_daemon(cfg).expect("start daemon");
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), handle.port);
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    while std::time::Instant::now() < deadline {
        if TcpStream::connect(addr).is_ok() {
            return handle;
        }
        thread::sleep(Duration::from_millis(20));
    }
    panic!("daemon did not start listening within 5s");
}

/// Raw HTTP round trip: write `raw`, read to EOF (the daemon always closes).
/// A read timeout keeps a regression from hanging the suite.
fn http_roundtrip(port: u16, raw: &str) -> String {
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port);
    let mut stream = TcpStream::connect(addr).expect("connect daemon");
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    stream.write_all(raw.as_bytes()).unwrap();
    stream.flush().unwrap();
    let mut out = String::new();
    let _ = stream.read_to_string(&mut out);
    out
}

fn http_get(port: u16, path: &str) -> String {
    http_roundtrip(
        port,
        &format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"),
    )
}

fn http_post(port: u16, path: &str, body: &str) -> String {
    http_roundtrip(
        port,
        &format!(
            "POST {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: {}\r\nConnection: \
             close\r\n\r\n{body}",
            body.len()
        ),
    )
}

/// First status line of a response, e.g. `HTTP/1.1 404 Not Found`.
fn status_line(resp: &str) -> &str {
    resp.lines().next().unwrap_or_default().trim_end()
}

/// Queue a pending `Text` request under `root`.
fn enqueue_text(root: &std::path::Path, id: &str) {
    enqueue_text_expiring(root, id, unix_now_ms() + 600_000);
}

/// Queue a pending `Text` request under `root` with an explicit TTL.
fn enqueue_text_expiring(root: &std::path::Path, id: &str, expires_at_ms: u64) {
    use crate::{
        inbox::{enqueue, PendingRequest, RequestOrigin},
        spec::{FieldSpec, PromptSpec, Urgency},
    };
    let spec = PromptSpec {
        details: None,
        title: "Probe".into(),
        question: "?".into(),
        field: FieldSpec::Text {
            label: "Name".into(),
            default: None,
            placeholder: None,
            max_length: None,
            secret: false,
            pattern: None,
        },
        notes: None,
        buttons: None,
        urgency: Urgency::Info,
        timeout_secs: 600,
        request_id: Some(id.into()),
    };
    let mut req = PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        },
    );
    req.expires_at_ms = expires_at_ms;
    enqueue(root, &req).expect("enqueue");
}

/// Expiry must hold at the HTTP answer surface, not only in the daemon's
/// sweeper: an expired request is reported as gone (410) and is never
/// archived as answered. Whether the sweeper or the answer attempt settles
/// the state, the operator-visible outcome is the same.
#[test]
fn http_expired_request_is_not_answerable() {
    use crate::inbox::{answered_dir, load, RequestState};

    let tmp = tempfile::tempdir().unwrap();
    let handle = start_daemon_on(tmp.path());
    let port = handle.port;
    enqueue_text_expiring(tmp.path(), "stale-http", 1);

    // The form page reports the expiry instead of offering a live form.
    assert_eq!(
        status_line(&http_get(port, "/inbox/stale-http")),
        "HTTP/1.1 410 Gone",
        "an expired request must not render an answerable form"
    );
    // A late POST is refused, exactly like an already-finalized request is.
    let post = http_post(port, "/inbox/stale-http/answer", "value=late&confirm=ok");
    assert_eq!(
        status_line(&post),
        "HTTP/1.1 410 Gone",
        "a late POST must be refused: {post}"
    );

    let req = load(tmp.path(), "stale-http").unwrap();
    assert_eq!(req.state, RequestState::Expired);
    assert!(req.response.is_none(), "no answer may be recorded");
    assert!(
        !answered_dir(tmp.path()).join("stale-http.json").exists(),
        "an expired request must not be archived as answered"
    );

    let _ = handle.stop();
    thread::sleep(Duration::from_millis(200));
}

/// Defect 1: the status each route decided on must reach the wire.
#[test]
fn http_routes_return_their_intended_status() {
    let tmp = tempfile::tempdir().unwrap();
    let handle = start_daemon_on(tmp.path());
    let port = handle.port;

    assert_eq!(status_line(&http_get(port, "/health")), "HTTP/1.1 200 OK");
    assert_eq!(
        status_line(&http_get(port, "/nope")),
        "HTTP/1.1 404 Not Found"
    );
    assert_eq!(
        status_line(&http_get(port, "/inbox/definitely-missing")),
        "HTTP/1.1 404 Not Found"
    );
    // Cancelling is POST-only; a GET must say so instead of pretending 200.
    assert_eq!(
        status_line(&http_get(port, "/shutdown")),
        "HTTP/1.1 403 Forbidden"
    );
    // An unknown request id is a client error, not success.
    assert_eq!(
        status_line(&http_post(
            port,
            "/inbox/missing-id/answer",
            "value=x&confirm=ok"
        )),
        "HTTP/1.1 400 Bad Request"
    );
    // Neither GET nor POST on the answer route.
    let put = http_roundtrip(
        port,
        "PUT /inbox/missing-id/answer HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: \
         0\r\nConnection: close\r\n\r\n",
    );
    assert_eq!(status_line(&put), "HTTP/1.1 405 Method Not Allowed");

    let _ = handle.stop();
    thread::sleep(Duration::from_millis(200));
}

/// Defect 2: an already-answered request is never re-answered over HTTP, and
/// the body that arrives second is not written to disk.
#[test]
fn http_reanswer_is_refused_and_the_first_answer_stands() {
    use crate::{
        inbox::{load, RequestState},
        spec::{ElicitResponse, FieldValue},
    };

    let tmp = tempfile::tempdir().unwrap();
    let handle = start_daemon_on(tmp.path());
    let port = handle.port;
    enqueue_text(tmp.path(), "once-1");

    let first = http_post(port, "/inbox/once-1/answer", "value=alice&confirm=ok");
    assert_eq!(
        status_line(&first),
        "HTTP/1.1 302 Found",
        "the first answer should redirect: {first}"
    );

    let second = http_post(port, "/inbox/once-1/answer", "value=second&confirm=ok");
    assert_eq!(
        status_line(&second),
        "HTTP/1.1 409 Conflict",
        "a re-answer must be refused: {second}"
    );
    let third = http_post(port, "/inbox/once-1/answer", "");
    assert_eq!(status_line(&third), "HTTP/1.1 409 Conflict");

    let req = load(tmp.path(), "once-1").unwrap();
    assert_eq!(req.state, RequestState::Answered);
    match req.response {
        Some(ElicitResponse::Answered {
            value: FieldValue::Text(v),
            ..
        }) => assert_eq!(v, "alice", "the first answer must stand"),
        other => panic!("expected Answered(Text(\"alice\")), got {other:?}"),
    }

    let _ = handle.stop();
    thread::sleep(Duration::from_millis(200));
}

/// Defect 3: a body that omits the field the spec asked for is not an answer,
/// while an explicitly empty text value is one.
#[test]
fn http_partial_body_is_not_recorded_as_an_answer() {
    use crate::{
        inbox::{load, RequestState},
        spec::{ElicitResponse, FieldValue},
    };

    let tmp = tempfile::tempdir().unwrap();
    let handle = start_daemon_on(tmp.path());
    let port = handle.port;
    enqueue_text(tmp.path(), "empty-1");

    for body in ["", "confirm=ok", "notes=hi&confirm=ok"] {
        let resp = http_post(port, "/inbox/empty-1/answer", body);
        assert_eq!(
            status_line(&resp),
            "HTTP/1.1 400 Bad Request",
            "body {body:?} must not be accepted: {resp}"
        );
        let req = load(tmp.path(), "empty-1").unwrap();
        assert_eq!(
            req.state,
            RequestState::Pending,
            "a refused body must leave the request answerable"
        );
        assert!(req.response.is_none());
    }

    // `value=` is an explicit empty answer: the human really can mean "".
    let ok = http_post(port, "/inbox/empty-1/answer", "value=&confirm=ok");
    assert_eq!(status_line(&ok), "HTTP/1.1 302 Found");
    let req = load(tmp.path(), "empty-1").unwrap();
    match req.response {
        Some(ElicitResponse::Answered {
            value: FieldValue::Text(v),
            ..
        }) => assert!(v.is_empty()),
        other => panic!("expected Answered(Text(\"\")), got {other:?}"),
    }

    let _ = handle.stop();
    thread::sleep(Duration::from_millis(200));
}

// ---- v0.5.1: tray-open regressions ----

#[test]
fn live_url_returns_none_when_no_lockfile() {
    let dir = tempdir_v051();
    assert!(live_url(&dir, None).is_none());
    assert!(read_lockfile(&dir).is_none());
}

#[test]
fn live_url_rejects_stale_lockfile() {
    let dir = tempdir_v051();
    let payload = LockfilePayload {
        root: dir.clone(),
        port: 1,
        bind: IpAddr::V4(Ipv4Addr::LOCALHOST),
        booted_at_ms: unix_now_ms(),
        ipc_sock: None,
    };
    std::fs::write(
        dir.join(lockfile::LOCKFILE_NAME),
        serde_json::to_vec(&payload).unwrap(),
    )
    .unwrap();
    assert!(live_url(&dir, None).is_none());
}

#[test]
fn live_url_accepts_running_daemon() {
    let dir = tempdir_v051();
    // Bind first, then advertise the port we actually hold in the lockfile.
    // `pick_unused_port()` would release the port before `live_url` probes it.
    let hold = TcpListener::bind(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 0))
        .expect("bind test port");
    let port = hold.local_addr().expect("local_addr").port();
    let payload = LockfilePayload {
        root: dir.clone(),
        port,
        bind: IpAddr::V4(Ipv4Addr::LOCALHOST),
        booted_at_ms: unix_now_ms(),
        ipc_sock: None,
    };
    std::fs::write(
        dir.join(lockfile::LOCKFILE_NAME),
        serde_json::to_vec(&payload).unwrap(),
    )
    .unwrap();
    let url = live_url(&dir, None);
    assert!(url.is_some(), "live_url should accept a live socket");
    assert!(url.unwrap().contains(&format!(":{port}")));
    drop(hold);
}

#[test]
fn live_url_respects_bind_filter() {
    let dir = tempdir_v051();
    let payload = LockfilePayload {
        root: dir.clone(),
        port: 1,
        bind: IpAddr::V4(Ipv4Addr::new(10, 0, 0, 1)),
        booted_at_ms: unix_now_ms(),
        ipc_sock: None,
    };
    std::fs::write(
        dir.join(lockfile::LOCKFILE_NAME),
        serde_json::to_vec(&payload).unwrap(),
    )
    .unwrap();
    assert!(live_url(&dir, Some(IpAddr::V4(Ipv4Addr::LOCALHOST))).is_none());
    assert!(
        live_url(&dir, Some(IpAddr::V4(Ipv4Addr::new(10, 0, 0, 1)))).is_none(),
        "is_port_live should reject the non-listening port"
    );
}

/// Scratch directory under /tmp for v0.5.1 tests.
fn tempdir_v051() -> std::path::PathBuf {
    use std::sync::atomic::AtomicU64;
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let mut p = std::env::temp_dir();
    p.push(format!(
        "phinbox-v0.5.1-{}-{}-{}",
        std::process::id(),
        unix_now_ms(),
        n
    ));
    std::fs::create_dir_all(&p).unwrap();
    p
}
