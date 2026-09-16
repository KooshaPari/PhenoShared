# CloudProvider Interface Design Specification

## Executive Summary

This document specifies a unified CloudProvider interface that abstracts 9+ cloud providers (AWS, GCP, Azure, Vercel, Render, Supabase, Fly.io, Neon, PlanetScale) into a consistent, language-agnostic API. The design supports both traditional infrastructure (VMs, databases) and modern serverless/edge deployments through a capability-based architecture.

**Key Design Principles:**
- **Capability-Based**: Providers declare what they support rather than forcing full interface implementation
- **Language-Agnostic**: Implementable in Go, Python, TypeScript with consistent semantics
- **Extensible**: New providers can be added without modifying core interfaces
- **Type-Safe**: Strong typing with clear resource hierarchies
- **Production-Ready**: Comprehensive error handling, retry logic, and observability

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│          (BytePort, Deploy-Kit, Custom Apps)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              CloudProvider Interface                        │
│  Common Operations: Deploy, Update, Scale, GetLogs, etc.    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   AWS Provider│  │  GCP Provider │  │Vercel Provider│
│   (EC2, RDS)  │  │ (Compute, SQL)│  │ (Edge, Funcs) │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   AWS APIs    │  │   GCP APIs    │  │  Vercel APIs  │
└───────────────┘  └───────────────┘  └───────────────┘
```

## Resource Type Hierarchy

### Base Resource Types

```yaml
compute:
  vm:           # Traditional VMs (EC2, GCE, Azure VMs)
  container:    # Container services (Render, Fly.io, Cloud Run)
  function:     # Serverless functions (Lambda, Cloud Functions)
  edge:         # Edge computing (Vercel Edge, CF Workers)

database:
  sql:          # Traditional SQL (RDS, Cloud SQL, Azure SQL)
  nosql:        # NoSQL databases (DynamoDB, Firestore)
  serverless:   # Serverless DB (Neon, PlanetScale, Supabase)

storage:
  object:       # Object storage (S3, GCS, Azure Blob)
  block:        # Block storage (EBS, Persistent Disk)
  file:         # File systems (EFS, Filestore)

network:
  loadbalancer: # Load balancers
  cdn:          # Content delivery networks
  dns:          # DNS management
  vpc:          # Virtual private clouds
```

### Capability-Based Extensions

Resources can implement optional capability interfaces:

```go
type Scalable interface {
    SetScale(ctx, resourceID, config) error
    GetScaleConfig(ctx, resourceID) (*ScaleConfig, error)
    AutoScale(ctx, resourceID, enabled) error
}

type Loggable interface {
    StreamLogs(ctx, resourceID, opts) (LogStream, error)
    SetLogLevel(ctx, resourceID, level) error
}

type Executable interface {
    Exec(ctx, resourceID, command) (string, error)
    RunCommand(ctx, resourceID, command) (LogStream, error)
}

type Backupable interface {
    CreateBackup(ctx, resourceID, config) (*Backup, error)
    RestoreBackup(ctx, resourceID, backupID) error
    ListBackups(ctx, resourceID) ([]*Backup, error)
}
```

## Deployment Workflow State Machine

```
┌─────────┐
│ PENDING │ Initial state
└────┬────┘
     │
     ▼
┌────────────┐
│ VALIDATING │ Check credentials, config
└────┬───────┘
     │
     ▼
┌──────────┐
│ BUILDING │ Build container/binary (if applicable)
└────┬─────┘
     │
     ▼
┌──────────────┐
│ PROVISIONING │ Create cloud resources
└──────┬───────┘
       │
       ▼
┌───────────┐
│ DEPLOYING │ Deploy code/configuration
└─────┬─────┘
      │
      ▼
┌──────────────┐
│ HEALTH_CHECK │ Verify deployment health
└──────┬───────┘
       │
       ▼
┌────────┐         ┌──────────┐
│ ACTIVE │◄────────┤ UPDATING │ Successful update
└────┬───┘         └─────┬────┘
     │                   │
     │            ┌──────▼───────┐
     │            │ ROLLING_BACK │ Failed update
     │            └──────┬───────┘
     │                   │
     └───────────────────┘
```

**State Transitions:**
- `PENDING → VALIDATING → BUILDING → PROVISIONING → DEPLOYING → HEALTH_CHECK → ACTIVE`
- `ACTIVE → UPDATING → HEALTH_CHECK → ACTIVE` (successful update)
- `ACTIVE → UPDATING → ROLLING_BACK → ACTIVE` (failed update)
- `ACTIVE → SCALING → ACTIVE` (scale operation)
- Any state → `FAILED` (on critical error)
- Any state → `DELETING → DELETED` (resource removal)

## Configuration Schema

### Project Configuration (YAML)

```yaml
version: "1.0"
environment: production

