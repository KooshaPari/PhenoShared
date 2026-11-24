# ADR-005: Load Balancing Strategy

**Document ID:** BYTEPORT_ADR_005  
**Status:** Accepted  
**Last Updated:** 2026-04-04  
**Author:** BytePort Architecture Team

---

## Context

BytePort supports distributed deployments where multiple server nodes handle client requests. We need a flexible load balancing system that:
1. Distributes load across nodes fairly
2. Handles node failure gracefully
3. Supports session affinity when required
4. Provides visibility into node health

## Decision

We implement a **pluggable load balancing system with multiple algorithm options**:

### Supported Algorithms

| Algorithm | Stateless | Complexity | Fairness | Use Case |
|-----------|-----------|-------------|----------|----------|
| Round Robin | Yes | O(1) | High | Homogeneous nodes |
| Weighted Round Robin | Yes | O(n) | High | Heterogeneous nodes |
| Least Connections | No | O(n) | Medium | Variable load |
| Consistent Hash | No | O(log n) | Medium | Session affinity |
| Power of Two | No | O(1) | High | Large clusters |
| Random | Yes | O(1) | Medium | Simple deployments |

## Core Trait

```rust
#[async_trait]
pub trait LoadBalancer: Send + Sync {
    async fn select(&self, request: &Request) -> Option<Node>;
    async fn record_result(&self, node: &Node, result: RequestResult);
    async fn add_node(&self, node: Node) -> Result<(), LbError>;
    async fn remove_node(&self, node_id: NodeId) -> Result<(), LbError>;
    fn healthy_nodes(&self) -> Vec<Node>;
}

pub struct Node {
    pub id: NodeId,
    pub address: SocketAddr,
    pub weight: u32,
    pub metadata: HashMap<String, String>,
    pub health: HealthStatus,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum HealthStatus {
    Healthy,
    Degraded,
    Unhealthy,
    Unknown,
}

pub struct RequestResult {
    pub latency: Duration,
    pub success: bool,
    pub error_type: Option<String>,
}
```

## Round Robin Implementation

```rust
pub struct RoundRobinBalancer {
    nodes: RwLock<Vec<Node>>,
    counter: AtomicUsize,
}

#[async_trait]
impl LoadBalancer for RoundRobinBalancer {
    async fn select(&self, _request: &Request) -> Option<Node> {
        let nodes = self.nodes.read().await;
        if nodes.is_empty() {
            return None;
        }
        
        let idx = self.counter.fetch_add(1, Ordering::SeqCst) % nodes.len();
        
        // Skip unhealthy nodes
        let mut attempts = 0;
        let start_idx = idx;
        while attempts < nodes.len() {
            if nodes[idx].health == HealthStatus::Healthy {
                return Some(nodes[idx].clone());
            }
            let idx = (idx + 1) % nodes.len();
            if idx == start_idx {
                break;
            }
            attempts += 1;
        }
        
        // Fallback to any available node
        nodes.get(idx).cloned()
    }
    
    async fn add_node(&self, node: Node) -> Result<(), LbError> {
        self.nodes.write().await.push(node);
        Ok(())
    }
    
    async fn remove_node(&self, node_id: NodeId) -> Result<(), LbError> {
        self.nodes.write().await.retain(|n| n.id != node_id);
        Ok(())
    }
    
    fn healthy_nodes(&self) -> Vec<Node> {
        self.nodes
            .try_read()
            .map(|nodes| {
                nodes.iter()
                    .filter(|n| n.health == HealthStatus::Healthy)
                    .cloned()
                    .collect()
            })
            .unwrap_or_default()
    }
}
```

## Consistent Hash Implementation

```rust
pub struct ConsistentHashBalancer {
    ring: RwLock<BTreeMap<u64, Node>>,
    virtual_nodes: usize,
    hasher: DefaultHasher,
}

impl ConsistentHashBalancer {
    pub fn new(virtual_nodes: usize) -> Self {
        Self {
            ring: RwLock::new(BTreeMap::new()),
            virtual_nodes,
            hasher: DefaultHasher::new(),
        }
    }
    
    fn hash(&self, key: &str) -> u64 {
        let mut h = self.hasher.clone();
        h.write(key.as_bytes());
        h.finish()
    }
}

#[async_trait]
impl LoadBalancer for ConsistentHashBalancer {
    async fn select(&self, request: &Request) -> Option<Node> {
        let ring = self.ring.read().await;
        if ring.is_empty() {
            return None;
        }
        
        let key = request.routing_key()
            .ok_or_else(|| "No routing key".to_string())?;
        let hash = self.hash(&key);
        
        // Find next node clockwise on ring
        ring.range(hash..)
            .next()
            .map(|(_, node)| node.clone())
            .or_else(|| ring.iter().next().map(|(_, node)| node.clone()))
    }
    
    async fn add_node(&self, node: Node) -> Result<(), LbError> {
        let mut ring = self.ring.write().await;
        for i in 0..self.virtual_nodes {
            let key = format!("{}#{}", node.id, i);
            ring.insert(self.hash(&key), node.clone());
        }
        Ok(())
    }
}
```

## Health Checking

```rust
pub struct HealthChecker {
    interval: Duration,
    timeout: Duration,
    unhealthy_threshold: u32,
    healthy_threshold: u32,
    checks: RwLock<HashMap<NodeId, HealthState>>,
}

struct HealthState {
    consecutive_failures: u32,
    consecutive_successes: u32,
}

impl HealthChecker {
    pub async fn check(&self, node: &Node) -> HealthStatus {
        let start = Instant::now();
        
        match tokio::time::timeout(
            self.timeout,
            self.perform_health_check(node),
        ).await {
            Ok(Ok(_)) => {
                let elapsed = start.elapsed();
                if elapsed < Duration::from_millis(100) {
                    HealthStatus::Healthy
                } else {
                    HealthStatus::Degraded
                }
            }
            _ => HealthStatus::Unhealthy,
        }
    }
    
    async fn perform_health_check(&self, node: &Node) -> Result<(), HealthCheckError> {
        // Send health check frame
        let frame = FrameBuilder::new(SCHEMA_ID_HEALTH_CHECK)
            .request()
            .payload(Bytes::new())
            .build()?;
        
        // Implementation uses connection pool
        Ok(())
    }
}
```

## Selection Strategy

```rust
pub struct LoadBalancerSelector {
    config: LoadBalancerConfig,
}

impl LoadBalancerSelector {
    pub fn create(&self) -> Arc<dyn LoadBalancer> {
        match self.config.algorithm {
            LoadBalancingAlgorithm::RoundRobin => {
                Arc::new(RoundRobinBalancer::new())
            }
            LoadBalancingAlgorithm::LeastConnections => {
                Arc::new(LeastConnectionsBalancer::new())
            }
            LoadBalancingAlgorithm::ConsistentHash { virtual_nodes } => {
                Arc::new(ConsistentHashBalancer::new(virtual_nodes))
            }
            LoadBalancingAlgorithm::Weighted => {
                Arc::new(WeightedRoundRobinBalancer::new())
            }
        }
    }
}
```

## Consequences

**Positive:**
- Multiple algorithms for diverse use cases
- Health checking prevents routing to failed nodes
- Consistent hashing enables session affinity
- Pluggable design allows easy extension

**Negative:**
- Stateful balancers require synchronization
- Health checking adds overhead
- Consistent hashing has non-uniform distribution with fewer nodes

---

*End of ADR-005*
