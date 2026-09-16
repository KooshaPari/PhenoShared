# Cache-Aside Pattern

## Overview

The **Cache-Aside Pattern** (also known as Lazy Loading) loads data into the cache on demand, keeping the cache and data store independent.

```
┌─────────────────────────────────────────────────────────────────┐
│                     CACHE-ASIDE PATTERN                          │
│                                                                  │
│   ┌─────────────┐                                              │
│   │ Application │                                              │
│   └──────┬──────┘                                              │
│          │                                                      │
│          │ 1. Get data                                          │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐     Cache Miss      ┌─────────────┐          │
│   │    Cache    │────────────────────▶│  Database   │          │
│   │   (Redis)   │                     │             │          │
│   └──────┬──────┘                     └──────┬──────┘          │
│          │                                  │                   │
│          │ 2. ❌ Not Found                  │ 3. Query          │
│          │                                  │                   │
│          │ 4. ◀──────── Return data ────────┘                   │
│          │                                  │                   │
│          │ 5. Store in cache              │                   │
│          │                                  │                   │
│          ▼                                                      │
│   ┌─────────────┐                                              │
│   │    Cache    │ ◀──────── Next request hits cache            │
│   │  ✓ Found    │                                              │
│   └─────────────┘                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## When to Use

### ✅ Use When

- Read-heavy workloads
- Cache doesn't need to be 100% consistent with database
- Data changes infrequently
- Multiple applications share the cache

### ❌ Don't Use When

- Write-heavy workloads (consider Write-Through)
- Strong consistency required (use Read-Through)
- Cache warming is critical at startup

## Implementation

### Basic Pattern

```rust
pub struct CacheAsideCache<K, V> {
    cache: Arc<dyn Cache<K, V>>,
    loader: Arc<dyn CacheLoader<K, V>>,
    ttl: Duration,
}

#[async_trait]
pub trait CacheLoader<K, V>: Send + Sync {
    async fn load(&self, key: &K) -> Result<Option<V>, CacheError>;
}

impl<K: Clone + Send + Sync + Hash + Eq, V: Clone + Send + Sync> CacheAsideCache<K, V> {
    pub async fn get(&self, key: &K) -> Result<Option<V>, CacheError> {
        // 1. Try cache first
        if let Some(value) = self.cache.get(key).await? {
            return Ok(Some(value));
        }
        
        // 2. Cache miss - load from source
        let value = match self.loader.load(key).await? {
            Some(v) => v,
            None => return Ok(None),
        };
        
        // 3. Store in cache for next time
        self.cache.set(key, &value, self.ttl).await?;
        
        Ok(Some(value))
    }
    
    pub async fn set(&self, key: &K, value: &V) -> Result<(), CacheError> {
        // Update database first (if applicable)
        // Then update cache
        self.cache.set(key, value, self.ttl).await
    }
    
    pub async fn invalidate(&self, key: &K) -> Result<(), CacheError> {
        self.cache.delete(key).await
    }
}
```

### With Stale-While-Revalidate

```rust
pub struct StaleWhileRevalidateCache<K, V> {
    cache: Arc<dyn Cache<K, V>>,
    loader: Arc<dyn CacheLoader<K, V>>,
    soft_ttl: Duration,  // Serve stale data
    hard_ttl: Duration,  // Must revalidate
}

impl<K, V> StaleWhileRevalidateCache<K, V> {
    pub async fn get(&self, key: &K) -> Result<Option<V>, CacheError> {
        let entry = self.cache.get_with_metadata(key).await?;
        
        match entry {
            Some((value, age)) if age < self.soft_ttl => {
                // Fresh data
                Ok(Some(value))
            }
            Some((value, age)) if age < self.hard_ttl => {
                // Stale but acceptable - serve immediately, refresh async
                let cache = self.cache.clone();
                let loader = self.loader.clone();
                let key = key.clone();
                
                tokio::spawn(async move {
                    if let Ok(Some(new_value)) = loader.load(&key).await {
                        let _ = cache.set(&key, &new_value, hard_ttl).await;
                    }
                });
                
                Ok(Some(value))
            }
            _ => {
                // Expired or missing - must load
                match self.loader.load(key).await? {
                    Some(value) => {
                        self.cache.set(key, &value, self.hard_ttl).await?;
                        Ok(Some(value))
                    }
                    None => Ok(None),
                }
            }
        }
    }
}
```

### With Write-Behind

```rust
pub struct WriteBehindCache<K, V> {
    cache: Arc<dyn Cache<K, V>>,
    loader: Arc<dyn CacheLoader<K, V>>,
    write_queue: Arc<dyn WriteQueue<K, V>>,
}

