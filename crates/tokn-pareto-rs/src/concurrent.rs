//! ParetoRs — concurrency primitives for shared state and async hot-paths.

use crate::cost::aggregate_costs;
use crate::models::{CostAggregate, CostSnapshot, ModelPricing, OnUnpricedAction};
use crate::utils::RawHarnessRecord;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Shared pricing book protected by a `tokio::sync::RwLock`.
///
/// Provides concurrent read/write access to the model pricing database.
/// Readers are not blocked by other readers; writers get exclusive access.
pub type SharedPricingBook = Arc<RwLock<PricingBook>>;

/// The pricing book stores model pricing data and provides lookup/update operations.
#[derive(Debug, Clone, Default)]
pub struct PricingBook {
    prices: HashMap<(String, String), ModelPricing>,
    updated_at: Option<chrono::DateTime<chrono::Utc>>,
}

impl PricingBook {
    /// Create a new empty pricing book.
    pub fn new() -> Self {
        Self {
            prices: HashMap::new(),
            updated_at: None,
        }
    }

    /// Create a pricing book pre-populated with pricing data.
    pub fn from_prices(prices: Vec<ModelPricing>) -> Self {
        let map = prices
            .into_iter()
            .map(|p| ((p.provider.clone(), p.model.clone()), p))
            .collect();
        Self {
            prices: map,
            updated_at: Some(chrono::Utc::now()),
        }
    }

    /// Create a shared (Arc<RwLock<PricingBook>>) from a list of prices.
    pub fn shared_from_prices(prices: Vec<ModelPricing>) -> SharedPricingBook {
        Arc::new(RwLock::new(Self::from_prices(prices)))
    }

    /// Look up pricing for a specific provider and model.
    pub fn get_price(&self, provider: &str, model: &str) -> Option<&ModelPricing> {
        self.prices.get(&(provider.to_string(), model.to_string()))
    }

    /// Insert or update pricing for a specific model.
    pub fn upsert(&mut self, pricing: ModelPricing) -> Option<ModelPricing> {
        self.updated_at = Some(chrono::Utc::now());
        self.prices
            .insert((pricing.provider.clone(), pricing.model.clone()), pricing)
    }

    /// Remove pricing for a specific model.
    pub fn remove(&mut self, provider: &str, model: &str) -> Option<ModelPricing> {
        self.updated_at = Some(chrono::Utc::now());
        self.prices
            .remove(&(provider.to_string(), model.to_string()))
    }

    /// Bulk replace all pricing data.
    pub fn replace_all(&mut self, new_prices: Vec<ModelPricing>) {
        self.prices.clear();
        for p in new_prices {
            self.prices.insert((p.provider.clone(), p.model.clone()), p);
        }
        self.updated_at = Some(chrono::Utc::now());
    }

    /// Get the count of models in the book.
    pub fn len(&self) -> usize {
        self.prices.len()
    }

    /// Check if the book is empty.
    pub fn is_empty(&self) -> bool {
        self.prices.is_empty()
    }

    /// Get the last update timestamp.
    pub fn updated_at(&self) -> Option<chrono::DateTime<chrono::Utc>> {
        self.updated_at
    }

    /// Convert to a flat list of ModelPricing.
    pub fn to_vec(&self) -> Vec<ModelPricing> {
        self.prices.values().cloned().collect()
    }
}

// ─── Concurrent Hot-Path Functions ────────────────────────────────────────────