project:
  name: myapp
  region: us-west-2
  tags:
    team: platform
    cost-center: engineering

# Provider credentials configuration
providers:
  aws:
    auth:
      type: iam
      role_arn: arn:aws:iam::123456789012:role/BytePortDeploy

  vercel:
    auth:
      type: token
      token_env: VERCEL_TOKEN

  supabase:
    auth:
      type: api_key
      key_env: SUPABASE_KEY
      project_id: abcdefghijklmn

# Resource definitions
resources:
  # Container service on Render
  - name: api-server
    type: compute.container
    provider: render
    spec:
      runtime: docker
      dockerfile: ./Dockerfile
      port: 8080
      env:
        DATABASE_URL: ${resources.postgres.connection_string}
        REDIS_URL: ${resources.redis.connection_string}
      scale:
        min: 2
        max: 10
        target_cpu: 70
    deploy:
      strategy: rolling
      health_check:
        type: http
        path: /health
        interval: 30s
        timeout: 5s
        retries: 3
        initial_delay: 10s
        success_threshold: 2
        failure_threshold: 3
      rollback:
        enabled: true
        max_retries: 2

  # Serverless database on Supabase
  - name: postgres
    type: database.serverless
    provider: supabase
    spec:
      engine: postgresql
      version: "15"
      storage: 10GB
      backup:
        enabled: true
        schedule: "0 2 * * *"  # Daily at 2 AM
        retention_days: 30
        point_in_time_recovery: true

  # Edge function on Vercel
  - name: edge-api
    type: compute.edge
    provider: vercel
    spec:
      runtime: nodejs20
      entry: ./src/edge/handler.ts
      regions: [iad1, sfo1, cdg1]
      env:
        API_KEY: ${secrets.edge_api_key}

# Resource dependencies
dependencies:
  - resource: api-server
    depends_on: [postgres, redis]
    wait_for: ACTIVE  # Wait for dependencies to be ACTIVE

  - resource: edge-api
    depends_on: [api-server]
    wait_for: HEALTH_CHECK
```

### Environment-Specific Overrides

```yaml
# environments/dev.yaml
resources:
  - name: api-server
    spec:
      scale:
        min: 1
        max: 2
      instance_type: small

# environments/prod.yaml
resources:
  - name: api-server
    spec:
      scale:
        min: 3
        max: 20
      instance_type: large
      regions: [us-west-2, us-east-1, eu-west-1]
```

## Error Taxonomy

### Error Categories

1. **AuthenticationError** (AUTHENTICATION)
   - **Retryable**: No
   - **Examples**: Invalid API key, expired token, insufficient permissions
   - **Handling**: Prompt for new credentials

2. **QuotaError** (QUOTA)
   - **Retryable**: Yes (with backoff)
   - **Examples**: Rate limit exceeded, max instances reached
   - **Handling**: Wait for reset_time, exponential backoff

3. **ValidationError** (VALIDATION)
   - **Retryable**: No
   - **Examples**: Invalid region, unsupported runtime
   - **Handling**: Fix configuration, re-deploy

4. **ResourceNotFoundError** (NOT_FOUND)
   - **Retryable**: Context-dependent
   - **Examples**: Instance not found, deleted resource
   - **Handling**: Verify resource ID, re-create if needed

5. **ConflictError** (CONFLICT)
   - **Retryable**: No
   - **Examples**: Name already taken, concurrent modification
   - **Handling**: Use different name, retry with latest version

6. **ProvisioningError** (PROVISIONING)
   - **Retryable**: Yes
   - **Examples**: Instance launch failed, deployment timeout
   - **Handling**: Retry with exponential backoff

7. **NetworkError** (NETWORK)
   - **Retryable**: Yes
   - **Examples**: Connection timeout, DNS resolution failed
   - **Handling**: Exponential backoff with jitter

8. **InternalProviderError** (INTERNAL)
   - **Retryable**: Yes
   - **Examples**: AWS 500 errors, service unavailable
   - **Handling**: Retry with exponential backoff

### Retry Strategy

```go
type RetryConfig struct {
    MaxRetries      int           // 5
    InitialDelay    time.Duration // 1 second
    MaxDelay        time.Duration // 16 seconds
    Multiplier      float64       // 2.0 (exponential)
    Jitter          bool          // true (prevent thundering herd)
    RetryableErrors []ErrorCategory
}

