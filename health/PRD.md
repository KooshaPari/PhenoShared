# Health Product Requirements Document

**Document ID:** PHENOTYPE_HEALTH_PRD_001  
**Version:** 1.0.0  
**Status:** Approved  
**Last Updated:** 2026-04-05  
**Author:** Phenotype Product Team  
**Stakeholders:** Platform Engineering, SRE, DevOps, Kubernetes Teams

---

## 1. Executive Summary

### 1.1 Product Vision

Health provides a comprehensive health checking framework for Go applications, designed to support Kubernetes-native deployments, microservices architectures, and distributed systems with multi-probe support and production-ready observability.

### 1.2 Mission Statement

To provide the most reliable, flexible, and observable health checking solution for Go applications, enabling teams to define, manage, and expose health checks with minimal configuration and maximum operational value.

### 1.3 Key Value Propositions

| Value Proposition | Description | Business Impact |
|-------------------|-------------|-----------------|
| **Multi-Probe Support** | Liveness, readiness, startup probes | Complete K8s integration |
| **Custom Check Registration** | Extensible health logic | Application-specific checks |
| **Concurrent Execution** | Parallel health checks | Fast response times |
| **Detailed Status Reporting** | Rich health information | Operational visibility |
| **Built-in HTTP Endpoint** | Ready-to-use handlers | Reduced boilerplate |
| **Kubernetes Native** | Follows K8s health check patterns | Seamless deployment |

### 1.4 Positioning Statement

For platform engineers deploying Go applications to Kubernetes, Health is the health checking framework that provides production-ready, K8s-native health probes out of the box, unlike generic health libraries that require significant customization for container orchestration.

---

## 2. Problem Statement

### 2.1 Current Pain Points

#### 2.1.1 Fragmented Health Check Implementations

Every service implements health checks differently, leading to:
- **Inconsistent endpoints**: /health, /healthz, /status, /ready - no standardization
- **Varying response formats**: JSON, plain text, custom structures
- **Different status codes**: 200, 204, 503 usage varies
- **Mixed probe support**: Some only have liveness, missing readiness

#### 2.1.2 Kubernetes Integration Complexity

Proper probe configuration is error-prone:
- **Probe type confusion**: When to use liveness vs readiness vs startup
- **Timing misconfiguration**: Initial delay, period, timeout settings
- **Failure threshold tuning**: Balancing sensitivity vs stability
- **Endpoint exposure**: Security concerns with health endpoints

#### 2.1.3 Limited Observability

Basic pass/fail health checks don't help debugging:
- **No detailed status**: Just "healthy" or "unhealthy"
- **Missing component status**: Which component failed?
- **No historical data**: When did health change?
- **No metrics**: How often do checks fail?

#### 2.1.4 Check Dependencies and Ordering

Managing check execution order is manual:
- **Database before API**: API check fails if DB not ready
- **Cache before processing**: Processing needs cache
- **External services**: Order matters for dependent services
- **Circular dependencies**: Complex dependency graphs

#### 2.1.5 Production Hardening Gaps

Missing features for production use:
- **No caching**: Every probe hits the system
- **No timeouts**: Checks can hang indefinitely
- **No retries**: Transient failures cause restarts
- **No circuit breakers**: Failing checks overwhelm system

### 2.2 Use Cases

| Scenario | Solution | Probe Type |
|----------|----------|------------|
| Kubernetes deployment | Health endpoint for K8s probes | All types |
| Database health | Connection pool verification | Readiness |
| External dependencies | Third-party service checks | Readiness |
| Resource exhaustion | Memory/CPU monitoring | Liveness |
| Maintenance windows | Configurable silence periods | Readiness |
| Graceful shutdown | Draining in-flight requests | Readiness |
| Long startup | Slow initialization handling | Startup |
| Multi-region | Geographic health aggregation | Custom |

### 2.3 Market Analysis

