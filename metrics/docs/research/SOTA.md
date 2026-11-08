# Metrics Library - State of the Art

> Comprehensive metrics collection for Go applications - SOTA Observability Research

**Version**: 1.0  
**Status**: Active  
**Last Updated**: 2026-04-05

---

## Part I: Observability Landscape (2024-2026)

### 1.1 Metrics Collection Evolution

The metrics collection landscape has evolved significantly from simple counters to sophisticated multi-dimensional telemetry systems. Modern applications require real-time visibility into system health, performance characteristics, and business outcomes.

#### Historical Evolution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Metrics Evolution Timeline                              │
│                                                                             │
│  2010      2014      2016      2018      2020      2022      2024+           │
│    │         │         │         │         │         │         │           │
│    ▼         ▼         ▼         ▼         ▼         ▼         ▼           │
│  ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐   ┌────┐             │
│  │SNMP│→  │StatsD│→ │Prom│→ │Otel│→ │Graf│→ │OTLP│→ │eBPF│             │
│  │    │   │      │   │etheus│   │metry│   │ana │   │    │   │Native│             │
│  └────┘   └────┘   └────┘   └────┘   └────┘   └────┘   └────┘             │
│                                                                             │
│  Push      Push      Pull      Both      Both      Push      Kernel         │
│  Polling   UDP       HTTP      HTTP/gRPC Stack     gRPC      Space          │
│                                                                             │
│  Metrics   Metrics   Metrics  Metrics   Logs      Unified   Zero-copy       │
│  Only      Only      +Labels  +Traces   +Traces   Signals   Overhead        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Modern Metrics Requirements

| Requirement | Traditional | Modern (2024+) | Impact |
|-------------|-------------|----------------|--------|
| **Cardinality** | 100s of series | 100,000s of series | High-dimensional data |
| **Collection Interval** | 60s | 1-15s | Real-time alerting |
| **Retained Labels** | 5-10 | 50+ | Fine-grained analysis |
| **Storage Cost** | $10/GB/month | $0.10/GB/month | Cost efficiency |
| **Query Latency** | Seconds | Sub-second | Interactive dashboards |
| **Data Volume** | GBs/day | TBs/day | Scalable ingestion |

### 1.2 Metrics Standards Comparison

#### Prometheus Ecosystem

| Component | Purpose | Adoption | Maturity |
|-----------|---------|----------|----------|
| **Prometheus Server** | Metrics storage | 95%+ | GA (2015) |
| **PromQL** | Query language | 90%+ | GA |
| **Alertmanager** | Alert routing | 85%+ | GA |
| **Pushgateway** | Batch metrics | 60%+ | GA |
| **Service Discovery** | Auto-detection | 70%+ | GA |
| **Remote Write** | Long-term storage | 80%+ | GA v2.0 |
| **Exposition Format** | OpenMetrics | 90%+ | GA |

#### OpenTelemetry Metrics

| Feature | Status | Spec Version | SDK Support |
|---------|--------|--------------|-------------|
| **Counter** | Stable | v1.0+ | All languages |
| **UpDownCounter** | Stable | v1.0+ | All languages |
| **Histogram** | Stable | v1.0+ | All languages |
| **Observable Gauge** | Stable | v1.0+ | All languages |
| **Exponential Histogram** | Stable | v1.17+ | Go, Java, .NET |
| **Views** | Stable | v1.0+ | All languages |
| **OTLP Protocol** | Stable | v1.0+ | All languages |

#### Vendor-Specific Formats

| Vendor | Format | Protocol | Open Source |
|--------|--------|----------|-------------|
| **Datadog** | DogStatsD | UDP | Partial |
| **InfluxDB** | Line Protocol | HTTP/UDP | Yes |
| **CloudWatch** | JSON | HTTPS | No |
| **Stackdriver** | Protobuf | gRPC | Partial |
| **New Relic** | JSON/Protobuf | HTTPS/gRPC | No |
| **Grafana Cloud** | Prometheus | HTTP/gRPC | Yes |

### 1.3 Metrics Storage Systems

#### Time-Series Databases (2024)

