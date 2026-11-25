# Health Check Pattern

## Overview

Health checks provide visibility into system operational status, enabling load balancers, orchestrators, and monitoring systems to make intelligent routing and scaling decisions.

## Types of Health Checks

### 1. Liveness Probe

Checks if the process is running (basic heartbeat).

```rust
// Simple liveness check
async fn liveness_check() -> StatusCode {
    // If we can respond, we're alive
    StatusCode::OK
}
```

**Use for:**
- Kubernetes pod restart decisions
- Basic process monitoring
- Circuit breaker decisions

### 2. Readiness Probe

Checks if the service is ready to handle traffic.

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
struct HealthState {
    is_healthy: Arc<RwLock<bool>>,
    startup_complete: Arc<RwLock<bool>>,
    last_error: Arc<RwLock<Option<String>>>,
}

impl HealthState {
    async fn is_ready(&self) -> bool {
        *self.startup_complete.read().await && *self.is_healthy.read().await
    }
}

async fn readiness_check(
    state: &HealthState,
    db_pool: &DbPool,
    cache: &CacheClient,
) -> Result<HealthResponse, HealthError> {
    let mut checks = Vec::new();
    let mut all_healthy = true;
    
    // Database connectivity
    let db_result = tokio::time::timeout(
        Duration::from_secs(2),
        db_pool.ping()
    ).await;
    
    match db_result {
        Ok(Ok(())) => checks.push(Check {
            name: "database",
            status: Status::Healthy,
            latency_ms: 15,
        }),
        Ok(Err(e)) => {
            all_healthy = false;
            checks.push(Check {
                name: "database",
                status: Status::Unhealthy(format!("Ping failed: {}", e)),
                latency_ms: 0,
            });
        }
        Err(_) => {
            all_healthy = false;
            checks.push(Check {
                name: "database",
                status: Status::Timeout,
                latency_ms: 2000,
            });
        }
    }
    
    // Cache connectivity
    let cache_result = tokio::time::timeout(
        Duration::from_secs(1),
        cache.get("health-check-key")
    ).await;
    
    match cache_result {
        Ok(_) => checks.push(Check {
            name: "cache",
            status: Status::Healthy,
            latency_ms: 5,
        }),
        Err(_) => {
            all_healthy = false;
            checks.push(Check {
                name: "cache",
                status: Status::Degraded("High latency".to_string()),
                latency_ms: 1000,
            });
        }
    }
    
    // External service check
    if let Some(dependency) = get_external_service() {
        match check_dependency(&dependency).await {
            Ok(status) => checks.push(status),
            Err(e) => {
                checks.push(Check {
                    name: &dependency.name,
                    status: Status::Unhealthy(e.to_string()),
                    latency_ms: 0,
                });
                // Don't mark all_healthy = false for optional dependencies
            }
        }
    }
    
    Ok(HealthResponse {
        status: if all_healthy {
            OverallStatus::Healthy
        } else {
            OverallStatus::Unhealthy
        },
        checks,
        timestamp: Utc::now(),
        version: env!("CARGO_PKG_VERSION"),
    })
}
```

### 3. Deep Health Check

Comprehensive check including business logic validation.

```rust
async fn deep_health_check(
    deps: &Dependencies,
) -> Result<DetailedHealthResponse, HealthError> {
    let mut report = DetailedHealthResponse::default();
    
    // Infrastructure checks
    report.infrastructure = check_infrastructure(deps).await?;
    
    // Data integrity checks
    report.data_integrity = check_data_integrity(deps).await?;
    
    // Business logic validation
    report.business_functions = check_critical_functions(deps).await?;
    
    // Performance validation
    report.performance = validate_performance(deps).await?;
    
    Ok(report)
}

async fn check_critical_functions(deps: &Dependencies) -> Vec<FunctionCheck> {
    vec![
        validate_user_creation(deps).await,
        validate_order_processing(deps).await,
        validate_payment_flow(deps).await,
    ]
}
```

## Implementation Patterns

### 1. Layered Health Checks

```
┌─────────────────────────────────────────┐
│           Load Balancer                │
│         /healthz (Liveness)             │
├─────────────────────────────────────────┤
│           Kubernetes                   │
│    /ready (Readiness Probe)            │
├─────────────────────────────────────────┤
│           Application                  │
│   /health/deep (Deep Health)           │
│   - Database connections               │
│   - Cache connectivity                 │
│   - External services                  │
│   - Business logic                     │
└─────────────────────────────────────────┘
```

### 2. Health Check Aggregation

```rust
// Aggregate checks from multiple services
pub struct HealthAggregator {
    services: Vec<Box<dyn HealthCheckable>>,
}

#[async_trait]
pub trait HealthCheckable: Send + Sync {
    async fn health_check(&self) -> ServiceHealth;
}