| Solution | Strengths | Weaknesses | Our Differentiation |
|----------|-----------|------------|---------------------|
| **K8s Probes** | Native integration | Manual implementation | Library support |
| **Health Go** | Simple | Limited features | Full-featured |
| **go-health** | Extensible | Complex config | Convention-based |
| **Custom code** | Flexible | Inconsistent | Standardized |
| **Prometheus** | Metrics | Not health checks | Complementary |

---

## 3. Target Users and Personas

### 3.1 Primary Personas

#### 3.1.1 Platform Engineer Priya

**Demographics**: Platform/Infrastructure engineer, 5+ years experience
**Goals**:
- Standardize health checks across organization
- Enable reliable Kubernetes deployments
- Provide debugging information during incidents
- Minimize resource overhead

**Pain Points**:
- Inconsistent health check implementations
- Poor debugging information when unhealthy
- Complex configuration requirements
- Manual dependency management

**Technical Profile**:
- Kubernetes expert
- Defines organizational standards
- Reviews service configurations
- Values reliability and consistency

**Quote**: "I need health checks that work out of the box with Kubernetes, provide useful debugging info, and don't require every team to reinvent the wheel."

#### 3.1.2 SRE Sam

**Demographics**: Site Reliability Engineer, 4+ years experience
**Goals**:
- Monitor production health accurately
- Debug incidents quickly with health data
- Tune probe sensitivity
- Automate incident response

**Pain Points**:
- False positives causing unnecessary restarts
- Missing component details when unhealthy
- Can't distinguish critical vs non-critical failures
- No health history for post-incident analysis

**Technical Profile**:
- Manages production systems
- On-call rotation
- Uses observability tools extensively
- Data-driven decision maker

**Quote**: "When a service shows unhealthy, I need to know immediately which component failed and why - not just a 503 status code."

#### 3.1.3 Backend Developer Dana

**Demographics**: Go backend developer, 2-5 years experience
**Goals**:
- Add health checks quickly
- Understand Kubernetes probe behavior
- Debug health check failures
- Integrate with existing code

**Pain Points**:
- Confused by liveness vs readiness vs startup
- Unclear how to implement custom checks
- Testing health checks is difficult
- Don't understand K8s probe behavior

**Technical Profile**:
- Building microservices
- New to Kubernetes
- Wants simple, clear APIs
- Values good documentation

**Quote**: "I know I need health checks for Kubernetes, but I'm not sure what the difference is between liveness and readiness probes."

### 3.2 Secondary Personas

#### 3.2.1 DevOps Engineer Dave

- Configures CI/CD pipelines
- Sets up monitoring and alerting
- Needs health endpoint for load balancers

#### 3.2.2 Security Engineer Steve

- Reviews health endpoint exposure
- Ensures no sensitive data in health responses
- Configures network policies

### 3.3 User Segmentation

| Segment | Size | Primary Need |
|---------|------|--------------|
| K8s-deployed services | 60% | Native probe support |
| VM/bare-metal services | 20% | Health endpoints |
| Library developers | 10% | Check composition |
| CLI tools | 10% | Simple status checks |

---

## 4. Functional Requirements

### 4.1 Health Checking (FR-HC)

#### FR-HC-001: Health Checker Core

**Requirement**: Central health check management with configurable execution

**Priority**: P0 - Critical

**Description**: A central HealthChecker that manages registered health checks, executes them according to configuration, and aggregates results into health status.

**API Specification**:
```go
type Checker struct {
    checks   map[string]Check
    timeout  time.Duration
    parallel bool
    cache    *Cache
}

// Register adds a health check
func (c *Checker) Register(name string, check Check) error

// RegisterCheck configures a check with options
func (c *Checker) RegisterCheck(name string, check Check, opts ...CheckOption) error

// Check runs all checks and returns aggregated status
func (c *Checker) Check(ctx context.Context) *Status

// CheckSpecific runs only named checks
func (c *Checker) CheckSpecific(ctx context.Context, names ...string) *Status

// Deregister removes a check
func (c *Checker) Deregister(name string) error
```