// Backoff sequence: 1s, 2s, 4s, 8s, 16s (with jitter)
```

## Provider Registry Pattern

### Registration

```go
// Providers self-register at init time
func init() {
    cloud.MustRegister(
        cloud.ProviderMetadata{
            Name:    "aws",
            Version: "1.0.0",
            SupportedResources: []cloud.ResourceType{
                cloud.ResourceTypeComputeVM,
                cloud.ResourceTypeDatabaseSQL,
                cloud.ResourceTypeStorageObject,
            },
            Capabilities: []cloud.Capability{
                cloud.CapabilityScalable,
                cloud.CapabilityBackupable,
                cloud.CapabilitySSH,
            },
            Regions: awsRegions,
            AuthTypes: []string{"iam", "access_key"},
        },
        NewAWSProvider, // Factory function
    )
}
```

### Usage

```go
// Get registry
registry := cloud.GetRegistry()

// List available providers
providers := registry.List()

// Create provider instance
credentials := cloud.Credentials{
    Type: "iam",
    Data: map[string]string{
        "role_arn": "arn:aws:iam::...",
    },
}

provider, err := registry.Get("aws", credentials)
if err != nil {
    // Handle error
}

// Use provider
resource, err := provider.CreateResource(ctx, config)
```

## Testing Strategy

### 1. Unit Tests

Test individual provider implementations in isolation:

```go
func TestAWSProvider_CreateResource(t *testing.T) {
    // Mock AWS SDK calls
    mockEC2 := &mockEC2Client{}
    provider := &AWSProvider{ec2: mockEC2}

    config := cloud.ResourceConfig{
        Name: "test-instance",
        Type: cloud.ResourceTypeComputeVM,
        Spec: map[string]any{
            "instance_type": "t3.micro",
        },
    }

    resource, err := provider.CreateResource(context.Background(), config)
    assert.NoError(t, err)
    assert.Equal(t, "test-instance", resource.Name)
}
```

### 2. Interface Compliance Tests

Generic test suite that validates all providers:

```go
func TestProviderCompliance(t *testing.T) {
    providers := []struct {
        name     string
        provider cloud.CloudProvider
    }{
        {"aws", newMockAWSProvider()},
        {"gcp", newMockGCPProvider()},
        {"vercel", newMockVercelProvider()},
    }

    for _, tc := range providers {
        t.Run(tc.name, func(t *testing.T) {
            testProviderMetadata(t, tc.provider)
            testResourceOperations(t, tc.provider)
            testErrorHandling(t, tc.provider)
        })
    }
}
```

### 3. Integration Tests

Test against real provider APIs (sandbox accounts):

```go
func TestAWSIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }

    provider := newAWSProvider(realCredentials)

    // Create resource
    resource, err := provider.CreateResource(ctx, config)
    require.NoError(t, err)

    // Verify creation
    fetched, err := provider.GetResource(ctx, resource.ID)
    require.NoError(t, err)
    assert.Equal(t, resource.ID, fetched.ID)

    // Cleanup
    defer provider.DeleteResource(ctx, resource.ID)
}
```

### 4. Mock Provider

For testing without cloud resources:

```go
type MockProvider struct {
    resources map[string]*cloud.Resource
    mu        sync.RWMutex
}

func (m *MockProvider) CreateResource(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
    m.mu.Lock()
    defer m.mu.Unlock()

    resource := &cloud.Resource{
        ID:           uuid.New().String(),
        Name:         config.Name,
        Type:         config.Type,
        Provider:     "mock",
        Status:       cloud.DeploymentStateActive,
        HealthStatus: cloud.HealthStatusHealthy,
        CreatedAt:    time.Now(),
        UpdatedAt:    time.Now(),
    }

    m.resources[resource.ID] = resource
    return resource, nil
}
```

## Migration Path from AWS-Only Code

### Phase 1: Create Abstraction (No Breaking Changes)

```
1. Create lib/cloud/ directory with interfaces
2. Implement AWSProvider that wraps existing AWS code
3. Keep existing direct AWS calls functional
4. Add comprehensive tests
```

```go
// lib/cloud/providers/aws/provider.go
type AWSProvider struct {
    ec2    *ec2.Client
    rds    *rds.Client
    // ... existing AWS clients
}

func (p *AWSProvider) CreateResource(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
    // Wrap existing AWS-specific code
    switch config.Type {
    case cloud.ResourceTypeComputeVM:
        return p.createEC2Instance(ctx, config)
    case cloud.ResourceTypeDatabaseSQL:
        return p.createRDSInstance(ctx, config)
    default:
        return nil, cloud.NewNotSupportedError("aws", string(config.Type))
    }
}

