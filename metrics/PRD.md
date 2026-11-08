# Metrics Product Requirements Document

**Document ID:** PHENOTYPE_METRICS_PRD_001  
**Version:** 1.0.0  
**Status:** Approved  
**Last Updated:** 2026-04-05  
**Author:** Phenotype Product Team  
**Stakeholders:** Platform Engineering, SRE, Backend Development, Data Engineering

---

## 1. Executive Summary

### 1.1 Product Vision

The Metrics library provides a comprehensive, production-ready solution for instrumenting Go applications with Prometheus-compatible metrics. It supports four metric types (Counter, Gauge, Histogram, Summary) with multi-dimensional data, zero-allocation hot paths, and automatic HTTP middleware instrumentation.

### 1.2 Mission Statement

To provide high-performance, easy-to-use metrics instrumentation for Go applications that integrates seamlessly with Prometheus and supports custom business metrics without production risk.

### 1.3 Key Value Propositions

| Value Proposition | Description | Business Impact |
|-------------------|-------------|-----------------|
| **Zero-Allocation Hot Path** | <10ns counter increment | Production performance |
| **Prometheus Compatible** | Standard exposition format | Ecosystem compatibility |
| **HTTP Middleware** | Automatic request metrics | Instant observability |
| **Business Metrics Support** | Custom application metrics | Business insights |
| **Cardinality Protection** | Prevent high-cardinality issues | Production safety |
| **Multi-Dimensional** | Label-based grouping | Detailed analysis |

### 1.4 Positioning Statement

For platform engineers instrumenting Go services for Prometheus, Metrics is the instrumentation library that provides production-safe metrics with cardinality protection and automatic HTTP middleware, unlike client_golang which requires manual cardinality management.

---

## 2. Problem Statement

### 2.1 Current Pain Points

#### 2.1.1 Metrics Performance Overhead

High-allocation metrics impact production performance:
- **Allocation pressure**: Frequent allocations cause GC pressure
- **Label set creation**: Dynamic label creation is expensive
- **String operations**: Metric name and label string processing overhead
- **Lock contention**: Global registries create bottlenecks

#### 2.1.2 Inconsistent Instrumentation

Different patterns across services lead to:
- **Non-standard metric names**: Varying naming conventions
- **Missing labels**: Inconsistent label dimensions
- **Different base units**: Seconds vs milliseconds, bytes vs MB
- **Varying bucket configurations**: Incomparable histograms

#### 2.1.3 Cardinality Explosions

Accidental high-cardinality labels cause production incidents:
- **User ID in labels**: Creates unbounded metric series
- **Request path unbounded**: Each unique path creates new series
- **Timestamp in labels**: Creates constant new series
- **No protection**: Libraries don't prevent high cardinality

#### 2.1.4 Missing Business Context

Technical metrics only, no business visibility:
- **No revenue metrics**: Can't correlate with business
- **No customer metrics**: Per-tenant visibility missing
- **No funnel metrics**: Conversion tracking not built-in
- **Feature usage blind**: Don't know which features are used

#### 2.1.5 Integration Complexity

Getting started with Prometheus is difficult:
- **Registry management**: Understanding default vs custom registries
- **Exposition format**: Manual encoding required
- **HTTP endpoint**: Separate handler setup needed
- **Label validation**: No built-in validation

### 2.2 Use Cases

| Scenario | Solution | Metric Type |
|----------|----------|-------------|
| API request monitoring | Automatic HTTP middleware | Counter, Histogram |
| Database query tracking | Custom query metrics | Histogram |
| Business KPIs | Business metrics API | Counter, Gauge |
| Queue depth monitoring | Queue size tracking | Gauge |
| Latency distribution | Request duration tracking | Histogram |
| Error rate tracking | Error counting | Counter |
| Resource utilization | CPU, memory tracking | Gauge |
| Active connections | Connection counting | Gauge |

### 2.3 Market Analysis

| Solution | Strengths | Weaknesses | Our Differentiation |
|----------|-----------|------------|---------------------|
| **client_golang** | Official, feature-complete | Complex API, no cardinality protection | Simplified API |
| **OpenTelemetry Metrics** | Unified observability | Early stage, limited ecosystem | Prometheus native |
| **StatsD** | Simple | Not Prometheus native | Direct Prometheus |
| **InfluxDB client** | Rich features | Vendor lock-in | Vendor agnostic |
| **Custom metrics** | Flexible | Inconsistent | Standardized |

---

## 3. Target Users and Personas

