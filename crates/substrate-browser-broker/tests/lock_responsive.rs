//! The broker's HTTP surface must stay responsive while the lease lock is
//! contended.
//!
//! TRIPWIRE, not a reproduction. On 2026-11-09 a brokerd instance was observed
//! accepting TCP connections on its port but returning **zero bytes** to every
//! HTTP request, while a second brokerd on the same state root stayed healthy.
//! Its tokio workers were all deep in brokerd code at 0% CPU. The cause was
//! never reproduced deliberately, but the plausible mechanism is that
//! `LeaseManager::with_lock` took the cross-process lock with a **blocking**
//! `flock` called from async context, pinning a tokio worker per contended
//! request until every worker was pinned and the HTTP task could no longer be
//! scheduled.
//!
//! The lock wait is now bounded, so a contended request degrades to an error
//! instead of pinning a worker indefinitely. This test pins the property that
//! matters to a client: **the health endpoint keeps answering** while other
//! requests are stuck contending for the lock.

use std::{
    fs,
    net::TcpListener,
    process::{Child, Command, Stdio},
    time::{Duration, Instant},
};

/// Pick a free loopback port.
fn free_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
    listener.local_addr().expect("local addr").port()
}

/// A running brokerd, killed on drop.
struct Daemon {
    child: Child,
    port: u16,
}

impl Daemon {
    fn start(root: &std::path::Path, token: &str) -> Self {
        let port = free_port();
        let child = Command::new(env!("CARGO_BIN_EXE_brokerd"))
            .arg("--root")
            .arg(root)
            .arg("--bind")
            .arg(format!("127.0.0.1:{port}"))
            .arg("--token")
            .arg(token)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn brokerd");
        let daemon = Self { child, port };
        daemon.wait_until_ready();
        daemon
    }

    fn wait_until_ready(&self) {
        let deadline = Instant::now() + Duration::from_secs(20);
        while Instant::now() < deadline {
            if self.get("/healthz").is_ok() {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        panic!("brokerd did not become ready");
    }

    fn get(&self, path: &str) -> Result<u16, ()> {
        self.get_authed(path, None)
    }

    fn get_authed(&self, path: &str, token: Option<&str>) -> Result<u16, ()> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(8))
            .build()
            .map_err(|_| ())?;
        let mut request = client.get(format!("http://127.0.0.1:{}{path}", self.port));
        if let Some(token) = token {
            request = request.header("Authorization", format!("Bearer {token}"));
        }
        request.send().map(|r| r.status().as_u16()).map_err(|_| ())
    }

    fn url(&self, path: &str) -> String {
        format!("http://127.0.0.1:{}{path}", self.port)
    }
}

impl Drop for Daemon {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[test]
fn health_stays_responsive_while_the_lease_lock_is_contended() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join("broker");
    fs::create_dir_all(&root).expect("create root");
    let token = "test-token";
    let daemon = Daemon::start(&root, token);

    // Take the lease store's lock the way another process would. The broker
    // roots its LeaseManager at <root>/leases, so the store's lock file is
    // <root>/leases/leases.lock (see Broker::new).
    let leases_dir = root.join("leases");
    fs::create_dir_all(&leases_dir).expect("create leases dir");
    let lock_path = leases_dir.join("leases.lock");
    let lock_file = fs::OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(&lock_path)
        .expect("open lock file");
    fs2::FileExt::lock_exclusive(&lock_file).expect("take exclusive lock");

    // Now every request that needs the lease store contends for the lock.
    let contenders = 8;
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .expect("client");
    let handles: Vec<_> = (0..contenders)
        .map(|_| {
            let url = daemon.url("/v1/leases");
            let client = client.clone();
            let token = token.to_string();
            std::thread::spawn(move || {
                client
                    .get(&url)
                    .header("Authorization", format!("Bearer {token}"))
                    .send()
                    .map(|r| r.status().as_u16())
            })
        })
        .collect();

    // While those contend, the health endpoint must still answer promptly.
    let started = Instant::now();
    let status = daemon
        .get("/healthz")
        .expect("health must answer while the lock is held");
    let elapsed = started.elapsed();
    assert_eq!(status, 200, "health must answer 200");
    assert!(
        elapsed < Duration::from_secs(3),
        "health must answer promptly while the lock is contended, took {elapsed:?}"
    );

    // The contending requests must not hang either: they either succeed (if
    // they got the lock before we took it) or fail with a clear error.
    for handle in handles {
        match handle.join() {
            Ok(Ok(code)) => assert!(
                code == 200 || code == 401,
                "unexpected status {code} from a contended lease read"
            ),
            Ok(Err(_)) => {},
            Err(_) => panic!("a contending request thread panicked"),
        }
    }

    // Releasing the lock must restore normal service.
    let _ = fs2::FileExt::unlock(&lock_file);
    drop(lock_file);
    let status = daemon
        .get_authed("/v1/leases", Some(token))
        .expect("service recovers once the lock is free");
    assert_eq!(status, 200, "lease read must succeed once the lock is free");
}
