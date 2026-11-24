# Graceful Degradation Pattern

## Overview

Graceful degradation ensures a system remains partially functional when components fail, rather than complete system failure. It prioritizes critical features while reducing or disabling non-essential capabilities.

## Core Principles

### 1. Feature Prioritization

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FeaturePriority {
    Critical,      // Must work (e.g., payment processing)
    Essential,   // Should work (e.g., product catalog)
    NiceToHave,  // Can be disabled (e.g., recommendations)
    Cosmetic,    // Visual only (e.g., animations)
}

pub struct Feature {
    pub name: String,
    pub priority: FeaturePriority,
    pub fallback: FallbackStrategy,
    pub circuit_breaker: Option<CircuitBreaker>,
}
```

### 2. Degradation Levels

```
Level 5: Full Functionality
  ├─ All features enabled
  └─ Performance at 100%

Level 4: Reduced Features
  ├─ Disable nice-to-have features
  └─ Simplified UI elements

Level 3: Essential Only
  ├─ Critical + Essential features
  └─ Static content for non-essential

Level 2: Critical Only
  ├─ Core business logic only
  └─ Read-only mode possible

Level 1: Maintenance Mode
  ├─ Static landing page
  └─ "We'll be back" message
```

## Implementation

### 1. Degradation Manager

```rust
use std::sync::Arc;
use tokio::sync::{RwLock, watch};

pub struct DegradationManager {
    current_level: Arc<RwLock<DegradationLevel>>,
    feature_states: Arc<RwLock<HashMap<String, FeatureState>>>,
    level_tx: watch::Sender<DegradationLevel>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum DegradationLevel {
    Full = 5,
    Reduced = 4,
    Essential = 3,
    Critical = 2,
    Maintenance = 1,
}

impl DegradationManager {
    pub async fn can_execute(&self, feature: &str) -> bool {
        let level = *self.current_level.read().await;
        let states = self.feature_states.read().await;
        
        if let Some(state) = states.get(feature) {
            state.min_level <= level && state.is_available
        } else {
            false
        }
    }
    
    pub async fn with_fallback<T, F, Fb>(&self, 
        feature: &str, 
        primary: F, 
        fallback: Fb
    ) -> Result<T, Error>
    where
        F: Future<Output = Result<T, Error>>,
        Fb: FnOnce() -> Result<T, Error>,
    {
        if self.can_execute(feature).await {
            match primary.await {
                Ok(result) => Ok(result),
                Err(e) => {
                    tracing::warn!("Primary failed for {}, using fallback: {}", feature, e);
                    fallback()
                }
            }
        } else {
            tracing::info!("Feature {} disabled, using fallback", feature);
            fallback()
        }
    }
    
    pub async fn degrade(&self, new_level: DegradationLevel) {
        let mut current = self.current_level.write().await;
        if new_level < *current {
            tracing::warn!("Degrading from {:?} to {:?}", *current, new_level);
            *current = new_level;
            self.level_tx.send(new_level).ok();
            self.notify_degradation(new_level).await;
        }
    }
    
    async fn notify_degradation(&self, level: DegradationLevel) {
        // Notify monitoring
        // Alert on-call if critical
        // Log for post-mortem
    }
}
```

### 2. Feature Toggle with Degradation

```rust
pub struct FeatureToggle {
    name: String,
    enabled: AtomicBool,
    degradation_impact: DegradationImpact,
    fallback: Box<dyn Fallback>,
}

#[async_trait]
pub trait Fallback: Send + Sync {
    type Output;
    async fn execute(&self) -> Result<Self::Output, Error>;
}

impl FeatureToggle {
    pub async fn execute_or_fallback<T, F>(&self, operation: F) -> Result<T, Error>
    where
        F: Future<Output = Result<T, Error>>,
    {
        if !self.enabled.load(Ordering::SeqCst) {
            return self.fallback.execute().await;
        }
        
        match operation.await {
            Ok(result) => Ok(result),
            Err(e) if self.should_degrade(&e) => {
                self.disable().await;
                self.fallback.execute().await
            }
            Err(e) => Err(e),
        }
    }
    