**Acceptance Criteria**:
1. [ ] Register synchronous and asynchronous checks
2. [ ] Check deduplication by name
3. [ ] Parallel execution support with goroutines
4. [ ] Configurable global timeout
5. [ ] Per-check timeout support
6. [ ] Thread-safe concurrent registration
7. [ ] Check result caching
8. [ ] Check execution ordering by dependencies

#### FR-HC-002: Status Aggregation

**Requirement**: Combine individual check results into overall health status

**Priority**: P1 - High

**Description**: Support multiple strategies for combining check results into an overall health determination, with detailed reporting of individual check states.

**Aggregation Strategies**:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Strict** | All checks must pass | Critical systems |
| **Majority** | Majority must pass | Tolerant systems |
| **AtLeastOne** | At least one must pass | Redundant services |
| **Weighted** | Weighted scoring | Mixed criticality |
| **Custom** | User-defined function | Complex logic |

**API Specification**:
```go
type AggregationStrategy int

const (
    Strict AggregationStrategy = iota
    Majority
    AtLeastOne
    Weighted
)

func (c *Checker) SetAggregationStrategy(strategy AggregationStrategy)
func (c *Checker) SetCheckWeight(name string, weight float64)
```

**Acceptance Criteria**:
1. [ ] All aggregation strategies implemented
2. [ ] Configurable per-check criticality (critical vs non-critical)
3. [ ] Detailed result reporting (individual check states)
4. [ ] Historical status tracking (configurable retention)
5. [ ] Status transition callbacks
6. [ ] Custom aggregation function support

**Status Structure**:
```go
type Status struct {
    Status    HealthStatus              // Up, Down, Degraded
    Checks    map[string]*CheckResult   // Individual results
    Timestamp time.Time                 // Check time
    Duration  time.Duration              // Total check time
}

type CheckResult struct {
    Name      string        // Check name
    Status    HealthStatus  // Pass, Fail, Unknown
    Error     string        // Error message if failed
    Duration  time.Duration // Check execution time
    Metadata  map[string]any // Additional data
    Timestamp time.Time     // When checked
}
```

### 4.2 Probe Types (FR-PT)

#### FR-PT-001: Liveness Probe

**Requirement**: Kubernetes liveness probe endpoint

**Priority**: P0 - Critical

**Description**: HTTP endpoint that indicates if the application is running (not deadlocked). Used by Kubernetes to restart unhealthy containers.

**Kubernetes Behavior**:
- Liveness failure → Container restart
- Should be simple, fast check
- Only critical application state (not dependencies)
- Fast failure detection

**Acceptance Criteria**:
1. [ ] /healthz endpoint (configurable path)
2. [ ] Returns 200 when healthy
3. [ ] Returns 503 when unhealthy
4. [ ] Response time < 1ms for simple checks
5. [ ] Includes basic application state only
6. [ ] Kubernetes-compatible response format
7. [ ] Configurable failure threshold

**Example Response**:
```json
{
  "status": "up",
  "timestamp": "2026-04-05T10:30:00Z"
}
```

#### FR-PT-002: Readiness Probe

**Requirement**: Kubernetes readiness probe endpoint

**Priority**: P0 - Critical

**Description**: HTTP endpoint that indicates if the application is ready to receive traffic. Used by Kubernetes to add/remove from service endpoints.

**Kubernetes Behavior**:
- Readiness failure → Pod removed from service
- Should check all dependencies
- Can fluctuate during operation
- Used for graceful draining

**Acceptance Criteria**:
1. [ ] /readyz endpoint (configurable path)
2. [ ] Returns 200 when ready
3. [ ] Returns 503 when not ready
4. [ ] Includes all registered checks
5. [ ] Detailed status per component
6. [ ] Used for graceful shutdown signaling
7. [ ] Configurable check selection