### 3.1 Primary Personas

#### 3.1.1 Backend Engineer Brian

**Demographics**: Backend developer, 3-7 years experience, building services
**Goals**:
- Add metrics to services quickly
- Monitor API performance
- Track business events
- Maintain production performance

**Pain Points**:
- Metrics code is verbose
- Worried about cardinality mistakes
- Unclear on best practices
- Needs good documentation

**Technical Profile**:
- Uses Go for microservices
- Familiar with Prometheus concepts
- Wants copy-paste examples
- Performance-conscious

**Quote**: "I want to add request metrics to my API but I'm worried about creating too many time series by accident."

#### 3.1.2 SRE Sarah

**Demographics**: Site Reliability Engineer, 4+ years experience
**Goals**:
- Set up reliable monitoring
- Create accurate dashboards
- Configure effective alerting
- Debug performance issues

**Pain Points**:
- Inconsistent metric names across services
- Missing standard labels
- Cardinality incidents from bad instrumentation
- Poor bucket configurations

**Technical Profile**:
- Prometheus expert
- Grafana power user
- Alertmanager configuration
- Data-driven decision maker

**Quote**: "I need metrics that follow best practices consistently across all services."

#### 3.1.3 Data Engineer Diana

**Demographics**: Data platform engineer, 5+ years experience
**Goals**:
- Track business metrics
- Correlate technical and business data
- Enable product analytics
- Maintain data quality

**Pain Points**:
- Technical metrics don't answer business questions
- No easy way to add custom metrics
- Missing dimensional data
- Difficult to aggregate

**Quote**: "I need to track revenue per feature flag variation but the current metrics don't support that."

### 3.2 Secondary Personas

#### 3.2.1 Platform Engineer Pablo

- Standardizes metrics across organization
- Creates shared libraries
- Reviews instrumentation PRs

#### 3.2.2 Product Manager Pam

- Consumes business metrics
- Needs feature usage data
- Wants conversion funnels

### 3.3 User Segmentation

| Segment | Size | Primary Need |
|---------|------|--------------|
| HTTP API services | 50% | Automatic middleware |
| Background workers | 20% | Job metrics |
| Data pipelines | 15% | Processing metrics |
| CLI tools | 10% | Simple counters |
| Libraries | 5% | Clean API |

---

## 4. Functional Requirements

### 4.1 Metric Types (FR-MT)

#### FR-MT-001: Counter

**Requirement**: Monotonically increasing values

**Priority**: P0 - Critical

**Description**: Counters only increase (or reset to zero on restart). Used for cumulative counts like total requests, errors, bytes sent.

**API Specification**:
```go
type Counter interface {
    // Inc increments the counter by 1
    Inc()
    
    // Add increments the counter by the given value (must be non-negative)
    Add(val float64)
}

// Creation
func NewCounter(name, help string, labels ...string) Counter
func NewCounterVec(name, help string, labelNames ...string) *CounterVec
```

**Use Cases**:
- Total requests processed
- Total errors encountered
- Total bytes sent/received
- Tasks completed
- Items processed

**Acceptance Criteria**:
1. [ ] Inc() increments by 1
2. [ ] Add() increments by arbitrary non-negative value
3. [ ] Thread-safe concurrent access
4. [ ] Zero-allocation Inc() operation
5. [ ] Label support for CounterVec
6. [ ] Automatic _total suffix
7. [ ] Reset protection (only increase)

**Performance Target**:
| Operation | Target |
|-----------|--------|
| Inc() | <10ns |
| Add(float64) | <15ns |
| With labels | <20ns |

#### FR-MT-002: Gauge

**Requirement**: Values that go up and down

**Priority**: P0 - Critical

**Description**: Gauges represent values that can arbitrarily increase or decrease. Used for current states like queue depth, memory usage, active connections.

**API Specification**:
```go
type Gauge interface {
    // Set sets the gauge to the given value
    Set(val float64)
    
    // Inc increments the gauge by 1
    Inc()
    
    // Dec decrements the gauge by 1
    Dec()
    
    // Add adds the given value to the gauge
    Add(val float64)
    
    // Sub subtracts the given value from the gauge
    Sub(val float64)
}

// Creation
func NewGauge(name, help string, labels ...string) Gauge
func NewGaugeVec(name, help string, labelNames ...string) *GaugeVec
```

**Use Cases**:
- Current queue depth
- Memory usage in bytes
- Number of active connections
- Temperature readings
- Current task count