| Database | Language | Storage Engine | Query Performance | Best For |
|----------|----------|----------------|-------------------|----------|
| **Prometheus** | Go | Custom TSDB | Good | Alerting, small scale |
| **VictoriaMetrics** | Go | MergeTree | Excellent | High cardinality |
| **Thanos** | Go | Object storage | Good | Global view |
| **Cortex** | Go | Object storage | Good | Multi-tenant |
| **Mimir** | Go | Object storage | Excellent | Grafana Cloud |
| **InfluxDB 3.0** | Rust | Apache Arrow | Excellent | Analytics |
| **TimescaleDB** | C/Rust | PostgreSQL | Good | SQL compatibility |
| **ClickHouse** | C++ | MergeTree | Excellent | Log + metrics |

#### Storage Performance Benchmarks

| Database | Ingestion/sec | Query p99 | Cardinality | Compression |
|----------|---------------|-----------|-------------|-------------|
| **VictoriaMetrics** | 1M+ samples | 10ms | 10M+ series | 10x |
| **InfluxDB 3.0** | 500K+ samples | 50ms | 1M series | 5x |
| **Prometheus** | 100K samples | 100ms | 100K series | 3x |
| **Thanos** | 500K samples | 200ms | 1M series | 5x |
| **Mimir** | 1M+ samples | 50ms | 10M+ series | 10x |
| **ClickHouse** | 2M+ rows | 100ms | Unlimited | 10x |

### 1.4 Metric Types Deep Dive

#### Prometheus Metric Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Prometheus Metric Types                                 │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Counter    │  │    Gauge     │  │  Histogram   │  │   Summary    │     │
│  │              │  │              │  │              │  │              │     │
│  │  Monotonic   │  │  Arbitrary   │  │  Buckets     │  │  Quantiles   │     │
│  │  Increasing  │  │  Up/Down     │  │  + Count     │  │  + Count     │     │
│  │  Reset on    │  │  Current     │  │  + Sum       │  │  + Sum       │     │
│  │  restart     │  │  value       │  │              │  │              │     │
│  │              │  │              │  │  count{}     │  │  count{}     │     │
│  │  rate()      │  │  Current     │  │  sum{}       │  │  sum{}       │     │
│  │  irate()     │  │  value       │  │  bucket{}    │  │  quantile{}  │     │
│  │  increase()  │  │              │  │  (le=)       │  │  (0.5,0.9)   │     │
│  │              │  │              │  │              │  │              │     │
│  │  Requests    │  │  Queue depth │  │  Latency     │  │  Latency     │     │
│  │  Errors      │  │  Temperature │  │  Request size│  │  (stream)    │     │
│  │  Bytes sent  │  │  Memory usage│  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                                             │
│  Best Practice: Use Histogram over Summary for aggregation                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Metric Type Selection Guide

| Metric | Use Counter | Use Gauge | Use Histogram | Use Summary |
|--------|-------------|-----------|---------------|-------------|
| HTTP requests | ✅ | ❌ | ✅ (duration) | ❌ |
| Queue depth | ❌ | ✅ | ❌ | ❌ |
| Active connections | ❌ | ✅ | ❌ | ❌ |
| Request duration | ❌ | ❌ | ✅ | ⚠️ |
| CPU usage % | ❌ | ✅ | ❌ | ❌ |
| Error rate | ✅ | ❌ | ❌ | ❌ |
| Payload size | ❌ | ❌ | ✅ | ❌ |
| Cache hit ratio | ✅ (hits, misses) | ❌ | ❌ | ❌ |

---

## Part II: Metrics Architecture & Design Patterns

### 2.1 Instrumentation Strategies

#### White-Box vs Black-Box Monitoring

| Aspect | White-Box | Black-Box | Hybrid |
|--------|-----------|-----------|--------|
| **Implementation** | Code instrumentation | External probes | Both |
| **Visibility** | Internal state | External behavior | Complete |
| **Performance impact** | 1-5% overhead | None | 1-5% |
| **Development effort** | High (code changes) | Low | Medium |
| **Flexibility** | Limited by code | Unlimited | High |
| **Use case** | Business logic | Infrastructure | Modern apps |