**Example Response**:
```json
{
  "status": "down",
  "timestamp": "2026-04-05T10:30:00Z",
  "checks": {
    "database": {
      "status": "up",
      "duration": "5ms"
    },
    "cache": {
      "status": "down",
      "error": "connection timeout",
      "duration": "5001ms"
    }
  }
}
```

#### FR-PT-003: Startup Probe

**Requirement**: Kubernetes startup probe endpoint

**Priority**: P1 - High

**Description**: HTTP endpoint that indicates if the application has started successfully. Disables liveness checks during slow startup.

**Kubernetes Behavior**:
- Startup failure → Container restart
- Disables liveness during startup
- For slow-starting containers
- One-time check (becomes NOP after success)

**Acceptance Criteria**:
1. [ ] /startupz endpoint (configurable path)
2. [ ] Returns 200 when started
3. [ ] Returns 503 during startup
4. [ ] Disables liveness during startup period
5. [ ] Configurable success threshold
6. [ ] Startup duration tracking
7. [ ] Integration with readiness

#### FR-PT-004: Custom Probe Endpoints

**Requirement**: User-defined probe endpoints

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Register custom probe paths
2. [ ] Configure which checks run per endpoint
3. [ ] Custom response formatting
4. [ ] Multiple custom endpoints

### 4.3 Built-in Checks (FR-BC)

#### FR-BC-001: Database Check

**Requirement**: Verify database connectivity and performance

**Priority**: P1 - High

**Description**: Check database health by verifying connection, optionally running a test query, and measuring response time.

**Supported Databases**:
- PostgreSQL (pgx, lib/pq)
- MySQL (go-sql-driver/mysql)
- SQLite (modernc/sqlite, mattn/go-sqlite3)
- MongoDB (mongo-driver)
- Redis (go-redis, redigo)

**Acceptance Criteria**:
1. [ ] Ping verification (connection alive)
2. [ ] Optional test query execution
3. [ ] Connection pool stats (active, idle, wait)
4. [ ] Query latency measurement
5. [ ] Connection count limits check
6. [ ] Database-specific error detection

**API Specification**:
```go
func NewSQLCheck(db *sql.DB, opts ...SQLCheckOption) Check
func NewPostgresCheck(conn string, opts ...SQLCheckOption) Check
func MySQLCheck(conn string, opts ...SQLCheckOption) Check
func RedisCheck(client *redis.Client, opts ...RedisCheckOption) Check
```

**Configuration Options**:
```go
WithQuery("SELECT 1")           // Custom test query
WithTimeout(5 * time.Second)    // Query timeout
WithMaxLatency(100 * time.Millisecond) // Alert threshold
WithPoolThreshold(0.8)          // Connection pool utilization threshold
```

#### FR-BC-002: HTTP Check

**Requirement**: Verify external HTTP endpoints

**Priority**: P1 - High

**Description**: Check external HTTP/HTTPS endpoints for availability, response time, and expected response content.

**Acceptance Criteria**:
1. [ ] GET/POST/HEAD request support
2. [ ] Status code validation (range or specific)
3. [ ] Response time measurement
4. [ ] Response body content check (optional)
5. [ ] TLS certificate validation
6. [ ] Follow redirects (configurable)
7. [ ] Custom headers support

**API Specification**:
```go
func NewHTTPCheck(url string, opts ...HTTPCheckOption) Check

WithMethod("POST")
WithExpectedStatus(200)
WithTimeout(5 * time.Second)
WithHeader("Authorization", "Bearer token")
WithTLSVerify(true)
```

#### FR-BC-003: System Checks

**Requirement**: Monitor system resources

**Priority**: P2 - Medium

**Description**: Check system resource utilization to prevent resource exhaustion issues.

**Checks**:

