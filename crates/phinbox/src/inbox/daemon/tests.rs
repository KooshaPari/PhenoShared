//! Integration tests for the inbox daemon.

use super::*;
use crate::inbox::unix_now_ms;
use std::io::{BufRead, BufReader, Write};
use std::net::{Ipv4Addr, TcpListener, TcpStream};
use std::sync::atomic::Ordering;
use std::thread;
use std::time::Duration;

#[test]
fn start_stop_roundtrip() {
    let tmp = tempfile::tempdir().unwrap();
    let port = pick_unused_port().expect("pick port");
    // Brief settling time to avoid the kernel's TIME_WAIT race.
    thread::sleep(Duration::from_millis(50));
    let cfg = DaemonConfig {
        inbox_root: tmp.path().to_path_buf(),
        port,
        bind: IpAddr::V4(Ipv4Addr::LOCALHOST),
        notify: NotifyChannels::default(),
        enable_tray: false,
    };
    let handle = start_daemon(cfg).unwrap();
    assert_eq!(handle.port, port);
    // Health check (retry until the listener is ready)
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), handle.port);
    let deadline = std::time::Instant::now() + Duration::from_secs(5);
    let mut stream = None;
    while std::time::Instant::now() < deadline {
        match TcpStream::connect(addr) {
            Ok(s) => {
                stream = Some(s);
                break;
            }
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
    assert!(status.contains("200"), "expected HTTP/1.1 200, got: {status}");
    handle.stop().unwrap();
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
    let port = pick_unused_port().expect("no free port");
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
    // Bind to the port so is_port_live() returns true.
    let _hold = TcpListener::bind(SocketAddr::new(
        IpAddr::V4(Ipv4Addr::LOCALHOST),
        port,
    ))
    .expect("bind test port");
    let url = live_url(&dir, None);
    assert!(url.is_some(), "live_url should accept a live socket");
    assert!(url.unwrap().contains(&format!(":{port}")));
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

fn pick_unused_port() -> Option<u16> {
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), 0);
    let l = TcpListener::bind(addr).ok()?;
    let p = l.local_addr().ok()?.port();
    drop(l);
    Some(p)
}