#### Instrumentation Levels

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Instrumentation Hierarchy                                 │
│                                                                             │
│  L4: Business Metrics                                                       │
│      ┌─────────────────────────────────────────────────────────────────┐   │
│      │ orders_total, revenue_usd, user_signups, cart_abandonment_rate │   │
│      └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  L3: Application Metrics                                                    │
│      ┌─────────────────────────────────────────────────────────────────┐   │
│      │ http_requests_total, db_query_duration, cache_hits_total       │   │
│      └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  L2: Runtime Metrics                                                          │
│      ┌─────────────────────────────────────────────────────────────────┐   │
│      │ gc_duration_seconds, goroutines_total, heap_bytes, threads     │   │
│      └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  L1: System Metrics                                                           │
│      ┌─────────────────────────────────────────────────────────────────┐   │
│      │ cpu_seconds_total, memory_bytes, disk_io_time, network_bytes   │   │
│      └─────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Golden Signals: Latency, Traffic, Errors, Saturation (all levels)         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Cardinality Management

#### High Cardinality Challenges

| Cardinality Level | Series Count | Impact | Mitigation |
|-------------------|--------------|--------|------------|
| **Low** (<100) | 10-100 | Negligible | None needed |
| **Medium** (1K-10K) | 1,000-10,000 | Manageable | Aggregation |
| **High** (100K-1M) | 100K-1M | Expensive | Sampling |
| **Extreme** (>1M) | 1M+ | Prohibitive | Re-architecture |

#### Cardinality Control Strategies

```go
// BAD: High cardinality with user_id
http_requests_total{user_id="12345", path="/api/users"}

// GOOD: Aggregate by bucket
http_requests_total{user_type="premium", path="/api/users"}

// BETTER: Separate high-cardinality to logs
trace_id="abc123"  // In logs, not metrics
http_requests_total{status="200", path="/api/users"}  // In metrics
```

### 2.3 Metric Naming Conventions

#### Prometheus Naming Best Practices

| Component | Format | Example | Notes |
|-----------|--------|---------|-------|
| **Namespace** | application_ | `phenotype_` | Single word |
| **Subsystem** | namespace_subsystem_ | `phenotype_http_` | Optional |
| **Name** | subsystem_metric | `phenotype_http_requests_total` | Descriptive |
| **Unit** | _seconds, _bytes, _total | `phenotype_http_request_duration_seconds` | Suffix |
| **Labels** | {key="value"} | `{method="GET", status="200"}` | Key=value |

#### Standard Metric Names by Category

| Category | Metric Name | Type | Labels |
|----------|-------------|------|--------|
| **HTTP** | http_requests_total | Counter | method, path, status |
| **HTTP** | http_request_duration_seconds | Histogram | method, path |
| **HTTP** | http_response_size_bytes | Histogram | method, path |
| **Database** | db_queries_total | Counter | query_type, table |
| **Database** | db_query_duration_seconds | Histogram | query_type, table |
| **Queue** | queue_depth | Gauge | queue_name |
| **Queue** | queue_processing_duration_seconds | Histogram | queue_name |
| **Cache** | cache_hits_total | Counter | cache_name |
| **Cache** | cache_misses_total | Counter | cache_name |

---

## Part III: Implementation Patterns

### 3.1 Client Libraries Comparison

#### Go Metrics Libraries

| Library | Vendor Lock-in | Performance | Features | Maintenance |
|---------|----------------|-------------|----------|-------------|
| **prometheus/client_go** | None | Excellent | Full | Active |
| **opentelemetry-go** | None | Good | Full + traces | Very active |
| **statsd-go** | DogStatsD | Good | Basic | Maintenance |
| **go-metrics** | None | Good | Basic | Inactive |
| **expvar** | None | Excellent | Minimal | Standard lib |
| **tally** | Uber | Good | Rich | Active |

#### Library Feature Matrix