| Resource | Metric | Threshold Type |
|----------|--------|----------------|
| Disk | Available space | Minimum bytes/% |
| Memory | Used/Total | Maximum % |
| CPU | Load average | Maximum value |
| Goroutines | Count | Maximum count |
| File descriptors | Open count | Maximum count |
| Inodes | Available | Minimum count |

**Acceptance Criteria**:
1. [ ] Disk space check (configurable threshold)
2. [ ] Memory usage check
3. [ ] CPU load check (1/5/15 min averages)
4. [ ] Goroutine count check
5. [ ] File descriptor count check
6. [ ] Inode availability check

#### FR-BC-004: Custom Check Interface

**Requirement**: Allow users to define custom health checks

**Priority**: P1 - High

**API Specification**:
```go
// Check is the interface for health checks
type Check interface {
    // Name returns the check name
    Name() string
    
    // Execute runs the health check
    Execute(ctx context.Context) error
    
    // Timeout returns the check timeout
    Timeout() time.Duration
}

// CheckFunc adapter for function-based checks
type CheckFunc func(ctx context.Context) error

func (f CheckFunc) Execute(ctx context.Context) error { return f(ctx) }
```

**Acceptance Criteria**:
1. [ ] Simple interface for custom checks
2. [ ] Context support for cancellation/timeout
3. [ ] Error return for failure indication
4. [ ] Check function adapter for convenience
5. [ ] Async check support for long operations

### 4.4 Check Features (FR-CF)

#### FR-CF-001: Check Caching

**Requirement**: Cache check results to prevent thundering herd

**Priority**: P1 - High

**Acceptance Criteria**:
1. [ ] Configurable cache duration per check
2. [ ] Cache invalidation
3. [ ] Stale-while-revalidate pattern
4. [ ] Cache hit/miss metrics

#### FR-CF-002: Check Timeouts

**Requirement**: Prevent hanging health checks

**Priority**: P0 - Critical

**Acceptance Criteria**:
1. [ ] Per-check timeout configuration
2. [ ] Global default timeout
3. [ ] Timeout error as check failure
4. [ ] Proper context cancellation

#### FR-CF-003: Check Retries

**Requirement**: Retry transient failures

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Configurable retry count
2. [ ] Exponential backoff
3. [ ] Jitter support
4. [ ] Retry-specific error detection

#### FR-CF-004: Check Dependencies

**Requirement**: Define check execution order

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Dependency graph definition
2. [ ] Topological ordering
3. [ ] Circular dependency detection
4. [ ] Skip dependents on parent failure

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### 5.1.1 Response Time Targets

| Operation | p50 | p99 | Max |
|-----------|-----|-----|-----|
| Liveness probe | <1ms | <5ms | <10ms |
| Simple check (ping) | <1ms | <5ms | <10ms |
| Database check | <5ms | <20ms | <50ms |
| All checks (10 parallel) | <5ms | <20ms | <50ms |
| Readiness endpoint | <10ms | <50ms | <100ms |

#### 5.1.2 Resource Usage

| Resource | Baseline | 100 Checks | 1000 Checks |
|----------|----------|------------|-------------|
| Memory | 2 MB | 10 MB | 50 MB |
| CPU (idle) | 0.1% | 1% | 5% |
| Goroutines | 5 | 105 | 1005 |
| Cache overhead | 100KB | 1MB | 10MB |

#### 5.1.3 Scalability

- Support 1000+ registered checks
- Handle 1000+ concurrent probe requests
- Minimal memory growth with check count

### 5.2 Reliability

#### 5.2.1 Availability

- Health checker itself must not fail
- Graceful handling of panics in checks
- Automatic recovery from check failures

#### 5.2.2 Data Consistency

- Check results consistent during concurrent access
- Status transitions atomic
- No race conditions in check execution

### 5.3 Security

#### 5.3.1 Endpoint Security

- No sensitive data in health responses
- Optional authentication for health endpoints
- CORS configuration support
- Request logging (configurable)