/// Calculate costs concurrently for a batch of harness records.
///
/// Spawns a separate tokio task for each record to parallelise cost computation.
/// Returns the aggregated cost snapshot.
pub async fn concurrent_cost_audit(
    records: Vec<RawHarnessRecord>,
    pricing_book: SharedPricingBook,
    on_unpriced: OnUnpricedAction,
) -> CostAggregate {
    let mut handles = Vec::with_capacity(records.len());

    for record in records {
        let book = Arc::clone(&pricing_book);
        let action = on_unpriced;
        let handle = tokio::spawn(async move {
            let book_guard = book.read().await;
            let key = (record.provider.clone(), record.model.clone());
            let pricing = book_guard.get_price(&record.provider, &record.model);

            match pricing {
                Some(p) => {
                    let input_cost = (record.input_tokens as f64 / 1_000_000.0) * p.input_per_m;
                    let output_cost = (record.output_tokens as f64 / 1_000_000.0) * p.output_per_m;
                    Some(CostSnapshot {
                        id: key.0.clone(),
                        provider: record.provider,
                        model: record.model,
                        input_tokens: record.input_tokens,
                        output_tokens: record.output_tokens,
                        input_cost,
                        output_cost,
                        total_cost: input_cost + output_cost,
                        latency_ms: record.latency_ms,
                        timestamp: record.timestamp,
                        routing_criteria: None,
                        routing_score: None,
                    })
                }
                None => match action {
                    OnUnpricedAction::Error => None,
                    _ => Some(CostSnapshot {
                        id: key.0,
                        provider: record.provider,
                        model: record.model,
                        input_tokens: record.input_tokens,
                        output_tokens: record.output_tokens,
                        input_cost: 0.0,
                        output_cost: 0.0,
                        total_cost: 0.0,
                        latency_ms: record.latency_ms,
                        timestamp: record.timestamp,
                        routing_criteria: None,
                        routing_score: None,
                    }),
                },
            }
        });
        handles.push(handle);
    }

    let mut snapshots = Vec::new();
    for handle in handles {
        if let Ok(Some(snapshot)) = handle.await {
            snapshots.push(snapshot);
        }
    }

    aggregate_costs(&snapshots)
}

/// Concurrently look up pricing for multiple (provider, model) pairs.
///
/// Returns a map of (provider, model) -> Option<ModelPricing>.
pub async fn concurrent_batch_lookup(
    queries: Vec<(String, String)>,
    pricing_book: SharedPricingBook,
) -> HashMap<(String, String), Option<ModelPricing>> {
    let mut handles = Vec::with_capacity(queries.len());

    for (provider, model) in queries {
        let book = Arc::clone(&pricing_book);
        let p = provider.clone();
        let m = model.clone();
        let handle = tokio::spawn(async move {
            let book_guard = book.read().await;
            let result = book_guard.get_price(&p, &m).cloned();
            ((p, m), result)
        });
        handles.push(handle);
    }

    let mut results = HashMap::new();
    for handle in handles {
        if let Ok((key, value)) = handle.await {
            results.insert(key, value);
        }
    }
    results
}

/// Concurrently update pricing for multiple models.
///
/// Returns the count of models that were updated.
pub async fn concurrent_batch_upsert(
    updates: Vec<ModelPricing>,
    pricing_book: SharedPricingBook,
) -> usize {
    let mut handles = Vec::with_capacity(updates.len());

    for pricing in updates {
        let book = Arc::clone(&pricing_book);
        let handle = tokio::spawn(async move {
            let mut book_guard = book.write().await;
            book_guard.upsert(pricing);
        });
        handles.push(handle);
    }

    let mut count = 0;
    for handle in handles {
        if handle.await.is_ok() {
            count += 1;
        }
    }
    count
}