    async fn disable(&self) {
        self.enabled.store(false, Ordering::SeqCst);
        tracing::warn!("Feature {} disabled due to failures", self.name);
    }
}
```

### 3. E-Commerce Example

```rust
pub struct EcommerceService {
    degradation_manager: Arc<DegradationManager>,
    recommendation_service: RecommendationService,
    inventory_service: InventoryService,
    pricing_service: PricingService,
    payment_service: PaymentService,
}

impl EcommerceService {
    pub async fn get_product_page(&self, product_id: ProductId) -> Result<ProductPage, Error> {
        // Critical: Must have product info
        let product = self.inventory_service.get_product(product_id).await
            .map_err(|e| Error::Critical(format!("Cannot load product: {}", e)))?;
        
        // Essential: Pricing (can use cached)
        let pricing = self.degradation_manager
            .with_fallback(
                "dynamic_pricing",
                self.pricing_service.get_dynamic_price(product_id),
                || Ok(self.pricing_service.get_cached_price(product_id))
            ).await?;
        
        // Nice-to-have: Recommendations (can skip)
        let recommendations = if self.degradation_manager.can_execute("recommendations").await {
            self.recommendation_service
                .get_recommendations(product_id)
                .await
                .unwrap_or_default() // Empty if fails
        } else {
            Vec::new() // Disabled gracefully
        };
        
        // Nice-to-have: Recently viewed (can skip)
        let recently_viewed = if self.degradation_manager.can_execute("recently_viewed").await {
            self.get_recently_viewed().await.ok()
        } else {
            None
        };
        
        Ok(ProductPage {
            product,
            pricing,
            recommendations,
            recently_viewed,
        })
    }
    
    pub async fn checkout(&self, order: Order) -> Result<Receipt, Error> {
        // Critical: Payment processing must work
        // If payment service is down, entire checkout fails
        // (This is correct behavior - can't checkout without payment)
        let payment = self.payment_service.process(order.payment).await
            .map_err(|e| Error::Critical(format!("Payment failed: {}", e)))?;
        
        // Essential: Inventory reservation
        // If inventory service is down, use optimistic locking
        // and reconcile later
        let reservation = self.degradation_manager
            .with_fallback(
                "inventory_reservation",
                self.inventory_service.reserve_items(&order.items),
                || self.create_deferred_reservation(&order.items)
            ).await?;
        
        // Nice-to-have: Email confirmation
        // Fire and forget, don't fail checkout if email fails
        if self.degradation_manager.can_execute("email_notifications").await {
            let _ = self.send_confirmation_email(&order).await;
        }
        
        Ok(Receipt::new(payment, reservation))
    }
}
```

### 4. Static Fallback Content

```rust
pub struct StaticFallback {
    content_cache: Arc<RwLock<HashMap<String, String>>>,
}

impl StaticFallback {
    pub async fn get_product_catalog(&self) -> Result<String, Error> {
        // Return cached static version
        let cache = self.content_cache.read().await;
        cache.get("product_catalog")
            .cloned()
            .ok_or_else(|| Error::NotFound("Static catalog unavailable".to_string()))
    }
    
