//! Integration tests for [`settly::reloadable`] (ported from
//! pheno-runtime-config per config-consolidation plan, phenotype-org-audits #72).
//!
//! Tests the [`Reloadable<T>`] trait and [`ArcReloadable<T>`] implementation
//! with concurrent readers, watch channels, and large values.

use std::sync::atomic::{AtomicUsize, Ordering};

use settly::reloadable::{ArcReloadable, Reloadable};

#[test]
fn concurrent_readers_no_data_race() {
    let r = ArcReloadable::new(0usize);
    const READERS: usize = 8;
    const ITERS: usize = 1000;
    let counter = AtomicUsize::new(0);

    std::thread::scope(|s| {
        for _ in 0..READERS {
            s.spawn(|| {
                for _ in 0..ITERS {
                    let _ = *r.current();
                    counter.fetch_add(1, Ordering::Relaxed);
                }
            });
        }
        // Writer in parallel
        for i in 0..100 {
            let _ = r.reload(i);
        }
    });

    assert_eq!(counter.load(Ordering::Relaxed), READERS * ITERS);
}

#[tokio::test]
async fn watch_notifies_all_subscribers() {
    let r = ArcReloadable::new("init".to_string());
    let mut rx1 = r.watch();
    let mut rx2 = r.watch();

    // First reload: both subscribers should see "update1"
    r.reload("update1".to_string()).unwrap();
    assert!(rx1.changed().await.is_ok());
    assert!(rx2.changed().await.is_ok());
    assert_eq!(&**rx1.borrow(), "update1");
    assert_eq!(&**rx2.borrow(), "update1");

    // Second reload: both subscribers should see "update2"
    r.reload("update2".to_string()).unwrap();
    assert!(rx1.changed().await.is_ok());
    assert!(rx2.changed().await.is_ok());
    assert_eq!(&**rx1.borrow(), "update2");
    assert_eq!(&**rx2.borrow(), "update2");
}

#[test]
fn reload_large_struct() {
    #[derive(Debug, Clone, PartialEq)]
    struct LargeConfig {
        values: Vec<u64>,
        labels: Vec<String>,
    }

    let initial = LargeConfig {
        values: (0..1000).collect(),
        labels: (0..100).map(|i| format!("label-{}", i)).collect(),
    };

    let r = ArcReloadable::new(initial);
    let current = r.current();
    assert_eq!(current.values.len(), 1000);
    assert_eq!(current.labels.len(), 100);

    let new = LargeConfig {
        values: (500..1500).collect(),
        labels: (100..200).map(|i| format!("label-{}", i)).collect(),
    };
    r.reload(new).unwrap();

    let updated = r.current();
    assert_eq!(updated.values[0], 500);
    assert_eq!(updated.labels[0], "label-100");
}