#[cfg(test)]
mod tests {
    use super::*;

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
        ]
    }

    #[test]
    fn test_pricing_book_new() {
        let book = PricingBook::new();
        assert!(book.is_empty());
        assert_eq!(book.len(), 0);
    }

    #[test]
    fn test_pricing_book_from_prices() {
        let book = PricingBook::from_prices(test_prices());
        assert_eq!(book.len(), 2);
        assert!(book.get_price("openai", "gpt-4o").is_some());
        assert!(book.get_price("anthropic", "claude-3").is_some());
    }

    #[test]
    fn test_pricing_book_upsert() {
        let mut book = PricingBook::new();
        let p = ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        };
        assert!(book.upsert(p).is_none());
        assert_eq!(book.len(), 1);

        let p2 = ModelPricing {
            provider: "openai".into(),
            model: "gpt-4o".into(),
            input_per_m: 3.0,
            output_per_m: 12.0,
        };
        assert!(book.upsert(p2).is_some());
        assert_eq!(book.len(), 1);
        assert_eq!(book.get_price("openai", "gpt-4o").unwrap().input_per_m, 3.0);
    }

    #[test]
    fn test_pricing_book_remove() {
        let mut book = PricingBook::from_prices(test_prices());
        assert!(book.remove("openai", "gpt-4o").is_some());
        assert_eq!(book.len(), 1);
        assert!(book.get_price("openai", "gpt-4o").is_none());
    }

    #[test]
    fn test_pricing_book_replace_all() {
        let mut book = PricingBook::from_prices(test_prices());
        book.replace_all(vec![ModelPricing {
            provider: "meta".into(),
            model: "llama-3".into(),
            input_per_m: 1.0,
            output_per_m: 4.0,
        }]);
        assert_eq!(book.len(), 1);
        assert!(book.get_price("meta", "llama-3").is_some());
    }

    #[tokio::test]
    async fn test_concurrent_cost_audit() {
        let book = PricingBook::shared_from_prices(test_prices());
        let records = vec![
            RawHarnessRecord {
                provider: "openai".into(),
                model: "gpt-4o".into(),
                input_tokens: 1000,
                output_tokens: 500,
                latency_ms: Some(100.0),
                success: true,
                timestamp: chrono::Utc::now(),
            },
            RawHarnessRecord {
                provider: "anthropic".into(),
                model: "claude-3".into(),
                input_tokens: 2000,
                output_tokens: 1000,
                latency_ms: Some(150.0),
                success: true,
                timestamp: chrono::Utc::now(),
            },
            RawHarnessRecord {
                provider: "unknown".into(),
                model: "unknown-model".into(),
                input_tokens: 100,
                output_tokens: 100,
                latency_ms: None,
                success: true,
                timestamp: chrono::Utc::now(),
            },
        ];
        let agg = concurrent_cost_audit(records, book, OnUnpricedAction::Warn).await;
        assert_eq!(agg.call_count, 3);
    }

    #[tokio::test]
    async fn concurrent_cost_audit_error_excludes_unpriced_records() {
        let book = PricingBook::shared_from_prices(vec![]);
        let records = vec![RawHarnessRecord {
            provider: "unknown".into(),
            model: "unknown-model".into(),
            input_tokens: 100,
            output_tokens: 50,
            latency_ms: None,
            success: true,
            timestamp: chrono::Utc::now(),
        }];

        let aggregate = concurrent_cost_audit(records, book, OnUnpricedAction::Error).await;

        assert_eq!(aggregate.call_count, 0);
        assert_eq!(aggregate.total_input_tokens, 0);
        assert_eq!(aggregate.total_output_tokens, 0);
        assert_eq!(aggregate.total_cost, 0.0);
    }

    #[tokio::test]
    async fn test_concurrent_batch_lookup() {
        let book = PricingBook::shared_from_prices(test_prices());
        let queries = vec![
            ("openai".to_string(), "gpt-4o".to_string()),
            ("anthropic".to_string(), "claude-3".to_string()),
            ("unknown".to_string(), "model".to_string()),
        ];
        let results = concurrent_batch_lookup(queries, book).await;
        assert_eq!(results.len(), 3);
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
    async fn test_concurrent_batch_upsert() {
        let book = PricingBook::shared_from_prices(test_prices());
        let updates = vec![
            ModelPricing {
                provider: "openai".into(),
                model: "gpt-4o".into(),
                input_per_m: 5.0,
                output_per_m: 20.0,
            },
            ModelPricing {
                provider: "meta".into(),
                model: "llama-3".into(),
                input_per_m: 1.0,
                output_per_m: 4.0,
            },
        ];
        let count = concurrent_batch_upsert(updates, book.clone()).await;
        assert_eq!(count, 2);
        let guard = book.read().await;
        assert_eq!(guard.len(), 3);
        assert_eq!(
            guard.get_price("openai", "gpt-4o").unwrap().input_per_m,
            5.0
        );
    }
}