#### 5.3.2 Check Isolation

- Check execution isolated (panics caught)
- No resource leakage from checks
- Timeout enforcement prevents DoS

### 5.4 Observability

#### 5.3.1 Metrics

| Metric | Type | Labels |
|--------|------|--------|
| health_check_duration | Histogram | check_name, status |
| health_check_total | Counter | check_name, status |
| health_status | Gauge | probe_type |
| health_cache_hit | Counter | check_name |

#### 5.3.2 Logging

- Check execution at DEBUG level
- Status changes at INFO level
- Check failures at WARN level
- Errors at ERROR level

---

## 6. User Stories

### 6.1 Primary User Stories

#### US-001: Kubernetes Deployment

**As a** DevOps engineer  
**I want** Kubernetes-compatible health probes  
**So that** K8s can manage my application lifecycle

**Acceptance Criteria**:
- Given health endpoints configured
- When K8s calls /healthz (liveness)
- Then it returns 200 for healthy
- And 503 for unhealthy
- And restarts container on repeated liveness failure

**Priority**: P0

#### US-002: Dependency Health

**As a** backend engineer  
**I want** to check database and cache health  
**So that** I know when my service is ready

**Acceptance Criteria**:
- Given database and cache registered
- When readiness probe is called
- Then it checks both connections
- And reports status for each
- And returns 503 if any critical check fails

**Priority**: P0

#### US-003: Custom Health Logic

**As a** backend engineer  
**I want** to add custom health checks  
**So that** I can verify application-specific requirements

**Acceptance Criteria**:
- Given a custom check function
- When registered with the checker
- Then it's included in health evaluation
- And results appear in status output
- And I can see custom error messages

**Priority**: P1

#### US-004: Graceful Shutdown

**As a** platform engineer  
**I want** readiness to fail during shutdown  
**So that** K8s stops sending traffic before termination

**Acceptance Criteria**:
- Given shutdown initiated
- When readiness probe is called
- Then it returns 503
- And indicates "shutting down" status
- Until shutdown completes

**Priority**: P1

### 6.2 Secondary User Stories

#### US-005: Slow Startup

**As a** backend engineer  
**I want** startup probe support  
**So that** my slow-starting app doesn't get restarted

**Priority**: P1

#### US-006: Health Debugging

**As an** SRE  
**I want** detailed health status  
**So that** I can debug during incidents

**Priority**: P2

---

## 7. Feature Specifications

### 7.1 HTTP Handler API

```go
// Handler creates an HTTP handler for health endpoints
func Handler(checker *Checker, opts ...HandlerOption) http.Handler

// Handler options
func WithLivenessPath(path string) HandlerOption
func WithReadinessPath(path string) HandlerOption
func WithStartupPath(path string) HandlerOption
func WithStatusFormatter(f StatusFormatter) HandlerOption

// Usage
mux.Handle("/health/", health.Handler(checker))
```

### 7.2 Status Formatter

```go
// StatusFormatter formats the health status for HTTP response
type StatusFormatter interface {
    Format(status *Status) ([]byte, error)
    ContentType() string
}

// Built-in formatters
var JSONFormatter StatusFormatter = &jsonFormatter{}
var PlainTextFormatter StatusFormatter = &plainTextFormatter{}
```

---

## 8. Success Metrics

### 8.1 Adoption Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| pkg.go.dev downloads | 10K | 6 months |
| K8s deployments | 100+ | 12 months |
| Contributing organizations | 15 | 12 months |
| Production users surveyed | 20 | 12 months |

### 8.2 Quality Metrics

| Metric | Target |
|--------|--------|
| Test coverage | >95% |
| Probe response time p99 | <10ms |
| Race detector clean | Yes |
| Documentation coverage | >95% |

### 8.3 Operational Metrics

| Metric | Target |
|--------|--------|
| False positive rate | <1% |
| Mean time to detect unhealthy | <5s |
| Incident correlation accuracy | >90% |