    pub async fn get_homepage(&self) -> Result<String, Error> {
        let cache = self.content_cache.read().await;
        cache.get("homepage")
            .cloned()
            .ok_or_else(|| Error::NotFound("Static homepage unavailable".to_string()))
    }
}

// Pre-generate static fallbacks during deployment
async fn generate_static_fallbacks(service: &EcommerceService) -> Result<(), Error> {
    let catalog = service.inventory_service.get_all_products().await?;
    let static_catalog = render_static_catalog(&catalog);
    
    let homepage = service.get_homepage_content().await?;
    let static_homepage = render_static_homepage(&homepage);
    
    // Store in cache
    let mut cache = service.static_fallback.content_cache.write().await;
    cache.insert("product_catalog".to_string(), static_catalog);
    cache.insert("homepage".to_string(), static_homepage);
    
    Ok(())
}
```

## Degradation Strategies

### 1. Read-Only Mode

```rust
pub struct ReadOnlyMode {
    enabled: AtomicBool,
    allowed_operations: HashSet<String>,
}

impl ReadOnlyMode {
    pub fn check_write_allowed(&self, operation: &str) -> Result<(), Error> {
        if self.enabled.load(Ordering::SeqCst) {
            if self.allowed_operations.contains(operation) {
                Ok(())
            } else {
                Err(Error::ReadOnly(format!(
                    "Write operation '{}' not allowed in read-only mode",
                    operation
                )))
            }
        } else {
            Ok(())
        }
    }
}

// Usage
impl OrderService {
    pub async fn create_order(&self, order: NewOrder) -> Result<Order, Error> {
        self.read_only_mode.check_write_allowed("create_order")?;
        
        // Proceed with order creation
        self.db.create_order(order).await
    }
}
```

### 2. Timeout Reduction

```rust
pub struct AdaptiveTimeouts {
    base_timeout: Duration,
    degradation_multiplier: f64,
}

impl AdaptiveTimeouts {
    pub fn get_timeout(&self, level: DegradationLevel) -> Duration {
        let multiplier = match level {
            DegradationLevel::Full => 1.0,
            DegradationLevel::Reduced => 0.8,
            DegradationLevel::Essential => 0.5,
            DegradationLevel::Critical => 0.3,
            DegradationLevel::Maintenance => 0.1,
        };
        
        self.base_timeout.mul_f64(multiplier)
    }
}

// Usage
async fn fetch_with_adaptive_timeout(
    &self,
    request: Request,
    level: DegradationLevel,
) -> Result<Response, Error> {
    let timeout = self.timeouts.get_timeout(level);
    
    tokio::time::timeout(timeout, self.client.request(request)).await
        .map_err(|_| Error::Timeout)?
}
```

### 3. Circuit Breaker Integration

```rust
pub struct DegradingCircuitBreaker {
    circuit_breaker: CircuitBreaker,
    feature_name: String,
    degradation_manager: Arc<DegradationManager>,
}

impl DegradingCircuitBreaker {
    pub async fn call<F, T>(&self, operation: F) -> Result<T, Error>
    where
        F: Future<Output = Result<T, Error>>,
    {
        if !self.circuit_breaker.allow_request() {
            // Circuit is open - trigger degradation
            self.degradation_manager
                .degrade_feature(&self.feature_name)
                .await;
            
            return Err(Error::CircuitOpen);
        }
        
        match operation.await {
            Ok(result) => {
                self.circuit_breaker.record_success();
                Ok(result)
            }
            Err(e) => {
                self.circuit_breaker.record_failure();
                
                if self.circuit_breaker.should_open() {
                    self.degradation_manager
                        .degrade_feature(&self.feature_name)
                        .await;
                }
                
                Err(e)
            }
        }
    }
}
```

## Frontend Degradation

### 1. Progressive Enhancement

```javascript
// React component with graceful degradation
function ProductPage({ productId }) {
  const [product, setProduct] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [degradationLevel, setDegradationLevel] = useState('full');
  
  useEffect(() => {
    // Always load critical data
    fetchProduct(productId).then(setProduct);
    
    // Load non-critical features if available
    if (degradationLevel !== 'critical') {
      fetchRecommendations(productId)
        .then(setRecommendations)
        .catch(() => setRecommendations([])); // Empty on failure
    }
    
    if (degradationLevel === 'full') {
      fetchReviews(productId)
        .then(setReviews)
        .catch(() => setReviews([]));
    }
  }, [productId, degradationLevel]);
  
  if (!product) return <Loading />;
  
  return (
    <div>
      <ProductInfo product={product} /> {/* Always shown */}
      
      {recommendations.length > 0 && (
        <Recommendations items={recommendations} />
      )}
      
      {reviews.length > 0 && (
        <Reviews items={reviews} />
      )}
      
      {degradationLevel !== 'full' && (
        <DegradationBanner level={degradationLevel} />
      )}
    </div>
  );
}
```

### 2. Feature Detection

```javascript
// Check feature availability before using
async function loadWidget(type) {
  const available = await checkFeatureAvailability(type);
  
  if (!available) {
    // Show simplified version or hide
    return <SimplifiedWidget />;
  }
  
  try {
    const data = await fetchWidgetData(type);
    return <FullWidget data={data} />;
  } catch (error) {
    // Fallback on error
    return <SimplifiedWidget error={error} />;
  }
}
```

## Monitoring and Alerting

### 1. Degradation Metrics

```rust
pub struct DegradationMetrics {
    current_level: Gauge,
    degraded_features: GaugeVec,
    fallback_activations: CounterVec,
    user_impact: Histogram,
}

impl DegradationMetrics {
    pub fn record_degradation(&self, level: DegradationLevel, features: &[String]) {
        self.current_level.set(level as i64);
        
        for feature in features {
            self.degraded_features
                .with_label_values(&[feature])
                .set(1);
        }
        
        // Alert if critical features affected
        let critical_affected = features.iter()
            .filter(|f| is_critical_feature(f))
            .count();
        
        if critical_affected > 0 {
            ALERTS.send(Alert::CriticalFeaturesDegraded {
                count: critical_affected,
                features: features.clone(),
            });
        }
    }
    
