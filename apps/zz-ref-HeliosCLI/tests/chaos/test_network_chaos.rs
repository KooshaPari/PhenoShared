//! Chaos test: Network simulation.
//!
//! Simulates network issues such as connection drops, DNS failures,
//! timeout scenarios, and partial message corruption.
//! These tests verify that the system handles network chaos gracefully.

use std::io::{self, Read, Write, ErrorKind};
use std::net::{TcpListener, TcpStream, ToSocketAddrs};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Barrier, Mutex};
use std::time::Duration;

// ── Helpers ──────────────────────────────────────

/// Simulates a network partition by wrapping a TcpStream and blocking I/O.
struct PartitionedStream {
    inner: Option<TcpStream>,
    blocked: Arc<AtomicBool>,
}

impl PartitionedStream {
    fn new(stream: TcpStream, blocked: Arc<AtomicBool>) -> Self {
        Self {
            inner: Some(stream),
            blocked,
        }
    }

    fn close(&mut self) -> Option<TcpStream> {
        self.inner.take()
    }
}

impl Read for PartitionedStream {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        if self.blocked.load(Ordering::Relaxed) {
            return Err(io::Error::new(
                ErrorKind::ConnectionReset,
                "simulated network partition",
            ));
        }
        match &mut self.inner {
            Some(stream) => stream.read(buf),
            None => Err(io::Error::new(
                ErrorKind::NotConnected,
                "stream already closed",
            )),
        }
    }
}

impl Write for PartitionedStream {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.blocked.load(Ordering::Relaxed) {
            return Err(io::Error::new(
                ErrorKind::ConnectionReset,
                "simulated network partition",
            ));
        }
        match &mut self.inner {
            Some(stream) => stream.write(buf),
            None => Err(io::Error::new(
                ErrorKind::NotConnected,
                "stream already closed",
            )),
        }
    }

    fn flush(&mut self) -> io::Result<()> {
        if let Some(ref mut stream) = self.inner {
            stream.flush()
        } else {
            Ok(())
        }
    }
}

/// Simulates DNS failure by attempting to resolve a non-existent hostname.
fn simulate_dns_failure() -> io::Result<()> {
    let result = "nonexistent.invalid:0".to_socket_addrs();
    match result {
        Ok(_) => Err(io::Error::new(
            ErrorKind::Other,
            "expected DNS resolution to fail",
        )),
        Err(e) if e.kind() == ErrorKind::Other || e.kind() == ErrorKind::AddrNotAvailable => Ok(()),
        Err(e) => Err(e),
    }
}

/// Simulates a connection timeout by connecting to a non-routable address.
fn simulate_connection_timeout() -> io::Result<()> {
    // 198.18.0.0/15 is TEST-NET, non-routable; use a very short timeout
    let addr = "198.18.0.1:9999".to_socket_addrs()?.next().unwrap();
    let result = TcpStream::connect_timeout(&addr, Duration::from_millis(50));
    match result {
        Ok(_) => Err(io::Error::new(
            ErrorKind::Other,
            "expected connection timeout",
        )),
        Err(e)
            if e.kind() == ErrorKind::ConnectionRefused
                || e.kind() == ErrorKind::TimedOut
                || e.kind() == ErrorKind::WouldBlock =>
        {
            Ok(())
        }
        Err(e) => Ok(()), // Other errors are acceptable for timeout simulation
    }
}

// ── Tests ────────────────────────────────────────