---

## 9. Release Criteria

### 9.1 MVP (v0.1.0)

- [ ] Core Checker API
- [ ] Liveness endpoint (/healthz)
- [ ] Readiness endpoint (/readyz)
- [ ] Database health check
- [ ] HTTP handler
- [ ] Basic documentation

### 9.2 Beta (v0.5.0)

- [ ] Startup probe support
- [ ] Multiple built-in checks
- [ ] Check caching
- [ ] Parallel execution
- [ ] Complete documentation

### 9.3 Production (v1.0.0)

- [ ] All probe types
- [ ] All built-in checks
- [ ] Custom check interface
- [ ] Metrics integration
- [ ] Production runbook
- [ ] Security review

---

## 10. Implementation Details

### 10.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HTTP Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  /healthz    │  │  /readyz      │  │  /startupz   │         │
│  │  Liveness    │  │  Readiness    │  │  Startup     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Health Checker                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Check Registry (name -> Check mapping)                │  │
│  │  - Thread-safe registration/deregistration             │  │
│  │  - Check configuration storage                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Check Executor                                        │  │
│  │  - Parallel execution with goroutines                  │  │
│  │  - Timeout enforcement                                 │  │
│  │  - Dependency ordering                                 │  │
│  │  - Result caching                                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Status Aggregator                                     │  │
│  │  - Strategy application (strict, majority, etc.)       │  │
│  │  - Status calculation                                  │  │
│  │  - Result formatting                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Individual Checks                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Database    │  │  HTTP        │  │  System      │         │
│  │  Check       │  │  Check       │  │  Check       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Interface-based checks | Flexibility, testability | Slightly more complex than functions |
| Parallel execution | Performance | Resource usage |
| Caching | Prevent overload | Stale data risk |
| K8s-first design | Primary use case | Less flexibility for other platforms |
| Panic recovery in checks | System stability | Silent failures possible |

---

## 11. Testing Strategy

### 11.1 Test Categories

| Category | Coverage | Focus |
|----------|----------|-------|
| Unit | 90% | Check execution, aggregation |
| Integration | 80% | HTTP handlers, real DB checks |
| K8s | 60% | Probe behavior simulation |
| Performance | N/A | Response time benchmarks |

### 11.2 Kubernetes Testing

- Minikube integration tests
- Kind (Kubernetes in Docker) tests
- Probe behavior verification
- Rolling update scenarios

---

## 12. Deployment and Operations

### 12.1 K8s Configuration Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-app:latest
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

### 12.2 Operational Runbook

**Pod restarting loop**:
1. Check liveness probe configuration
2. Verify liveness check logic isn't flaky
3. Check application logs for panics
4. Adjust failure threshold if needed

**Traffic to unhealthy pods**:
1. Check readiness probe configuration
2. Verify readiness includes all dependencies
3. Check dependency health independently
4. Look for readiness check timeout issues

---

## 13. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Misconfigured probes | High | Medium | Clear documentation, examples |
| Thundering herd | Medium | Low | Check caching, jitter |
| Check timeouts | Medium | Medium | Default timeouts, context usage |
| Panic in check | High | Low | Panic recovery wrapper |

---

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| **Liveness** | Is the application running? |
| **Readiness** | Is the application ready for traffic? |
| **Startup** | Has the application started? |
| **Probe** | Kubernetes health check mechanism |
| **Check** | Individual health verification |

### 14.2 Kubernetes Probe Comparison

| Aspect | Liveness | Readiness | Startup |
|--------|----------|-----------|---------|
| Failure action | Restart | Remove from service | Restart |
| Use during startup | Yes | No | Exclusive |
| Can fluctuate | Yes | Yes | No |
| Check complexity | Simple | Complex | Medium |
| Typical period | 10s | 5s | 10s |

---

*End of Health PRD v1.0.0*