    pub fn record_fallback_activation(&self, feature: &str, reason: &str) {
        self.fallback_activations
            .with_label_values(&[feature, reason])
            .inc();
    }
}
```

### 2. SLA Tracking

```rust
pub struct DegradedSlaTracker {
    normal_sla: Duration,
    degraded_sla_multiplier: f64,
}

impl DegradedSlaTracker {
    pub fn is_within_sla(&self, 
        response_time: Duration, 
        level: DegradationLevel
    ) -> bool {
        let adjusted_sla = match level {
            DegradationLevel::Full => self.normal_sla,
            DegradationLevel::Reduced => self.normal_sla.mul_f64(1.5),
            DegradationLevel::Essential => self.normal_sla.mul_f64(2.0),
            DegradationLevel::Critical => self.normal_sla.mul_f64(3.0),
            DegradationLevel::Maintenance => Duration::MAX, // No SLA
        };
        
        response_time <= adjusted_sla
    }
}
```

## Testing Degradation

### 1. Chaos Testing

```rust
#[tokio::test]
async fn test_graceful_degradation() {
    let service = EcommerceService::new();
    
    // Test with recommendation service down
    chaos::disable_service("recommendations").await;
    
    let page = service.get_product_page(product_id).await.unwrap();
    
    // Product should still load
    assert!(page.product.is_some());
    // Recommendations should be empty, not error
    assert!(page.recommendations.is_empty());
}

#[tokio::test]
async fn test_critical_failure() {
    let service = EcommerceService::new();
    
    // Test with inventory down
    chaos::disable_service("inventory").await;
    
    // Should fail - inventory is critical
    let result = service.get_product_page(product_id).await;
    assert!(result.is_err());
}
```

### 2. Load Testing with Degradation

```rust
#[tokio::test]
async fn test_degradation_under_load() {
    let service = Arc::new(EcommerceService::new());
    
    // Simulate high load
    let handles: Vec<_> = (0..1000)
        .map(|_| {
            let svc = service.clone();
            tokio::spawn(async move {
                svc.get_product_page(product_id).await
            })
        })
        .collect();
    
    // Verify some degrade to fallback
    let results = futures::future::join_all(handles).await;
    let degraded_count = results.iter()
        .filter(|r| matches!(r, Ok(page) if page.recommendations.is_empty()))
        .count();
    
    assert!(degraded_count > 0, "Some requests should degrade under load");
}
```