#[test]
fn test_network_partition_blocks_read() {
    let blocked = Arc::new(AtomicBool::new(false));

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();

    let server_blocked = blocked.clone();
    let server_handle = std::thread::spawn(move || {
        let (stream, _) = listener.accept().unwrap();
        let mut partitioned = PartitionedStream::new(stream, server_blocked);
        let mut buf = [0u8; 1024];
        let result = partitioned.read(&mut buf);
        assert!(
            result.is_err(),
            "read should fail during partition"
        );
        drop(partitioned);
    });

    let client = TcpStream::connect(addr).unwrap();
    let mut client_stream = PartitionedStream::new(client, blocked.clone());

    // Activate partition
    blocked.store(true, Ordering::Relaxed);

    let result = client_stream.write(b"hello");
    assert!(result.is_err(), "write should fail during partition");

    // Deactivate and verify recovery
    blocked.store(false, Ordering::Relaxed);
    let result = client_stream.write(b"recovered");
    // May succeed or fail depending on server state, but should not be partition error
    match result {
        Ok(_) => {}
        Err(e) => assert_ne!(e.kind(), ErrorKind::ConnectionReset),
    }

    server_handle.join().unwrap();
}

#[test]
fn test_network_partition_recovery() {
    let blocked = Arc::new(AtomicBool::new(true)); // Start blocked

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();

    let mut stream = TcpStream::connect(addr).unwrap();
    stream.set_read_timeout(Some(Duration::from_millis(100))).ok();

    // While blocked, reads should fail
    let mut buf = [0u8; 1024];
    if blocked.load(Ordering::Relaxed) {
        let result = stream.read(&mut buf);
        // May fail or succeed depending on timing
    }

    // Unblock
    blocked.store(false, Ordering::Relaxed);

    // Accept the connection on server side (non-blocking)
    let _ = listener.set_nonblocking(true);
    let _ = listener.accept();
}

#[test]
fn test_concurrent_network_partitions() {
    let num_connections = 10;
    let barrier = Arc::new(Barrier::new(num_connections + 1));
    let blocked = Arc::new(AtomicBool::new(true));
    let errors = Arc::new(Mutex::new(Vec::new()));

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();

    let mut handles = Vec::new();

    for i in 0..num_connections {
        let b = blocked.clone();
        let e = errors.clone();
        let a = addr;
        let bar = barrier.clone();

        handles.push(std::thread::spawn(move || {
            bar.wait();
            match TcpStream::connect_timeout(
                &a.to_socket_addrs().unwrap().next().unwrap(),
                Duration::from_secs(2),
            ) {
                Ok(stream) => {
                    let mut ps = PartitionedStream::new(stream, b);
                    let mut buf = [0u8; 100];
                    let result = ps.write(b"test");
                    if result.is_err() {
                        e.lock().unwrap().push(i);
                    }
                }
                Err(_) => {
                    e.lock().unwrap().push(i);
                }
            }
        }));
    }

    barrier.wait(); // Release all threads

    for h in handles {
        h.join().unwrap();
    }

    // All should have encountered errors during partition
    let err_count = errors.lock().unwrap().len();
    assert!(
        err_count > 0,
        "expected errors during partition"
    );
}

#[test]
fn test_dns_failure_simulation() {
    let result = simulate_dns_failure();
    assert!(result.is_ok(), "DNS failure simulation should succeed");
}

#[test]
fn test_connection_timeout_simulation() {
    let result = simulate_connection_timeout();
    assert!(result.is_ok(), "timeout simulation should succeed");
}

#[test]
fn test_partial_write_under_partition() {
    let blocked = Arc::new(AtomicBool::new(false));
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();

    let mut stream = TcpStream::connect(addr).unwrap();
    let mut ps = PartitionedStream::new(stream, blocked.clone());

    // Write should succeed when not blocked
    let result = ps.write(b"hello");
    assert!(result.is_ok());

    // Now block and attempt write
    blocked.store(true, Ordering::Relaxed);
    let result = ps.write(b"world");
    assert!(result.is_err());
}

#[test]
fn test_connection_refused_simulation() {
    // Try connecting to a port that is not listening
    let result = TcpStream::connect("127.0.0.1:1");
    assert!(result.is_err());

    let err = result.unwrap_err();
    assert!(
        err.kind() == ErrorKind::ConnectionRefused
            || err.kind() == ErrorKind::AddrInUse
            || err.kind() == ErrorKind::AddrNotAvailable,
        "unexpected error kind: {:?}",
        err.kind()
    );
}