impl<K, V> WriteBehindCache<K, V> {
    pub async fn set(&self, key: &K, value: &V) -> Result<(), CacheError> {
        // Update cache immediately
        self.cache.set(key, value, self.ttl).await?;
        
        // Queue write to database (async)
        self.write_queue.enqueue(key, value).await;
        
        Ok(())
    }
}
```

## Cache Invalidation Strategies

### 1. Time-Based (TTL)

```rust
// Simple expiration
cache.set("user:123", &user, Duration::from_secs(300)).await?;
```

### 2. Event-Based (Pub/Sub)

```rust
pub struct CacheInvalidator {
    cache: Arc<dyn Cache<String, Value>>,
    subscriber: Arc<dyn EventSubscriber>,
}

impl CacheInvalidator {
    pub async fn start(&self) -> Result<(), Error> {
        let mut stream = self.subscriber.subscribe("cache.invalidate").await?;
        
        while let Some(event) = stream.next().await {
            match event {
                InvalidateEvent::Key(key) => {
                    self.cache.delete(&key).await?;
                    info!(key = %key, "Invalidated cache key");
                }
                InvalidateEvent::Pattern(pattern) => {
                    self.cache.delete_pattern(&pattern).await?;
                    info!(pattern = %pattern, "Invalidated cache pattern");
                }
            }
        }
        
        Ok(())
    }
}

// Publisher side
pub async fn update_user(user_id: &str, update: UserUpdate) -> Result<User, Error> {
    // Update database
    let user = db.users.update(user_id, update).await?;
    
    // Invalidate cache
    event_bus.publish(CacheEvent::Invalidate {
        key: format!("user:{}", user_id),
    }).await?;
    
    Ok(user)
}
```

### 3. Tag-Based

```rust
// Associate cache keys with tags
pub struct TaggedCache {
    cache: Arc<dyn Cache<String, Value>>,
    tag_index: Arc<dyn TagIndex>,
}

impl TaggedCache {
    pub async fn set_with_tags(
        &self,
        key: &str,
        value: &Value,
        tags: Vec<String>,
        ttl: Duration,
    ) -> Result<(), CacheError> {
        // Store value
        self.cache.set(key, value, ttl).await?;
        
        // Index tags
        for tag in tags {
            self.tag_index.add_to_tag(&tag, key).await?;
        }
        
        Ok(())
    }
    
    pub async fn invalidate_tag(&self, tag: &str) -> Result<u64, CacheError> {
        let keys = self.tag_index.get_keys_for_tag(tag).await?;
        let count = keys.len() as u64;
        
        for key in keys {
            self.cache.delete(&key).await?;
        }
        
        self.tag_index.remove_tag(tag).await?;
        
        Ok(count)
    }
}

// Usage
let user = fetch_user(user_id).await?;
cache.set_with_tags(
    &format!("user:{}", user_id),
    &user,
    vec![
        format!("org:{}", user.org_id),
        "type:user".to_string(),
    ],
    Duration::from_secs(3600),
).await?;

// When org changes, invalidate all users in that org
cache.invalidate_tag(&format!("org:{}", org_id)).await?;
```

## Handling Cache Stampede

### Singleflight Pattern

```rust
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