func (p *AWSProvider) createEC2Instance(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
    // Call existing EC2 launch code
    instance, err := p.launchEC2Instance(ctx, config.Spec)
    if err != nil {
        return nil, err
    }

    // Convert to cloud.Resource
    return convertToResource(instance), nil
}
```

### Phase 2: Implement Additional Providers

```
1. Add Vercel, Render, Supabase providers
2. Test in parallel with AWS provider
3. Validate abstraction works for different paradigms
4. No changes to application code yet
```

### Phase 3: Migrate Application Code

```
1. Replace direct AWS calls with CloudProvider interface
2. Use provider registry to select providers
3. Maintain backward compatibility with feature flags
4. Gradual rollout to production
```

**Before:**
```go
// Direct AWS usage
ec2Client := ec2.New(sess)
instance, err := ec2Client.RunInstances(ctx, &ec2.RunInstancesInput{...})
```

**After:**
```go
// Through CloudProvider interface
provider, _ := cloud.GetRegistry().Get("aws", credentials)
resource, err := provider.CreateResource(ctx, config)
```

### Phase 4: Multi-Provider Support

```
1. Enable deployments across multiple providers
2. Add orchestration layer for dependencies
3. Support provider-specific optimizations
4. Full multi-cloud deployment support
```

## Cost Estimation

### Interface

```go
type CostEstimate struct {
    HourlyUSD   float64
    DailyUSD    float64
    MonthlyUSD  float64
    Breakdown   map[string]float64 // component -> cost
    Confidence  string             // high, medium, low
    LastUpdated time.Time
}

// Usage
estimate, err := provider.EstimateCost(ctx, config)
fmt.Printf("Estimated cost: $%.2f/month\n", estimate.MonthlyUSD)
fmt.Printf("Breakdown: %+v\n", estimate.Breakdown)
```

### Provider-Specific Handling

- **AWS**: Use AWS Pricing API
- **Vercel**: Calculate based on function invocations + bandwidth
- **Supabase**: Database size + storage + bandwidth
- **Providers without APIs**: Maintain pricing database, update regularly

## Health Checks and Verification

```yaml
health_check:
  type: http  # http, tcp, command, custom
  path: /health
  port: 8080
  interval: 30s
  timeout: 5s
  retries: 3
  initial_delay: 10s
  success_threshold: 2  # Consecutive successes to mark healthy
  failure_threshold: 3  # Consecutive failures to trigger rollback
```

**Verification Workflow:**
1. Deploy new version
2. Wait `initial_delay`
3. Run health checks every `interval`
4. If `success_threshold` met → Mark healthy
5. If `failure_threshold` met → Trigger rollback
6. Continue monitoring after deployment

## Provider Comparison Matrix

| Feature | AWS | GCP | Azure | Vercel | Render | Supabase | Fly.io | Neon | PlanetScale |
|---------|-----|-----|-------|--------|--------|----------|--------|------|-------------|
| VM Support | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Containers | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Serverless Functions | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Edge Computing | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SQL Database | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Auto-Scaling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SSH Access | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Backups | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Database Branching | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |

## Implementation Roadmap

### Week 1-2: Foundation
- ✅ Design interfaces and types
- ✅ Implement error handling
- ✅ Create provider registry
- ✅ Write comprehensive documentation

### Week 3-4: AWS Provider
- Wrap existing AWS code in CloudProvider interface
- Implement all required methods
- Add unit tests and mocks
- Integration tests with AWS sandbox

### Week 5-6: Serverless Providers
- Implement Vercel provider (edge, functions)
- Implement Render provider (containers)
- Test deployment workflows
- Verify health checks and rollbacks

### Week 7-8: Database Providers
- Implement Supabase provider
- Implement Neon provider
- Implement PlanetScale provider
- Test migration workflows

### Week 9-10: Integration & Testing
- Cross-provider integration tests
- Performance benchmarking
- Cost estimation accuracy testing
- Documentation and examples

### Week 11-12: Production Rollout
- Migrate BytePort to use CloudProvider interface
- Deploy to staging environment
- Monitor and optimize
- Production deployment with feature flags

## Next Steps

1. **Review and Approve Design**: Get stakeholder sign-off on interface design
2. **Set Up Development Environment**: Create repos, CI/CD pipelines
3. **Start Phase 1 Implementation**: Begin with AWS provider wrapper
4. **Parallel Provider Development**: Different team members work on different providers
5. **Integration Testing**: Set up test accounts with all providers
6. **Documentation**: Create provider-specific implementation guides

## Success Criteria

- ✅ Single codebase deploys to 9+ providers
- ✅ Provider additions require no core changes
- ✅ 95%+ test coverage
- ✅ Sub-2s p95 latency for provider operations
- ✅ Zero downtime migrations from AWS-only code
- ✅ Cost estimation within 10% accuracy
- ✅ Comprehensive error handling and retry logic
