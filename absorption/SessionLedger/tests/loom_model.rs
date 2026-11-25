//! Loom permutation models for C00 L7 concurrency safety.
//!
//! Enabled only with `RUSTFLAGS='--cfg loom'` (see `.github/workflows/loom-smoke.yml`,
//! `.github/workflows/loom-permutation.yml`, and `docs/ops/concurrency-safety.md`).
//! The loom crate is a `[target.'cfg(loom)'.dev-dependencies]` entry so default
//! `cargo test` never builds it.
//!
//! Covers cancel + bounded capacity, `sync_channel`-style `try_send`, broadcast/SSE
//! epoch fan-out (single and multi-bump), tokio-shaped mpsc watcher→consumer,
//! mpsc drain → broadcast publish, triple SSE subscriber fan-out, full
//! watcher→mpsc→broadcast→SSE pipeline permutations, and cancel-guarded epoch
//! publication. Live tokio ports live in `tests/daemon_graph_tokio.rs`
//! ([`docs/ops/daemon-graph-hard.md`]); process-level HTTP SSE soak under loom
//! remains unpaid.

#[cfg(not(loom))]
#[test]
fn loom_cfg_not_enabled_documents_soft_lane() {
    // Discoverable under default `cargo test` without pulling loom.
    eprintln!("skip: loom_model requires RUSTFLAGS=--cfg loom (soft CI: loom-smoke.yml)");
}

#[cfg(loom)]
mod loom_perm {
    use loom::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
    use loom::sync::mpsc;
    use loom::sync::Arc;
    use loom::thread;

    /// Two producers race a shared capacity counter under cooperative cancel.
    /// Loom explores interleavings; the assert is timing-independent.
    #[test]
    fn cancel_and_capacity_conserve() {
        loom::model(|| {
            const CAPACITY: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let reserved = Arc::new(AtomicUsize::new(0));

            let mut joins = Vec::new();
            for _ in 0..2 {
                let cancel = Arc::clone(&cancel);
                let reserved = Arc::clone(&reserved);
                joins.push(thread::spawn(move || {
                    for _ in 0..4 {
                        if cancel.load(Ordering::Acquire) {
                            return;
                        }
                        let mut prev = reserved.load(Ordering::Acquire);
                        loop {
                            if prev >= CAPACITY {
                                return;
                            }
                            match reserved.compare_exchange(
                                prev,
                                prev + 1,
                                Ordering::AcqRel,
                                Ordering::Acquire,
                            ) {
                                Ok(_) => break,
                                Err(current) => prev = current,
                            }
                        }
                    }
                }));
            }

            cancel.store(true, Ordering::Release);
            for join in joins {
                join.join().unwrap();
            }
            assert!(
                reserved.load(Ordering::Acquire) <= CAPACITY,
                "reserved slots must not exceed capacity under loom interleavings"
            );
        });
    }

    /// Loom port of `race_model`'s bounded `try_send` contract: at most `CAPACITY`
    /// messages may be buffered; cancel forbids new reservations.
    #[test]
    fn bounded_try_send_respects_capacity() {
        loom::model(|| {
            const CAPACITY: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let buffered = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let producer = {
                let cancel = Arc::clone(&cancel);
                let buffered = Arc::clone(&buffered);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = buffered.load(Ordering::Acquire);
                        if prev >= CAPACITY {
                            break;
                        }
                        if buffered
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            producer.join().unwrap();
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                buffered.fetch_sub(1, Ordering::AcqRel);
            }

            assert!(buffered.load(Ordering::Acquire) <= CAPACITY);
            assert!(drained <= CAPACITY);
        });
    }