impl HealthAggregator {
    pub async fn aggregate(&self) -> AggregatedHealth {
        let mut results = Vec::new();
        
        for service in &self.services {
            let health = service.health_check().await;
            results.push(health);
        }
        
        AggregatedHealth {
            overall: if results.iter().all(|h| h.is_healthy()) {
                OverallStatus::Healthy
            } else if results.iter().any(|h| h.is_critical() && !h.is_healthy()) {
                OverallStatus::Unhealthy
            } else {
                OverallStatus::Degraded
            },
            services: results,
        }
    }
}
```

### 3. Health Check with Degradation

```rust
pub enum ServiceStatus {
    Healthy,
    Degraded { reason: String, impact: ImpactLevel },
    Unhealthy { reason: String },
}

impl ServiceStatus {
    pub fn is_operational(&self) -> bool {
        matches!(self, ServiceStatus::Healthy | ServiceStatus::Degraded { .. })
    }
}

async fn check_with_degradation(deps: &Dependencies) -> ServiceStatus {
    let checks = vec![
        check_primary_database(deps).await,
        check_replica_database(deps).await,
        check_cache(deps).await,
    ];
    
    // Service works with degraded cache
    if checks[0].is_healthy() && checks[1].is_healthy() && !checks[2].is_healthy() {
        return ServiceStatus::Degraded {
            reason: "Cache unavailable".to_string(),
            impact: ImpactLevel::Performance,
        };
    }
    
    // Service works with one database down (replica only)
    if checks[0].is_healthy() && !checks[1].is_healthy() && checks[2].is_healthy() {
        return ServiceStatus::Degraded {
            reason: "Primary database in failover".to_string(),
            impact: ImpactLevel::ReducedCapacity,
        };
    }
    
    // Critical failure - can't operate
    if !checks[0].is_healthy() {
        return ServiceStatus::Unhealthy {
            reason: "Primary database down".to_string(),
        };
    }
    
    ServiceStatus::Healthy
}
```

## Kubernetes Integration

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phenotype-service
spec:
  template:
    spec:
      containers:
      - name: app
        image: phenotype/app:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 2
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
          successThreshold: 2
        startupProbe:
          httpGet:
            path: /startup
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 30
```

## Monitoring Integration

```rust
// Export health metrics to Prometheus
impl HealthMonitor {
    async fn export_metrics(&self, health: &HealthResponse) {
        for check in &health.checks {
            HEALTH_CHECK_STATUS
                .with_label_values(&[&check.name])
                .set(if check.status.is_healthy() { 1.0 } else { 0.0 });
            
            HEALTH_CHECK_LATENCY
                .with_label_values(&[&check.name])
                .observe(check.latency_ms as f64 / 1000.0);
        }
        
        OVERALL_HEALTH.set(match health.status {
            OverallStatus::Healthy => 1.0,
            OverallStatus::Degraded => 0.5,
            OverallStatus::Unhealthy => 0.0,
        });
    }
}

// Prometheus alerts
// alert: ServiceUnhealthy
// expr: overall_health < 1
// for: 5m
// labels:
//   severity: critical
```

## Best Practices

### 1. Check What Matters

```rust
// ❌ Bad: Checking everything, slow response
async fn bad_health_check() -> Result<(), Error> {
    check_all_100_dependencies().await?; // Takes 30 seconds
    Ok(())
}

// ✅ Good: Critical path only, fast response
async fn good_health_check() -> Result<(), Error> {
    // Check only synchronous dependencies
    tokio::time::timeout(Duration::from_secs(3), async {
        check_critical_db().await?;
        check_critical_cache().await?;
        Ok(())
    }).await??
}
```

### 2. Different Checks for Different Needs

| Endpoint | Use Case | Frequency | Depth |
|----------|----------|-----------|-------|
| /healthz | Liveness | Every 5s | Minimal |
| /ready | Readiness | Every 5s | Dependencies |
| /health | Monitoring | Every 30s | Full |
| /health/deep | Diagnostics | On demand | Complete |

### 3. Graceful Degradation Reporting

```rust
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: OverallStatus,
    pub version: String,
    pub checks: Vec<Check>,
    pub degraded_capabilities: Vec<String>,
    pub recommendations: Vec<String>,
}

// Example response
{
  "status": "degraded",
  "version": "1.2.3",
  "checks": [
    {"name": "database", "status": "healthy"},
    {"name": "cache", "status": "unhealthy", "reason": "timeout"}
  ],
  "degraded_capabilities": ["real-time-analytics"],
  "recommendations": [
    "Cache cluster needs investigation",
    "Service operating with reduced performance"
  ]
}
```

### 4. Startup Sequence

```
┌─────────────────────────────────────────────┐
│  1. Binary starts                            │
│     ↓                                        │
│  2. Startup probe begins                     │
│     ↓                                        │
│  3. Initialize logging, config               │
│     ↓                                        │
│  4. Connect to database                      │
│     ↓                                        │
│  5. Run migrations                           │
│     ↓                                        │
│  6. Connect to cache                         │
│     ↓                                        │
│  7. Register with service discovery          │
│     ↓                                        │
│  8. Startup probe succeeds                   │
│     ↓                                        │
│  9. Readiness probe begins                   │
│     ↓                                        │
│  10. Traffic routing begins                  │
└─────────────────────────────────────────────┘
```