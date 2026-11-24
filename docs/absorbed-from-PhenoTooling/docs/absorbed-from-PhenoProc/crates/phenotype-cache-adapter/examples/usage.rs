use std::sync::Arc;

use phenotype_cache_adapter::{MetricsHook, TwoTierCache};

#[derive(Debug)]
struct ObsHook;

impl MetricsHook for ObsHook {
    fn record_hit(&self, _tier: &str) {}
    fn record_miss(&self, _tier: &str) {}
}

fn main() {
    let _hook = Arc::new(ObsHook);
    let cache = TwoTierCache::new(100, 1000);

    cache.put("key1".to_string(), "value1".to_string());
    let _ = cache.get(&"key1".to_string());
}