pub struct SingleflightCache<K, V> {
    cache: Arc<dyn Cache<K, V>>,
    loader: Arc<dyn CacheLoader<K, V>>,
    in_flight: Arc<Mutex<HashMap<K, Arc<tokio::sync::RwLock<Option<V>>>>>>,
}

impl<K: Clone + Hash + Eq + Send + Sync, V: Clone + Send + Sync> SingleflightCache<K, V> {
    pub async fn get(&self, key: &K) -> Result<Option<V>, CacheError> {
        // Try cache first
        if let Some(value) = self.cache.get(key).await? {
            return Ok(Some(value));
        }
        
        // Check if already loading
        let lock = {
            let mut in_flight = self.in_flight.lock().unwrap();
            in_flight.entry(key.clone()).or_insert_with(|| {
                Arc::new(tokio::sync::RwLock::new(None))
            }).clone()
        };
        
        // Only first requestor loads, others wait
        let result = {
            let guard = lock.read().await;
            if let Some(ref value) = *guard {
                // Another requestor already loaded
                return Ok(Some(value.clone()));
            }
            drop(guard);
            
            // Get write lock and load
            let mut guard = lock.write().await;
            if let Some(ref value) = *guard {
                // Race condition: someone else loaded while waiting
                return Ok(Some(value.clone()));
            }
            
            // Actually load
            let value = self.loader.load(key).await?;
            *guard = value.clone();
            value
        };
        
        // Clean up in_flight
        {
            let mut in_flight = self.in_flight.lock().unwrap();
            in_flight.remove(key);
        }
        
        // Store in cache if loaded
        if let Some(ref value) = result {
            self.cache.set(key, value, self.ttl).await?;
        }
        
        Ok(result)
    }
}
```

## Testing

```rust
#[tokio::test]
async fn cache_aside_hits_cache_on_second_request() {
    let cache = InMemoryCache::new();
    let loader = MockLoader::new(vec![
        ("key1".to_string(), "value1".to_string()),
    ]);
    
    let cache_aside = CacheAsideCache::new(
        Arc::new(cache),
        Arc::new(loader),
        Duration::from_secs(60),
    );
    
    // First request - cache miss, loads from source
    let value1 = cache_aside.get(&"key1".to_string()).await.unwrap();
    assert_eq!(value1, Some("value1".to_string()));
    assert_eq!(loader.load_count("key1"), 1);
    
    // Second request - cache hit
    let value2 = cache_aside.get(&"key1".to_string()).await.unwrap();
    assert_eq!(value2, Some("value1".to_string()));
    assert_eq!(loader.load_count("key1"), 1); // Not loaded again
}

#[tokio::test]
async fn invalidation_removes_from_cache() {
    let cache = InMemoryCache::new();
    let loader = MockLoader::new(vec![]);
    
    let cache_aside = CacheAsideCache::new(
        Arc::new(cache.clone()),
        Arc::new(loader),
        Duration::from_secs(60),
    );
    
    // Pre-populate cache
    cache.set(&"key1".to_string(), &"value1".to_string(), Duration::from_secs(60)).await.unwrap();
    
    // Verify in cache
    assert!(cache_aside.get(&"key1".to_string()).await.unwrap().is_some());
    
    // Invalidate
    cache_aside.invalidate(&"key1".to_string()).await.unwrap();
    
    // Verify not in cache (would load from source if available)
    assert!(cache.get(&"key1".to_string()).await.unwrap().is_none());
}
```

## Anti-Patterns

- ❌ No TTL (cache grows forever)
- ❌ No invalidation (stale data)
- ❌ Cache as source of truth (cache is secondary)
- ❌ Not handling cache failures (should fall back to source)
- ❌ Thundering herd (multiple simultaneous cache misses)

## Related Patterns

- [Singleflight Pattern](./singleflight.md)
- [Write-Through Pattern](./write-through.md)
- [Read-Through Pattern](./read-through.md)

## References

- [Cache-Aside Pattern - Microsoft](https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside)
- [Caching Strategies - AWS](https://docs.aws.amazon.com/whitepapers/latest/database-caching/caching-patterns.html)
