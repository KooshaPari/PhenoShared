//! Benchmarks for pheno-proc-uds
//!
//! Measures message throughput and roundtrip latency for UDS IPC.

#![cfg(unix)]

use criterion::{criterion_group, criterion_main, Criterion};
use pheno_proc_uds::{UdsServer, UdsStream};
use std::time::Duration;

/// Unique socket path for benchmarks.
fn bench_sock(name: &str) -> String {
    let dir = std::env::temp_dir();
    let id = std::process::id();
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{}/bench_uds_{}_{}_{}.sock", dir.display(), name, id, ts)
}

/// Benchmark: single-message roundtrip latency (64-byte payload).
fn bench_roundtrip_64b(c: &mut Criterion) {
    c.bench_function("uds_roundtrip_64b", |b| {
        b.iter_custom(|iters| {
            let path = bench_sock("rt64");

            // Spawn server in a dedicated tokio runtime on a background thread
            let srv_path = path.clone();
            let srv_path2 = path.clone();
            let server_handle = std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let server = UdsServer::bind(&srv_path).await.unwrap();
                    for _ in 0..iters {
                        let mut stream = server.accept().await.unwrap();
                        let msg = stream.recv_msg().await.unwrap();
                        stream.send_msg(&msg).await.unwrap();
                    }
                });
                let _ = std::fs::remove_file(&srv_path2);
            });

            // Wait for server to bind
            std::thread::sleep(Duration::from_millis(50));

            // Client runs on the caller's thread
            let start = std::time::Instant::now();
            {
                let rt2 = tokio::runtime::Runtime::new().unwrap();
                rt2.block_on(async {
                    for _ in 0..iters {
                        let mut client = UdsStream::connect(&path).await.unwrap();
                        client.send_msg("bench").await.unwrap();
                        let _ = client.recv_msg().await.unwrap();
                    }
                });
            }
            let elapsed = start.elapsed();
            let _ = server_handle.join();
            elapsed
        });
    });
}

/// Benchmark: single-message roundtrip latency (1 KB payload).
fn bench_roundtrip_1kb(c: &mut Criterion) {
    c.bench_function("uds_roundtrip_1kb", |b| {
        b.iter_custom(|iters| {
            let path = bench_sock("rt1k");
            let payload = "A".repeat(1024);

            let srv_path = path.clone();
            let srv_path2 = path.clone();
            let server_handle = std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let server = UdsServer::bind(&srv_path).await.unwrap();
                    for _ in 0..iters {
                        let mut stream = server.accept().await.unwrap();
                        let msg = stream.recv_msg().await.unwrap();
                        stream.send_msg(&msg).await.unwrap();
                    }
                });
                let _ = std::fs::remove_file(&srv_path2);
            });

            std::thread::sleep(Duration::from_millis(50));

            let start = std::time::Instant::now();
            {
                let rt2 = tokio::runtime::Runtime::new().unwrap();
                rt2.block_on(async {
                    for _ in 0..iters {
                        let mut client = UdsStream::connect(&path).await.unwrap();
                        client.send_msg(&payload).await.unwrap();
                        let _ = client.recv_msg().await.unwrap();
                    }
                });
            }
            let elapsed = start.elapsed();
            let _ = server_handle.join();
            elapsed
        });
    });
}

/// Benchmark: message throughput (1000 sequential connections, one message each).
fn bench_throughput(c: &mut Criterion) {
    c.bench_function("uds_throughput_64b_1k_msgs", |b| {
        b.iter_custom(|iters| {
            let msg_count = iters.min(1000) as usize;
            let path = bench_sock("tp64");

            let srv_path = path.clone();
            let srv_path2 = path.clone();
            let server_handle = std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let server = UdsServer::bind(&srv_path).await.unwrap();
                    for _ in 0..msg_count {
                        let mut stream = server.accept().await.unwrap();
                        let _ = stream.recv_msg().await;
                    }
                });
                let _ = std::fs::remove_file(&srv_path2);
            });

            std::thread::sleep(Duration::from_millis(50));

            let start = std::time::Instant::now();
            {
                let rt2 = tokio::runtime::Runtime::new().unwrap();
                rt2.block_on(async {
                    for _ in 0..msg_count {
                        let mut client = UdsStream::connect(&path).await.unwrap();
                        client.send_msg("data").await.unwrap();
                    }
                });
            }
            let elapsed = start.elapsed();
            let _ = server_handle.join();
            elapsed
        });
    });
}

criterion_group!(
    benches,
    bench_roundtrip_64b,
    bench_roundtrip_1kb,
    bench_throughput
);
criterion_main!(benches);