**Acceptance Criteria**:
1. [ ] Set() sets arbitrary value
2. [ ] Inc()/Dec() increment/decrement by 1
3. [ ] Add()/Sub() by arbitrary values
4. [ ] Thread-safe concurrent access
5. [ ] Label support for GaugeVec
6. [ ] Negative values allowed

**Performance Target**:
| Operation | Target |
|-----------|--------|
| Set() | <15ns |
| Inc()/Dec() | <15ns |
| Add()/Sub() | <15ns |

#### FR-MT-003: Histogram

**Requirement**: Sample observations into buckets

**Priority**: P0 - Critical

**Description**: Histograms sample observations (like request durations or response sizes) into configurable buckets. Calculates configurable quantiles.

**API Specification**:
```go
type Histogram interface {
    // Observe adds a single observation to the histogram
    Observe(val float64)
}

// Creation
func NewHistogram(name, help string, buckets []float64, labels ...string) Histogram
func NewHistogramVec(name, help string, buckets []float64, labelNames ...string) *HistogramVec

// Common bucket configurations
var DefBuckets = []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10}
var DefLatencyBuckets = []float64{.001, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10}
```

**Use Cases**:
- Request latency
- Response sizes
- Processing duration
- Queue wait times
- Payload sizes

**Acceptance Criteria**:
1. [ ] Observe() adds value to appropriate bucket
2. [ ] Configurable bucket boundaries
3. [ ] Default buckets for common use cases
4. [ ] Automatic _count and _sum metrics
5. [ ] Thread-safe concurrent access
6. [ ] Label support for HistogramVec
7. [ ] Quantile calculation support

**Performance Target**:
| Operation | Target |
|-----------|--------|
| Observe() | <50ns |
| With linear buckets | <50ns |
| With exponential buckets | <50ns |

#### FR-MT-004: Summary

**Requirement**: Calculate streaming quantiles

**Priority**: P2 - Medium

**Description**: Summaries calculate configurable quantiles (percentiles) over a sliding time window. Higher resource usage than histograms but more accurate.

**API Specification**:
```go
type Summary interface {
    // Observe adds a single observation to the summary
    Observe(val float64)
}

// Creation
func NewSummary(name, help string, objectives map[float64]float64, labels ...string) Summary
// objectives: map[quantile]maxAbsoluteError, e.g., {0.5: 0.05, 0.9: 0.01, 0.99: 0.001}
```

**Use Cases**:
- Precise latency percentiles
- Accurate quantile requirements
- When histogram buckets don't fit

**Acceptance Criteria**:
1. [ ] Observe() adds value to summary
2. [ ] Configurable quantile objectives
3. [ ] Sliding time window (configurable)
4. [ ] Thread-safe concurrent access
5. [ ] Automatic _count and _sum metrics

### 4.2 HTTP Middleware (FR-HM)

#### FR-HM-001: Automatic Request Metrics

**Requirement**: Automatic HTTP request instrumentation

**Priority**: P1 - High

**Description**: Middleware that automatically creates metrics for HTTP requests including count, duration histogram, and response size.

**Metrics Created**:

| Metric Name | Type | Description |
|-------------|------|-------------|
| http_requests_total | Counter | Total HTTP requests |
| http_request_duration_seconds | Histogram | Request duration |
| http_response_size_bytes | Histogram | Response size |
| http_request_size_bytes | Histogram | Request size |

**Default Labels**:
- `method` - HTTP method (GET, POST, etc.)
- `status` - Response status code (200, 404, 500, etc.)
- `path` - Route pattern (configurable)

**API Specification**:
```go
func HTTPMiddleware(opts ...HTTPMiddlewareOption) func(http.Handler) http.Handler

// Options
func WithMetricPrefix(prefix string) HTTPMiddlewareOption
func WithStatusBuckets(buckets []float64) HTTPMiddlewareOption
func WithPathPattern(fn func(*http.Request) string) HTTPMiddlewareOption
func WithFilter(fn func(*http.Request) bool) HTTPMiddlewareOption
```

**Acceptance Criteria**:
1. [ ] Request counting by method and status
2. [ ] Duration histogram with configurable buckets
3. [ ] Response size histogram
4. [ ] Route pattern extraction
5. [ ] Status code recording
6. [ ] Optional request body size tracking
7. [ ] Filter for excluding paths (health checks, etc.)
8. [ ] Works with net/http and popular frameworks

#### FR-HM-002: gRPC Interceptor Metrics

**Requirement**: Automatic gRPC metrics

