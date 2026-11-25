use pareto_rs::concurrent::*;
use pareto_rs::models::*;
use pareto_rs::utils::RawHarnessRecord;
use std::sync::Arc;

fn test_prices() -> Vec<ModelPricing> {
    vec![
        ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        },
        ModelPricing {
            provider: "anthropic".into(),
            model: "claude-3".into(),
            input_per_m: 3.0,
            output_per_m: 15.0,
        },
        ModelPricing {
            provider: "meta".into(),
            model: "llama-3".into(),
            input_per_m: 1.0,
            output_per_m: 4.0,
        },
    ]
}

#[tokio::test]
async fn test_integration_shared_book_concurrent_reads() {
    let book = PricingBook::shared_from_prices(test_prices());
    let mut handles = vec![];

    for i in 0..10 {
        let b = Arc::clone(&book);
        let provider = if i % 2 == 0 { "openai" } else { "anthropic" };
        handles.push(tokio::spawn(async move {
            let guard = b.read().await;
            let price = guard.get_price(provider, "gpt-4o");
            if provider == "openai" {
                assert!(price.is_some());
            } else {
                assert!(price.is_none());
            }
        }));
    }

    for h in handles {
        h.await.unwrap();
    }
}

#[tokio::test]
async fn test_integration_shared_book_concurrent_writes() {
    let book = PricingBook::shared_from_prices(vec![]);
    let mut handles = vec![];

    for i in 0..10 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let mut guard = b.write().await;
            guard.upsert(ModelPricing {
                provider: format!("provider-{}", i),
                model: "model".into(),
                input_per_m: 1.0,
                output_per_m: 2.0,
            });
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let guard = book.read().await;
    assert_eq!(guard.len(), 10);
}

#[tokio::test]
async fn test_integration_concurrent_cost_audit() {
    let book = PricingBook::shared_from_prices(test_prices());
    let records = (0..20)
        .map(|i| RawHarnessRecord {
            provider: if i % 2 == 0 {
                "openai".into()
            } else {
                "anthropic".into()
            },
            model: "gpt-4o".into(),
            input_tokens: 1000,
            output_tokens: 500,
            latency_ms: Some(100.0),
            success: true,
            timestamp: chrono::Utc::now(),
        })
        .collect();
    let agg = concurrent_cost_audit(records, book, OnUnpricedAction::Warn).await;
    assert_eq!(agg.call_count, 20);
}

#[tokio::test]
async fn test_integration_concurrent_batch_lookup() {
    let book = PricingBook::shared_from_prices(test_prices());
    let queries = vec![
        ("openai".into(), "gpt-4o".into()),
        ("anthropic".into(), "claude-3".into()),
        ("meta".into(), "llama-3".into()),
        ("unknown".into(), "model".into()),
    ];
    let results = concurrent_batch_lookup(queries, book).await;
    assert_eq!(results.len(), 4);
    assert!(
        results
            .get(&("openai".into(), "gpt-4o".into()))
            .unwrap()
            .is_some()
    );
    assert!(
        results
            .get(&("unknown".into(), "model".into()))
            .unwrap()
            .is_none()
    );
}

#[tokio::test]
async fn test_integration_concurrent_batch_upsert() {
    let book = PricingBook::shared_from_prices(vec![]);
    let updates = vec![
        ModelPricing {
            provider: "a".into(),
            model: "m1".into(),
            input_per_m: 1.0,
            output_per_m: 1.0,
        },
        ModelPricing {
            provider: "b".into(),
            model: "m2".into(),
            input_per_m: 2.0,
            output_per_m: 2.0,
        },
        ModelPricing {
            provider: "c".into(),
            model: "m3".into(),
            input_per_m: 3.0,
            output_per_m: 3.0,
        },
    ];
    let count = concurrent_batch_upsert(updates, book.clone()).await;
    assert_eq!(count, 3);
    let guard = book.read().await;
    assert_eq!(guard.len(), 3);
}

#[tokio::test]
async fn test_integration_mixed_read_write_contention() {
    let book = PricingBook::shared_from_prices(test_prices());
    let mut handles = vec![];

    // Writers
    for i in 0..5 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let mut guard = b.write().await;
            guard.upsert(ModelPricing {
                provider: format!("writer-{}", i),
                model: "model".into(),
                input_per_m: 1.0,
                output_per_m: 1.0,
            });
            tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        }));
    }

    // Readers
    for _ in 0..10 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let guard = b.read().await;
            let _ = guard.to_vec();
            tokio::time::sleep(std::time::Duration::from_millis(5)).await;
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let guard = book.read().await;
    assert!(guard.len() >= 3);
}

#[tokio::test]
async fn test_integration_concurrent_remove_and_read() {
    let book = PricingBook::shared_from_prices(test_prices());
    let mut handles = vec![];

    // Removers
    let b = Arc::clone(&book);
    handles.push(tokio::spawn(async move {
        let mut guard = b.write().await;
        guard.remove("openai", "gpt-4o");
    }));

    // Readers
    for _ in 0..5 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let guard = b.read().await;
            let _ = guard.get_price("openai", "gpt-4o");
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let guard = book.read().await;
    assert!(guard.get_price("openai", "gpt-4o").is_none());
}

#[tokio::test]
async fn test_integration_concurrent_replace_all_and_read() {
    let book = PricingBook::shared_from_prices(test_prices());
    let mut handles = vec![];

    let b = Arc::clone(&book);
    handles.push(tokio::spawn(async move {
        let mut guard = b.write().await;
        guard.replace_all(vec![ModelPricing {
            provider: "new".into(),
            model: "model".into(),
            input_per_m: 1.0,
            output_per_m: 1.0,
        }]);
    }));

    for _ in 0..5 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let guard = b.read().await;
            let _ = guard.to_vec();
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    let guard = book.read().await;
    assert_eq!(guard.len(), 1);
}

#[tokio::test]
async fn test_integration_spawn_heavy_computation() {
    let book = PricingBook::shared_from_prices(test_prices());
    let mut handles = vec![];

    for _i in 0..50 {
        let b = Arc::clone(&book);
        handles.push(tokio::spawn(async move {
            let guard = b.read().await;
            // Simulate computation
            let mut sum = 0.0;
            for _ in 0..100 {
                sum += guard
                    .get_price("openai", "gpt-4o")
                    .map(|p| p.input_per_m)
                    .unwrap_or(0.0);
            }
            assert!(sum > 0.0);
        }));
    }

    for h in handles {
        h.await.unwrap();
    }
}

#[tokio::test]
async fn test_integration_deadlock_prevention_read_before_write() {
    let book = PricingBook::shared_from_prices(test_prices());

    // Acquire read lock briefly then release
    {
        let guard = book.read().await;
        assert!(guard.get_price("openai", "gpt-4o").is_some());
    }

    // Now acquire write lock
    {
        let mut guard = book.write().await;
        guard.upsert(ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 5.0,
            output_per_m: 20.0,
        });
    }

    // Verify the update
    {
        let guard = book.read().await;
        assert_eq!(
            guard.get_price("openai", "gpt-4o").unwrap().input_per_m,
            5.0
        );
    }
}
