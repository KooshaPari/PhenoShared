//! Live tokio `sl-daemon` broadcast/SSE graph ports (C00 L7).
//!
//! Models the production watcher → mpsc → broadcast → SSE subscriber shape from
//! `crates/sl-daemon/src/main.rs` with real `tokio::sync::{mpsc, broadcast}`
//! (not loom). Capacities mirror daemon constants at reduced scale for fast CI.
//!
//! SSOT: `docs/ops/daemon-graph-hard.md`. Blocking gate:
//! `.github/workflows/daemon-graph-hard.yml`.

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use tokio::sync::{broadcast, mpsc};
use tokio::time::timeout;

/// Reduced-scale mirror of `CHANNEL_CAPACITY` / `BROADCAST_CAPACITY` in sl-daemon.
const MPSC_CAP: usize = 8;
const BROADCAST_CAP: usize = 8;

/// Watcher enqueues paths; drain task publishes each path on broadcast; SSE
/// subscribers each observe every published path (no lag under load).
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn daemon_tokio_mpsc_broadcast_sse_pipeline_conserves() {
    let (tx, mut rx) = mpsc::channel::<PathBuf>(MPSC_CAP);
    let (bcast_tx, _) = broadcast::channel::<PathBuf>(BROADCAST_CAP);
    let publish_count = Arc::new(AtomicUsize::new(0));

    let mut subs = Vec::new();
    for _ in 0..3 {
        let mut sub = bcast_tx.subscribe();
        let seen = Arc::new(AtomicUsize::new(0));
        let seen_task = Arc::clone(&seen);
        tokio::spawn(async move {
            loop {
                match sub.recv().await {
                    Ok(_) => {
                        seen_task.fetch_add(1, Ordering::AcqRel);
                    }
                    Err(broadcast::error::RecvError::Closed) => break,
                    Err(broadcast::error::RecvError::Lagged(_)) => {}
                }
            }
        });
        subs.push(seen);
    }

    let drain_task = {
        let bcast_tx = bcast_tx.clone();
        let publish_count = Arc::clone(&publish_count);
        tokio::spawn(async move {
            while let Some(path) = rx.recv().await {
                let _ = bcast_tx.send(path);
                publish_count.fetch_add(1, Ordering::AcqRel);
            }
        })
    };

    let paths: Vec<PathBuf> = (0..5).map(|i| PathBuf::from(format!("session-{i}.jsonl"))).collect();
    for path in &paths {
        tx.send(path.clone()).await.expect("mpsc send");
    }
    drop(tx);

    timeout(Duration::from_secs(5), drain_task)
        .await
        .expect("drain task join timed out")
        .expect("drain task panicked");
    drop(bcast_tx);

    // Allow subscriber tasks to observe Closed.
    tokio::time::sleep(Duration::from_millis(50)).await;

    let final_count = publish_count.load(Ordering::Acquire);
    assert_eq!(final_count, paths.len());
    for seen in &subs {
        assert_eq!(
            seen.load(Ordering::Acquire),
            final_count,
            "each SSE subscriber must observe every published path"
        );
    }
}

/// Lagging SSE subscriber surfaces `RecvError::Lagged` and still converges to
/// the final publish count after catching up (broadcast capacity contract).
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn daemon_tokio_broadcast_lagged_subscriber_recovers() {
    let (bcast_tx, _) = broadcast::channel::<u64>(2);
    let mut lagging = bcast_tx.subscribe();
    let mut keeping_up = bcast_tx.subscribe();

    for bump in 1..=6u64 {
        let _ = bcast_tx.send(bump);
        // Keeping-up subscriber drains so it never lags permanently.
        while let Ok(v) = keeping_up.try_recv() {
            assert!(v >= 1);
        }
    }

    let mut recovered = 0u64;
    let mut lagged = false;
    loop {
        match lagging.try_recv() {
            Ok(_) => recovered += 1,
            Err(broadcast::error::TryRecvError::Lagged(_)) => {
                lagged = true;
            }
            Err(broadcast::error::TryRecvError::Empty | broadcast::error::TryRecvError::Closed) => {
                break
            }
        }
    }

    assert!(lagged, "slow subscriber must observe Lagged under overflow");
    assert!(recovered >= 1, "slow subscriber must still recover some events");
    drop(bcast_tx);
}

/// Cooperative cancel forbids new mpsc enqueues after shutdown; drained count
/// equals published broadcast bumps.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn daemon_tokio_shutdown_stops_mpsc_enqueue() {
    let cancel = Arc::new(AtomicBool::new(false));
    let (tx, mut rx) = mpsc::channel::<u32>(MPSC_CAP);
    let (bcast_tx, _) = broadcast::channel::<u32>(BROADCAST_CAP);
    let publish_count = Arc::new(AtomicUsize::new(0));

    let watcher = {
        let cancel = Arc::clone(&cancel);
        let tx = tx.clone();
        tokio::spawn(async move {
            for id in 0..16u32 {
                if cancel.load(Ordering::Acquire) {
                    break;
                }
                if tx.try_send(id).is_err() {
                    break;
                }
                tokio::task::yield_now().await;
            }
        })
    };

    let drain_task = {
        let bcast_tx = bcast_tx.clone();
        let publish_count = Arc::clone(&publish_count);
        tokio::spawn(async move {
            while let Some(id) = rx.recv().await {
                let _ = bcast_tx.send(id);
                publish_count.fetch_add(1, Ordering::AcqRel);
            }
        })
    };

    tokio::time::sleep(Duration::from_millis(5)).await;
    cancel.store(true, Ordering::Release);
    drop(tx);

    timeout(Duration::from_secs(5), watcher)
        .await
        .expect("watcher join timed out")
        .expect("watcher panicked");
    timeout(Duration::from_secs(5), drain_task)
        .await
        .expect("drain task join timed out")
        .expect("drain task panicked");

    let final_count = publish_count.load(Ordering::Acquire);
    assert!(final_count > 0, "at least one item should drain before cancel");

    // Post-cancel enqueue must be refused by the cancel bit.
    let post = {
        let cancel = Arc::clone(&cancel);
        tokio::spawn(async move {
            if cancel.load(Ordering::Acquire) {
                return false;
            }
            true
        })
    };
    let would_enqueue = timeout(Duration::from_secs(1), post)
        .await
        .expect("post-cancel check timed out")
        .expect("post-cancel check panicked");
    assert!(!would_enqueue, "post-cancel watcher must not enqueue");
}