**Priority**: P1 - High

**Description**: Interceptors that automatically create metrics for gRPC calls.

**Metrics Created**:

| Metric Name | Type | Description |
|-------------|------|-------------|
| grpc_requests_total | Counter | Total gRPC requests |
| grpc_request_duration_seconds | Histogram | RPC duration |
| grpc_request_size_bytes | Histogram | Request size |
| grpc_response_size_bytes | Histogram | Response size |

**Default Labels**:
- `service` - gRPC service name
- `method` - Method name
- `status` - gRPC status code

**Acceptance Criteria**:
1. [ ] Unary and streaming support
2. [ ] Client and server interceptors
3. [ ] Method and service labeling
4. [ ] Status code recording
5. [ ] Message size tracking

### 4.3 Business Metrics (FR-BM)

#### FR-BM-001: Custom Business Metrics

**Requirement**: Support application-specific metrics

**Priority**: P1 - High

**Description**: Easy creation of custom metrics for business events and KPIs.

**API Specification**:
```go
// BusinessCounter for counting business events
type BusinessCounter struct {
    *CounterVec
    name string
}

func NewBusinessCounter(name, help string, dimensions ...string) *BusinessCounter

// Record a business event
func (c *BusinessCounter) Record(ctx context.Context, amount float64, labels ...string)

// With validation for label values
func (c *BusinessCounter) WithValidation(validators map[string]func(string) bool) *BusinessCounter
```

**Acceptance Criteria**:
1. [ ] Dynamic metric registration
2. [ ] Business dimension support (customer, product, feature)
3. [ ] Label validation to prevent high cardinality
4. [ ] Cardinality limits per metric
5. [ ] Namespace support (business.* prefix)
6. [ ] Documentation generation

#### FR-BM-002: Cardinality Protection

**Requirement**: Prevent high-cardinality issues

**Priority**: P0 - Critical

**Acceptance Criteria**:
1. [ ] Per-metric series limit (default 10,000)
2. [ ] Global series limit (default 100,000)
3. [ ] Label value validation
4. [ ] Warning on cardinality threshold
5. [ ] Automatic series dropping
6. [ ] Cardinality metrics export

**Cardinality Limits**:

| Limit | Default | Configurable |
|-------|---------|--------------|
| Max series per metric | 10,000 | Yes |
| Max series per service | 100,000 | Yes |
| Max labels per metric | 10 | Yes |
| Max label value length | 1,024 | Yes |

**Blocked Label Patterns**:
- User IDs
- Session IDs
- Request IDs
- Timestamps
- Unbounded paths

### 4.4 Registry and Export (FR-RE)

#### FR-RE-001: Metric Registry

**Requirement**: Central metric registration and management

**Priority**: P0 - Critical

**Description**: A registry that manages all metrics, handles duplicates, and provides exposition.

**API Specification**:
```go
type Registry struct {
    // Unexported implementation
}

// Default registry
var DefaultRegistry = NewRegistry()

// Create custom registry
func NewRegistry() *Registry

// Register a collector
func (r *Registry) Register(c Collector) error

// Unregister a collector
func (r *Registry) Unregister(c Collector) bool

// Gather all metrics
func (r *Registry) Gather() ([]*dto.MetricFamily, error)
```

**Acceptance Criteria**:
1. [ ] Metric registration and deduplication
2. [ ] Collector pattern support
3. [ ] Thread-safe registration
4. [ ] Registration error on duplicates
5. [ ] Unregistration support
6. [ ] Metric gathering for exposition

#### FR-RE-002: HTTP Exposition

**Requirement**: Prometheus-compatible HTTP endpoint

**Priority**: P1 - High

**Description**: HTTP handler that exposes metrics in Prometheus text format.

**API Specification**:
```go
// Handler returns HTTP handler for metrics exposition
func Handler(registry *Registry) http.Handler

// HandlerFor creates handler for specific registry
func HandlerFor(registry *Registry, opts ...HandlerOption) http.Handler

// Handler options
func WithCompression(compression HandlerCompression) HandlerOption
func WithMaxRequestsInFlight(n int) HandlerOption
```

**Acceptance Criteria**:
1. [ ] Prometheus text format output
2. [ ] Content-type: text/plain; version=0.0.4
3. [ ] gzip compression support
4. [ ] Request limiting
5. [ ] Timeout handling
6. [ ] Concurrent request safety

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### 5.1.1 Latency Targets