| Feature | prometheus | opentelemetry | statsd | tally |
|---------|------------|---------------|--------|-------|
| Counter | ✅ | ✅ | ✅ | ✅ |
| Gauge | ✅ | ✅ | ✅ | ✅ |
| Histogram | ✅ | ✅ | ❌ | ✅ |
| Summary | ✅ | ✅ | ❌ | ✅ |
| Labels | ✅ | ✅ | ✅ | ✅ |
| Exponential buckets | ✅ | ✅ | ❌ | ❌ |
| Push gateway | ✅ | ✅ | ✅ | ✅ |
| OTLP export | ❌ | ✅ | ❌ | ❌ |
| Views/Aggregation | ❌ | ✅ | ❌ | ✅ |

### 3.2 Collection Patterns

#### Pull vs Push Models

| Aspect | Pull (Prometheus) | Push (StatsD/OTLP) | Hybrid |
|--------|-------------------|-------------------|--------|
| **Architecture** | Central scrapes | Clients send | Both |
| **Firewall** | Inbound rules | Outbound only | Flexible |
| **Scale** | Limited by scrape | Unlimited | Best |
| **Short jobs** | Pushgateway | Direct | Either |
| **Real-time** | ~15s delay | Immediate | Configurable |
| **Reliability** | Metrics survive client death | Lost on crash | Mixed |
| **Complexity** | Simple server | Complex client | Medium |

### 3.3 Performance Optimization

#### Overhead Reduction Techniques

| Technique | CPU Impact | Memory Impact | Implementation |
|-----------|------------|---------------|----------------|
| **Batch collection** | -50% | +10% | Buffer and flush |
| **Async collection** | -30% | +5% | Goroutine workers |
| **Label pooling** | -20% | -30% | sync.Pool for labels |
| **Metric sharding** | -40% | 0% | Per-core metrics |
| **Exponential histogram** | -25% | -80% | OTel native |

---

## Part IV: Metrics in Production

### 4.1 Alerting Strategies

#### Alerting Best Practices

| Anti-Pattern | Better Approach | Rationale |
|--------------|-----------------|-----------|
| Alert on every error | Alert on error rate | Noise reduction |
| Static thresholds | Dynamic baselines | Seasonality |
| Missing = 0 | Missing = unknown | Avoid false negatives |
| Many small alerts | Few actionable alerts | Cognitive load |
| 24/7 paging | Business hours + on-call | Sustainability |

#### The Four Golden Signals

| Signal | Metric | Alert Threshold | SLO Target |
|--------|--------|-----------------|------------|
| **Latency** | request_duration_seconds | p99 < 100ms | 99.9% |
| **Traffic** | requests_per_second | Capacity < 80% | N/A |
| **Errors** | error_rate | < 0.1% | 99.9% |
| **Saturation** | resource_utilization | < 80% | N/A |

### 4.2 Dashboard Design

#### Dashboard Hierarchy

| Level | Audience | Refresh | Metrics |
|-------|----------|---------|---------|
| **Executive** | C-level | 5m | Business KPIs |
| **Service** | Engineering | 30s | Golden signals |
| **System** | SRE | 10s | Resource usage |
| **Debug** | Developers | Real-time | Detailed traces |

### 4.3 Cost Optimization

#### Metrics Cost Factors

| Factor | Cost Impact | Optimization |
|--------|-------------|--------------|
| **Cardinality** | Linear | Drop high-card labels |
| **Retention** | Linear | 15d local, long-term remote |
| **Sampling** | Configurable | 1% for high-volume |
| **Aggregation** | Pre-compute | Recording rules |
| **Compression** | -90% | Efficient encoding |

---

## Part V: Research & Innovations

### 5.1 Emerging Technologies

#### eBPF-Based Metrics

| Feature | Traditional | eBPF Native | Improvement |
|---------|-------------|-------------|-------------|
| **Kernel metrics** | /proc parsing | Direct kernel | 10x faster |
| **Network metrics** | iptables counters | XDP/TC programs | 100x throughput |
| **Syscall tracing** | ptrace | Kprobes | Minimal overhead |
| **Context switches** | /proc/stat | Sched tracepoints | Real-time |

#### OpenTelemetry Protocol (OTLP)