    /// Models SSE broadcast fan-out: one epoch bump is observed by each subscriber
    /// without exceeding the publisher's generation count.
    #[test]
    fn broadcast_epoch_fans_out_to_subscribers() {
        loom::model(|| {
            let epoch = Arc::new(AtomicUsize::new(0));
            let sub_a = Arc::new(AtomicUsize::new(0));
            let sub_b = Arc::new(AtomicUsize::new(0));

            let publisher = {
                let epoch = Arc::clone(&epoch);
                thread::spawn(move || {
                    epoch.store(1, Ordering::Release);
                })
            };

            let reader_a = {
                let epoch = Arc::clone(&epoch);
                let sub_a = Arc::clone(&sub_a);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    if current > 0 {
                        sub_a.store(current, Ordering::Release);
                    }
                })
            };

            let reader_b = {
                let epoch = Arc::clone(&epoch);
                let sub_b = Arc::clone(&sub_b);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    if current > 0 {
                        sub_b.store(current, Ordering::Release);
                    }
                })
            };

            publisher.join().unwrap();
            reader_a.join().unwrap();
            reader_b.join().unwrap();

            let epoch_final = epoch.load(Ordering::Acquire);
            assert!(sub_a.load(Ordering::Acquire) <= epoch_final);
            assert!(sub_b.load(Ordering::Acquire) <= epoch_final);
        });
    }

    /// Watcher pipeline: bounded enqueue between scan and broadcast; drained
    /// broadcast count matches dequeued items.
    #[test]
    fn watcher_pipeline_bounded_enqueue_under_cancel() {
        loom::model(|| {
            const QUEUE_CAP: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let queued = Arc::new(AtomicUsize::new(0));
            let broadcast = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let scanner = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= QUEUE_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            scanner.join().unwrap();
            cancel.store(true, Ordering::Release);
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                queued.fetch_sub(1, Ordering::AcqRel);
                broadcast.fetch_add(1, Ordering::AcqRel);
            }

            assert!(queued.load(Ordering::Acquire) <= QUEUE_CAP);
            assert_eq!(broadcast.load(Ordering::Acquire), drained);
        });
    }

    /// Multi-bump SSE epoch: each published bundle bumps generation; subscribers
    /// never observe a value above the publisher's final epoch.
    #[test]
    fn broadcast_epoch_monotonic_under_multi_bump() {
        loom::model(|| {
            let epoch = Arc::new(AtomicUsize::new(0));
            let sub_a = Arc::new(AtomicUsize::new(0));
            let sub_b = Arc::new(AtomicUsize::new(0));

            let publisher = {
                let epoch = Arc::clone(&epoch);
                thread::spawn(move || {
                    for bump in 1..=3usize {
                        epoch.store(bump, Ordering::Release);
                    }
                })
            };

            let reader_a = {
                let epoch = Arc::clone(&epoch);
                let sub_a = Arc::clone(&sub_a);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    if current > 0 {
                        sub_a.store(current, Ordering::Release);
                    }
                })
            };

            let reader_b = {
                let epoch = Arc::clone(&epoch);
                let sub_b = Arc::clone(&sub_b);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    if current > 0 {
                        sub_b.store(current, Ordering::Release);
                    }
                })
            };

            publisher.join().unwrap();
            reader_a.join().unwrap();
            reader_b.join().unwrap();

            let epoch_final = epoch.load(Ordering::Acquire);
            assert!(epoch_final <= 3);
            assert!(sub_a.load(Ordering::Acquire) <= epoch_final);
            assert!(sub_b.load(Ordering::Acquire) <= epoch_final);
        });
    }

    /// Daemon-graph pipeline: watcher drain publishes one SSE epoch bump per
    /// dequeued path; broadcast count matches drained items.
    #[test]
    fn watcher_drain_bumps_sse_epoch_per_item() {
        loom::model(|| {
            const QUEUE_CAP: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let queued = Arc::new(AtomicUsize::new(0));
            let epoch = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let scanner = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= QUEUE_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            scanner.join().unwrap();
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                queued.fetch_sub(1, Ordering::AcqRel);
                epoch.fetch_add(1, Ordering::AcqRel);
            }

            assert!(queued.load(Ordering::Acquire) <= QUEUE_CAP);
            assert_eq!(epoch.load(Ordering::Acquire), drained);
        });
    }

    /// Cancel forbids new watcher reservations; SSE epoch matches drained items
    /// and post-cancel producers cannot grow the queue.
    #[test]
    fn daemon_graph_pipeline_conserves_under_cancel() {
        loom::model(|| {
            const QUEUE_CAP: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let queued = Arc::new(AtomicUsize::new(0));
            let epoch = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let scanner = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= QUEUE_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            let cancel_setter = {
                let cancel = Arc::clone(&cancel);
                thread::spawn(move || {
                    cancel.store(true, Ordering::Release);
                })
            };

            scanner.join().unwrap();
            cancel_setter.join().unwrap();
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                queued.fetch_sub(1, Ordering::AcqRel);
                epoch.fetch_add(1, Ordering::AcqRel);
            }

            let post_cancel_producer = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                thread::spawn(move || {
                    if cancel.load(Ordering::Acquire) {
                        return;
                    }
                    let prev = queued.load(Ordering::Acquire);
                    if prev >= QUEUE_CAP {
                        return;
                    }
                    let _ = queued.compare_exchange(
                        prev,
                        prev + 1,
                        Ordering::AcqRel,
                        Ordering::Acquire,
                    );
                })
            };
            post_cancel_producer.join().unwrap();

            assert!(queued.load(Ordering::Acquire) <= QUEUE_CAP);
            assert_eq!(epoch.load(Ordering::Acquire), drained);
        });
    }

    /// Tokio-shaped mpsc: watcher enqueues on a bounded channel; drain conserves
    /// capacity under cancel races (sequential consumer — avoids loom mpsc explosion).
    #[test]
    fn daemon_mpsc_watcher_to_consumer_conserve() {
        loom::model(|| {
            const MPSC_CAP: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let reserved = Arc::new(AtomicUsize::new(0));
            let consumed = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let watcher = {
                let cancel = Arc::clone(&cancel);
                let reserved = Arc::clone(&reserved);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = reserved.load(Ordering::Acquire);
                        if prev >= MPSC_CAP {
                            break;
                        }
                        if reserved
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            let cancel_setter = {
                let cancel = Arc::clone(&cancel);
                thread::spawn(move || {
                    cancel.store(true, Ordering::Release);
                })
            };

            watcher.join().unwrap();
            cancel_setter.join().unwrap();
            drop(tx);

            while rx.try_recv().is_ok() {
                reserved.fetch_sub(1, Ordering::AcqRel);
                consumed.fetch_add(1, Ordering::AcqRel);
            }

            assert!(reserved.load(Ordering::Acquire) <= MPSC_CAP);
            assert!(consumed.load(Ordering::Acquire) <= MPSC_CAP);
        });
    }

    /// ETL consumer contract: each mpsc drain publishes one broadcast bump.
    #[test]
    fn daemon_mpsc_drain_triggers_broadcast_publish() {
        loom::model(|| {
            const MPSC_CAP: usize = 2;
            let queued = Arc::new(AtomicUsize::new(0));
            let published = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let watcher = {
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= MPSC_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            watcher.join().unwrap();
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                queued.fetch_sub(1, Ordering::AcqRel);
                published.fetch_add(1, Ordering::AcqRel);
            }

            assert!(queued.load(Ordering::Acquire) <= MPSC_CAP);
            assert_eq!(published.load(Ordering::Acquire), drained);
        });
    }

    /// SSE bridge: three subscribers each observe a publish epoch at or below the
    /// broadcaster's final generation (tokio `broadcast` fan-out shape).
    #[test]
    fn daemon_broadcast_sse_triple_fanout() {
        loom::model(|| {
            let epoch = Arc::new(AtomicUsize::new(0));
            let sub_a = Arc::new(AtomicUsize::new(0));
            let sub_b = Arc::new(AtomicUsize::new(0));
            let sub_c = Arc::new(AtomicUsize::new(0));

            let publisher = {
                let epoch = Arc::clone(&epoch);
                thread::spawn(move || {
                    for bump in 1..=2usize {
                        epoch.store(bump, Ordering::Release);
                    }
                })
            };

            let readers: Vec<_> = [(&sub_a, "a"), (&sub_b, "b"), (&sub_c, "c")]
                .into_iter()
                .map(|(sub, _label)| {
                    let epoch = Arc::clone(&epoch);
                    let sub = Arc::clone(sub);
                    thread::spawn(move || {
                        let current = epoch.load(Ordering::Acquire);
                        if current > 0 {
                            sub.store(current, Ordering::Release);
                        }
                    })
                })
                .collect();

            publisher.join().unwrap();
            for reader in readers {
                reader.join().unwrap();
            }

            let epoch_final = epoch.load(Ordering::Acquire);
            assert!(epoch_final <= 2);
            assert!(sub_a.load(Ordering::Acquire) <= epoch_final);
            assert!(sub_b.load(Ordering::Acquire) <= epoch_final);
            assert!(sub_c.load(Ordering::Acquire) <= epoch_final);
        });
    }

    /// Full daemon graph: watcher mpsc enqueue → drain bumps broadcast epoch per
    /// path; SSE subscribers never exceed the publisher epoch (sequential drain).
    #[test]
    fn daemon_graph_mpsc_broadcast_sse_pipeline() {
        loom::model(|| {
            const MPSC_CAP: usize = 2;
            let queued = Arc::new(AtomicUsize::new(0));
            let epoch = Arc::new(AtomicUsize::new(0));
            let sub_a = Arc::new(AtomicUsize::new(0));
            let sub_b = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let watcher = {
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= MPSC_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            let reader_a = {
                let epoch = Arc::clone(&epoch);
                let sub_a = Arc::clone(&sub_a);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    sub_a.store(current, Ordering::Release);
                })
            };

            let reader_b = {
                let epoch = Arc::clone(&epoch);
                let sub_b = Arc::clone(&sub_b);
                thread::spawn(move || {
                    let current = epoch.load(Ordering::Acquire);
                    sub_b.store(current, Ordering::Release);
                })
            };

            watcher.join().unwrap();
            drop(tx);

            while rx.try_recv().is_ok() {
                queued.fetch_sub(1, Ordering::AcqRel);
                epoch.fetch_add(1, Ordering::AcqRel);
            }

            reader_a.join().unwrap();
            reader_b.join().unwrap();

            let epoch_final = epoch.load(Ordering::Acquire);
            assert!(queued.load(Ordering::Acquire) <= MPSC_CAP);
            assert!(sub_a.load(Ordering::Acquire) <= epoch_final);
            assert!(sub_b.load(Ordering::Acquire) <= epoch_final);
        });
    }

    /// Shutdown/cancel forbids new mpsc reservations after the token is set; epoch
    /// matches drained items and post-cancel watcher cannot grow the queue.
    #[test]
    fn daemon_graph_shutdown_stops_mpsc_enqueue() {
        loom::model(|| {
            const MPSC_CAP: usize = 2;
            let cancel = Arc::new(AtomicBool::new(false));
            let queued = Arc::new(AtomicUsize::new(0));
            let epoch = Arc::new(AtomicUsize::new(0));
            let (tx, rx) = mpsc::channel::<u32>();

            let watcher = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                let tx = tx.clone();
                thread::spawn(move || {
                    for id in 0..3u32 {
                        if cancel.load(Ordering::Acquire) {
                            break;
                        }
                        let prev = queued.load(Ordering::Acquire);
                        if prev >= MPSC_CAP {
                            break;
                        }
                        if queued
                            .compare_exchange(prev, prev + 1, Ordering::AcqRel, Ordering::Acquire)
                            .is_ok()
                        {
                            let _ = tx.send(id);
                        }
                    }
                })
            };

            let shutdown = {
                let cancel = Arc::clone(&cancel);
                thread::spawn(move || {
                    cancel.store(true, Ordering::Release);
                })
            };

            watcher.join().unwrap();
            shutdown.join().unwrap();
            drop(tx);

            let mut drained = 0usize;
            while rx.try_recv().is_ok() {
                drained += 1;
                queued.fetch_sub(1, Ordering::AcqRel);
                epoch.fetch_add(1, Ordering::AcqRel);
            }

            let post_shutdown_watcher = {
                let cancel = Arc::clone(&cancel);
                let queued = Arc::clone(&queued);
                thread::spawn(move || {
                    if cancel.load(Ordering::Acquire) {
                        return;
                    }
                    let prev = queued.load(Ordering::Acquire);
                    if prev >= MPSC_CAP {
                        return;
                    }
                    let _ = queued.compare_exchange(
                        prev,
                        prev + 1,
                        Ordering::AcqRel,
                        Ordering::Acquire,
                    );
                })
            };
            post_shutdown_watcher.join().unwrap();

            assert!(queued.load(Ordering::Acquire) <= MPSC_CAP);
            assert_eq!(epoch.load(Ordering::Acquire), drained);
        });
    }
}