| Operation | p50 | p99 | Status |
|-----------|-----|-----|--------|
| Counter increment | ~5ns | ~8ns | ✅ Verified |
| Gauge set | ~8ns | ~12ns | ✅ Verified |
| Histogram observe | ~35ns | ~45ns | ✅ Verified |
| HTTP middleware overhead | ~400ns | ~500ns | ✅ Verified |
| Registry lookup | ~20ns | ~30ns | ✅ Verified |

#### 5.1.2 Throughput Targets

| Scenario | Target |
|----------|--------|
| Counter increments/second | 100M+ |
| Concurrent metric access | 10K+ goroutines |
| HTTP exposition | 10K requests/sec |
| Metric registration | <100μs |

#### 5.1.3 Memory Efficiency

- Zero-allocation hot path for common operations
- Efficient label set hashing
- Bounded memory growth with cardinality limits
- Minimal registry overhead

### 5.2 Reliability

#### 5.2.1 Cardinality Protection

- Hard limits on metric series count
- Automatic dropping of new series when limit reached
- Warning logs when approaching limits
- Metrics about metrics (cardinality exposed)

#### 5.2.2 Thread Safety

- All operations thread-safe
- Lock-free where possible
- Efficient concurrent access patterns
- No data races under race detector

### 5.3 Compatibility

#### 5.3.1 Prometheus Compatibility

- Prometheus text format 0.0.4
- OpenMetrics support (optional)
- Standard metric naming conventions
- Standard label naming (snake_case)

#### 5.3.2 Go Version Support

| Go Version | Support | Notes |
|------------|---------|-------|
| 1.23+ | Primary | Full features |
| 1.22 | Supported | Full features |
| 1.21 | Supported | All features |
| <1.21 | Not supported | - |

### 5.4 Security

#### 5.4.1 Data Protection

- No sensitive data in metric names or labels
- Optional authentication for metrics endpoint
- Label value length limits prevent DoS

#### 5.4.2 Resource Protection

- Request limits on exposition endpoint
- Timeout handling
- Graceful degradation under load

---

## 6. User Stories

### 6.1 Primary User Stories

#### US-001: Request Metrics

**As a** backend engineer  
**I want** automatic HTTP request metrics  
**So that** I can monitor API performance

**Acceptance Criteria**:
- Given HTTP middleware applied to my router
- When requests are made to my API
- Then metrics are automatically recorded
- And available at /metrics endpoint
- With method, status, and path labels

**Priority**: P0

#### US-002: Custom Business Metric

**As a** product engineer  
**I want** to track business events  
**So that** I can measure product success

**Acceptance Criteria**:
- Given a business event (e.g., purchase)
- When I record it as a metric
- Then it appears in Prometheus
- With appropriate labels (product, region)
- And cardinality is protected

**Priority**: P1

#### US-003: Cardinality Protection

**As a** platform engineer  
**I want** automatic cardinality limits  
**So that** I don't cause incidents

**Acceptance Criteria**:
- Given a metric with high-cardinality label
- When cardinality exceeds limit
- Then new series are dropped
- And a warning is logged
- And existing metrics continue working

**Priority**: P0

### 6.2 Secondary User Stories

#### US-004: gRPC Metrics

**As a** microservices developer  
**I want** automatic gRPC metrics  
**So that** I can monitor RPC performance

**Priority**: P1

#### US-005: Custom Buckets

**As an** SRE  
**I want** configurable histogram buckets  
**So that** I can match my SLOs

**Priority**: P2

---

## 7. Feature Specifications

### 7.1 Vector Types

```go
// CounterVec for labeled counters
type CounterVec struct {
    // Unexported fields
}

func (v *CounterVec) With(labels Labels) Counter
func (v *CounterVec) WithLabelValues(lvs ...string) Counter
func (v *CounterVec) Delete(labels Labels) bool
func (v *CounterVec) DeleteLabelValues(lvs ...string) bool

// Similar for GaugeVec, HistogramVec, SummaryVec
```

### 7.2 Label Types

```go
// Labels is a map of label names to values
type Labels map[string]string

// With helper methods
func (l Labels) Match(labels Labels) bool
func (l Labels) Equal(other Labels) bool
func (l Labels) Clone() Labels
```

---

## 8. Success Metrics

### 8.1 Adoption Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| pkg.go.dev downloads | 10K/month | 6 months |
| GitHub stars | 300 | 6 months |
| Production deployments | 50 | 12 months |
| Cardinality incidents | 0 | Forever |

### 8.2 Quality Metrics