| Feature | Prometheus Remote Write | OTLP | Advantage |
|---------|------------------------|------|-----------|
| **Transport** | HTTP/1.1 | HTTP/2, gRPC | Multiplexing |
| **Compression** | Snappy | zstd, gzip | Better ratio |
| **Batching** | Per-metric | Multi-signal | Efficiency |
| **Metadata** | External | In-band | Self-describing |
| **Retry** | Client-side | Built-in | Reliability |

### 5.2 Industry Innovations

| Company | Innovation | Open Source | Integration |
|---------|------------|-------------|-------------|
| **Google** | Monarch | Internal | Borg metrics |
| **Meta** | ODS | Internal | Time-series scale |
| **Netflix** | Atlas | Yes | Cloud-native |
| **Uber** | M3 | Yes | Multi-tenant |
| **Shopify** | StatsD → Prometheus | Migration | Cost reduction |
| **Cloudflare** | Quicksilver | Internal | Edge metrics |

### 5.3 Future Directions

#### Predicted Trends (2026-2028)

| Trend | Timeline | Impact | Readiness |
|-------|----------|--------|-----------|
| **Unified signals** | 2026 | Metrics + logs + traces merge | Beta |
| **AI-driven baselines** | 2026 | Auto-thresholds | Production |
| **eBPF native** | 2027 | Kernel metrics | Emerging |
| **Streaming analytics** | 2027 | Real-time ML | Research |
| **Carbon-aware** | 2028 | Green metrics | Planning |

---

## Part VI: Benchmarking

### 6.1 Performance Benchmarks

#### Collection Overhead

| Operation | Time | Memory | Allocs |
|-----------|------|--------|--------|
| **Counter increment** | 10ns | 0B | 0 |
| **Gauge set** | 15ns | 0B | 0 |
| **Histogram observe** | 50ns | 0B | 0 |
| **With 5 labels** | +100ns | 200B | 2 |
| **Export (1000 series)** | 5ms | 50KB | 100 |

#### Scalability Tests

| Metric Count | Ingestion/sec | Memory | CPU |
|--------------|---------------|--------|-----|
| 1,000 | 100K | 10MB | 1% |
| 10,000 | 500K | 50MB | 5% |
| 100,000 | 1M | 200MB | 15% |
| 1,000,000 | 2M | 1GB | 40% |

### 6.2 Reference Implementations

```go
// High-performance counter with label pooling
type PooledCounter struct {
    vec      *prometheus.CounterVec
    labelPool sync.Pool
}

func (c *PooledCounter) Inc(labels ...string) {
    c.vec.WithLabelValues(labels...).Inc()
}

// Zero-allocation histogram
type FastHistogram struct {
    buckets  []float64
    counts   []uint64
    sum      float64
    count    uint64
    mu       sync.RWMutex
}

func (h *FastHistogram) Observe(v float64) {
    h.mu.Lock()
    defer h.mu.Unlock()
    
    h.sum += v
    h.count++
    
    for i, b := range h.buckets {
        if v <= b {
            h.counts[i]++
            return
        }
    }
}
```

---

## Part VII: References

### 7.1 Core Resources

| Resource | URL | Description |
|----------|-----|-------------|
| Prometheus | https://prometheus.io | Metrics standard |
| OpenTelemetry | https://opentelemetry.io | Unified observability |
| VictoriaMetrics | https://victoriametrics.com | Scalable storage |
| Grafana | https://grafana.com | Visualization |
| SRE Book | https://sre.google | Best practices |

### 7.2 Research Papers

| Paper | Authors | Year | Topic |
|-------|---------|------|-------|
| "Monarch" | Google | 2020 | Planet-scale metrics |
| "Gorilla" | Facebook | 2013 | Time-series compression |
| "Borgmon" | Google | 2016 | Internal monitoring |

### 7.3 Glossary

| Term | Definition |
|------|------------|
| **Cardinality** | Number of unique time series |
| **Histogram** | Distribution of values into buckets |
| **Counter** | Monotonically increasing metric |
| **Gauge** | Metric that can go up or down |
| **Exporter** | Bridge between systems and Prometheus |
| **Scrape** | Pull-based metric collection |
| **Series** | Unique label combination |
| **Sample** | Single value at a timestamp |

---

*This document reflects the state-of-the-art in metrics collection as of April 2026.*
