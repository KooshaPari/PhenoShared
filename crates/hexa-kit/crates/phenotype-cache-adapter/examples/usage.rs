use phenotype_cache_adapter::TwoTierCache;

fn main() {
    let cache = TwoTierCache::new(100, 1000);

    cache.put("key1".to_string(), "value1".to_string());
    let _ = cache.get(&"key1".to_string());
}