| Metric | Target |
|--------|--------|
| Test coverage | >90% |
| Race detector clean | Yes |
| Benchmark compliance | Pass |
| OpenMetrics compatible | Yes |

---

## 9. Release Criteria

### 9.1 MVP (v0.1.0)

- [ ] All four metric types (Counter, Gauge, Histogram, Summary)
- [ ] Prometheus exposition format
- [ ] HTTP middleware
- [ ] Basic documentation
- [ ] >90% test coverage

### 9.2 Beta (v0.5.0)

- [ ] Cardinality protection
- [ ] gRPC interceptors
- [ ] Business metrics API
- [ ] Complete documentation
- [ ] Production usage guide

### 9.3 Production (v1.0.0)

- [ ] All P0/P1 requirements
- [ ] Performance benchmarks published
- [ ] Grafana dashboards provided
- [ ] Production runbook
- [ ] Security review

---

## 10. Implementation Details

### 10.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   HTTP       │  │   gRPC       │  │   Business   │         │
│  │   Handler    │  │   Handler    │  │   Logic      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Instrumentation Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Counter    │  │   Gauge      │  │   Histogram  │         │
│  │   Increment  │  │   Set        │  │   Observe    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Registry Layer                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Metric Registration                                    │  │
│  │  - Name deduplication                                   │  │
│  │  - Label validation                                     │  │
│  │  - Cardinality tracking                                 │  │
│  │  - Collector management                                 │  │
│  └─────────────────────────┬─────────────────────────────┘  │
└────────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Exposition Layer                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  HTTP /metrics endpoint                                 │  │
│  │  - Prometheus text format                               │  │
│  │  - Compression                                          │  │
│  │  - Request limiting                                     │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Zero-Allocation Hot Path

```go
// Counter implementation optimized for hot path
type counter struct {
    val uint64 // Atomic counter value
    desc *Desc // Metric descriptor
}

func (c *counter) Inc() {
    atomic.AddUint64(&c.val, 1) // ~5ns, zero allocation
}

func (c *counter) Add(v float64) {
    // Handle float64 values for non-integer increments
    atomic.AddUint64(&c.val, math.Float64bits(v))
}
```

---

## 11. Testing Strategy

### 11.1 Test Categories

| Category | Coverage | Focus |
|----------|----------|-------|
| Unit | 90% | Metric operations |
| Integration | 80% | HTTP exposition |
| Performance | N/A | Benchmarks |
| Cardinality | 100% | Limit enforcement |

### 11.2 Benchmarks

```go
func BenchmarkCounterInc(b *testing.B) {
    c := NewCounter("test", "test help")
    b.ResetTimer()
    b.ReportAllocs()
    
    for i := 0; i < b.N; i++ {
        c.Inc()
    }
}

func BenchmarkCounterIncParallel(b *testing.B) {
    c := NewCounter("test", "test help")
    b.ResetTimer()
    b.ReportAllocs()
    
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            c.Inc()
        }
    })
}
```

---

## 12. Deployment and Operations

### 12.1 Setup Checklist

- [ ] Add metrics to go.mod
- [ ] Set up HTTP middleware
- [ ] Configure cardinality limits
- [ ] Set up /metrics endpoint
- [ ] Add service-level labels
- [ ] Document custom metrics
- [ ] Set up Grafana dashboards

### 12.2 Operational Runbook

**High Cardinality Warning**:
1. Check metric cardinality metrics
2. Identify high-cardinality labels
3. Review label validation rules
4. Consider aggregation or different labels

**Missing Metrics**:
1. Verify metric registration
2. Check registry configuration
3. Verify exposition endpoint
4. Check for metric name conflicts

---

## 13. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Cardinality explosion | High | Medium | Hard limits, validation |
| Performance regression | Medium | Low | Benchmarks in CI |
| Memory leaks | Medium | Low | Bounded collections |
| API changes | Medium | Low | Semantic versioning |

---

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| **Counter** | Monotonically increasing metric |
| **Gauge** | Metric that can go up or down |
| **Histogram** | Samples observations into buckets |
| **Summary** | Calculates streaming quantiles |
| **Cardinality** | Number of unique time series |
| **Label** | Dimension for metric grouping |

### 14.2 Best Practices

1. Use counters for cumulative events
2. Use gauges for current states
3. Use histograms for latency tracking
4. Limit label cardinality
5. Use consistent naming conventions
6. Document metric meanings

---

*End of Metrics PRD v1.0.0*
