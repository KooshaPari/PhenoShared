# CloudProvider Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the CloudProvider abstraction layer for BytePort's multi-cloud deployment system.

## Project Structure

```
lib/cloud/
├── types.go                    # Core data structures
├── interfaces.go               # CloudProvider and capability interfaces
├── errors.go                   # Error types and retry logic
├── registry.go                 # Provider registry implementation
├── example_provider.go         # Template for new providers
├── example_test.go            # Test templates and mock provider
├── DESIGN.md                  # Comprehensive design specification
├── README.md                  # User documentation
├── IMPLEMENTATION_GUIDE.md    # This file
├── examples/                  # YAML configuration examples
│   ├── simple-deployment.yaml
│   ├── multi-cloud-deployment.yaml
│   └── environment-overrides.yaml
└── providers/                 # Provider implementations (to be created)
    ├── aws/
    │   ├── provider.go
    │   ├── ec2.go
    │   ├── rds.go
    │   └── provider_test.go
    ├── vercel/
    │   ├── provider.go
    │   └── provider_test.go
    ├── render/
    ├── supabase/
    ├── fly/
    ├── neon/
    └── planetscale/
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2) ✅ COMPLETE

**Deliverables:**
- ✅ Core interface definitions (interfaces.go)
- ✅ Type system (types.go)
- ✅ Error taxonomy (errors.go)
- ✅ Provider registry (registry.go)
- ✅ Comprehensive documentation (DESIGN.md, README.md)
- ✅ Example provider template (example_provider.go)
- ✅ Test templates (example_test.go)
- ✅ YAML configuration examples

**Files Created:**
```
lib/cloud/types.go              # 600+ lines - Complete type system
lib/cloud/interfaces.go         # 400+ lines - All interfaces
lib/cloud/errors.go            # 300+ lines - Error handling
lib/cloud/registry.go          # 200+ lines - Provider registry
lib/cloud/example_provider.go  # 250+ lines - Implementation template
lib/cloud/example_test.go      # 400+ lines - Test suite
lib/cloud/DESIGN.md            # 8000+ lines - Architecture spec
lib/cloud/README.md            # 4000+ lines - User guide
```

### Phase 2: AWS Provider Wrapper (Week 3-4)

**Goal:** Wrap existing AWS code in CloudProvider interface without breaking changes.

**Steps:**

1. **Create AWS Provider Directory**
   ```bash
   mkdir -p lib/cloud/providers/aws
   ```

2. **Implement AWS Provider**
   ```go
   // lib/cloud/providers/aws/provider.go
   package aws

   import (
       "context"
       "github.com/aws/aws-sdk-go-v2/config"
       "github.com/aws/aws-sdk-go-v2/service/ec2"
       "github.com/aws/aws-sdk-go-v2/service/rds"
       "github.com/byteport/api/lib/cloud"
   )

   type AWSProvider struct {
       ec2Client *ec2.Client
       rdsClient *rds.Client
       cfg       aws.Config
   }

   func NewAWSProvider(credentials cloud.Credentials) (cloud.CloudProvider, error) {
       // Initialize AWS SDK
       cfg, err := config.LoadDefaultConfig(context.Background())
       if err != nil {
           return nil, err
       }

       return &AWSProvider{
           ec2Client: ec2.NewFromConfig(cfg),
           rdsClient: rds.NewFromConfig(cfg),
           cfg:       cfg,
       }, nil
   }

   func (p *AWSProvider) GetMetadata() cloud.ProviderMetadata {
       return cloud.ProviderMetadata{
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
           // ... AWS regions
       }
   }

   // Implement remaining CloudProvider methods...
   ```

3. **Wrap Existing Functionality**
   ```go
   // lib/cloud/providers/aws/ec2.go
   func (p *AWSProvider) createEC2Instance(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
       // Call existing BytePort EC2 launch code
       // Convert to cloud.Resource
       instance := launchExistingEC2Instance(config.Spec)

       return &cloud.Resource{
           ID:       *instance.InstanceId,
           Name:     config.Name,
           Type:     cloud.ResourceTypeComputeVM,
           Provider: "aws",
           // ... populate from AWS instance
       }, nil
   }
   ```

4. **Register Provider**
   ```go
   func init() {
       cloud.MustRegister(
           cloud.ProviderMetadata{ /* ... */ },
           NewAWSProvider,
       )
   }
   ```

5. **Write Tests**
   ```go
   // lib/cloud/providers/aws/provider_test.go
   func TestAWSProvider_CreateResource(t *testing.T) {
       // Use mocked AWS SDK clients
       provider := setupMockAWSProvider()

       resource, err := provider.CreateResource(ctx, config)
       assert.NoError(t, err)
       assert.Equal(t, "aws", resource.Provider)
   }
   ```

**Success Criteria:**
- [ ] All existing AWS functionality accessible through CloudProvider interface
- [ ] No breaking changes to current BytePort code
- [ ] 80%+ test coverage
- [ ] All AWS regions supported
- [ ] Documentation updated

### Phase 3: Serverless Providers (Week 5-6)

**Goal:** Implement Vercel and Render providers for serverless/container deployments.

**Vercel Provider Tasks:**

1. **Create Vercel Client**
   ```go
   // lib/cloud/providers/vercel/client.go
   type VercelClient struct {
       token   string
       baseURL string
   }

   func (c *VercelClient) DeployFunction(ctx context.Context, spec FunctionSpec) (*Deployment, error) {
       // Call Vercel API
   }
   ```

2. **Implement Provider**
   ```go
   // lib/cloud/providers/vercel/provider.go
   func (p *VercelProvider) CreateResource(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
       switch config.Type {
       case cloud.ResourceTypeComputeEdge:
           return p.createEdgeFunction(ctx, config)
       case cloud.ResourceTypeComputeFunction:
           return p.createServerlessFunction(ctx, config)
       default:
           return nil, cloud.NewNotSupportedError("vercel", string(config.Type))
       }
   }
   ```

3. **Handle Edge-Specific Features**
   ```go
   type EdgeFunctionSpec struct {
       Runtime   string   `json:"runtime"`
       Entry     string   `json:"entry"`
       Regions   []string `json:"regions"`
       MemoryMB  int      `json:"memory_mb"`
   }

   func (p *VercelProvider) createEdgeFunction(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
       // Parse spec
       var spec EdgeFunctionSpec
       if err := parseSpec(config.Spec, &spec); err != nil {
           return nil, err
       }

       // Deploy via Vercel API
       deployment, err := p.client.DeployEdgeFunction(ctx, spec)
       // ...
   }
   ```

**Render Provider Tasks:**

1. **Implement Container Deployment**
   ```go
   // lib/cloud/providers/render/provider.go
   func (p *RenderProvider) createWebService(ctx context.Context, config cloud.ResourceConfig) (*cloud.Resource, error) {
       // Parse Docker configuration
       // Call Render API to create service
       // Monitor deployment status
       // Return resource
   }
   ```

2. **Implement Auto-Scaling**
   ```go
   func (p *RenderProvider) SetScale(ctx context.Context, resourceID string, config cloud.ScaleConfig) error {
       // Call Render API to update scaling configuration
       return p.client.UpdateServiceScale(ctx, resourceID, config)
   }
   ```

**Success Criteria:**
- [ ] Vercel provider supports edge and serverless functions
- [ ] Render provider supports containers
- [ ] Auto-scaling works correctly
- [ ] Health checks trigger rollbacks
- [ ] Integration tests pass with real APIs

### Phase 4: Database Providers (Week 7-8)

**Goal:** Implement Supabase, Neon, and PlanetScale database providers.

**Supabase Provider Tasks:**

1. **Implement DatabaseProvider Interface**
   ```go
   // lib/cloud/providers/supabase/provider.go
   type SupabaseProvider struct {
       cloud.CloudProvider
       apiKey    string
       projectID string
   }

   func (p *SupabaseProvider) GetConnectionString(ctx context.Context, resourceID string) (string, error) {
       project, err := p.client.GetProject(ctx, p.projectID)
       if err != nil {
           return "", err
       }
       return project.ConnectionString, nil
   }

   func (p *SupabaseProvider) ExecuteMigration(ctx context.Context, resourceID string, migration cloud.Migration) error {
       // Execute SQL migration via Supabase API
       return p.client.RunMigration(ctx, migration.SQL)
   }
   ```

2. **Handle Branching (Supabase-Specific)**
   ```go
   type BranchSpec struct {
       BaseBranch string `json:"base_branch"`
       Name       string `json:"name"`
   }

   func (p *SupabaseProvider) CreateBranch(ctx context.Context, resourceID string, spec BranchSpec) (*cloud.Resource, error) {
       // Supabase branching feature
       // This is provider-specific metadata
   }
   ```

**Neon Provider Tasks:**

Similar to Supabase but with Neon-specific features like instant branching.

**PlanetScale Provider Tasks:**

Implement with PlanetScale-specific branching and deployment workflow.

**Success Criteria:**
- [ ] All three database providers functional
- [ ] Connection pooling configured
- [ ] Migrations work correctly
- [ ] Backups can be created and restored
- [ ] Provider-specific features exposed via metadata

### Phase 5: Integration & Testing (Week 9-10)

**Goal:** Comprehensive testing across all providers.

**Tasks:**

1. **Provider Compliance Suite**
   ```go
   // lib/cloud/compliance_test.go
   func TestAllProvidersCompliance(t *testing.T) {
       providers := []struct {
           name     string
           provider cloud.CloudProvider
           skip     []string // Operations to skip
       }{
           {"aws", getAWSProvider(), nil},
           {"vercel", getVercelProvider(), []string{"SSH"}},
           {"render", getRenderProvider(), nil},
           // ... all providers
       }

       for _, tc := range providers {
           t.Run(tc.name, func(t *testing.T) {
               testProviderCompliance(t, tc.provider, tc.skip)
           })
       }
   }
   ```

2. **Cross-Provider Integration**
   ```go
   func TestMultiCloudDeployment(t *testing.T) {
       // Deploy frontend to Vercel
       // Deploy API to Render
       // Deploy database to Supabase
       // Verify all components work together
   }
   ```

3. **Performance Benchmarks**
   ```go
   func BenchmarkProviderCreateResource(b *testing.B) {
       for _, provider := range allProviders {
           b.Run(provider.GetMetadata().Name, func(b *testing.B) {
               for i := 0; i < b.N; i++ {
                   provider.CreateResource(ctx, config)
               }
           })
       }
   }
   ```

4. **Cost Estimation Accuracy**
   ```go
   func TestCostEstimationAccuracy(t *testing.T) {
       // Create resources
       // Get estimates
       // Compare with actual costs after 1 week
       // Assert within 10% accuracy
   }
   ```

**Success Criteria:**
- [ ] All providers pass compliance tests
- [ ] Multi-cloud deployments work end-to-end
- [ ] Performance meets SLAs (p95 < 2s)
- [ ] Cost estimates within 10% of actual
- [ ] 95%+ overall test coverage

### Phase 6: Production Rollout (Week 11-12)

**Goal:** Deploy to production with zero downtime.

**Migration Strategy:**

1. **Feature Flag Setup**
   ```go
   // config/features.go
   type FeatureFlags struct {
       UseCloudProvider     bool
       CloudProviderAllowed map[string]bool
   }

   var flags = FeatureFlags{
       UseCloudProvider: false, // Start disabled
       CloudProviderAllowed: map[string]bool{
           "aws": true, // Only AWS initially
       },
   }
   ```

2. **Parallel Execution**
   ```go
   // Deploy using both old and new code, compare results
   func deployWithValidation(config ResourceConfig) (*Resource, error) {
       // Old path
       oldResource, oldErr := deployOldWay(config)

       if flags.UseCloudProvider {
           // New path
           provider, _ := cloud.GetRegistry().Get(config.Provider, creds)
           newResource, newErr := provider.CreateResource(ctx, config)

           // Compare results
           if !resourcesMatch(oldResource, newResource) {
               log.Warnf("Discrepancy detected: %v", diff(oldResource, newResource))
               metrics.IncrementDiscrepancy()
           }

           // Use new result if flag is fully enabled
           if flags.FullCutover {
               return newResource, newErr
           }
       }

       return oldResource, oldErr
   }
   ```

3. **Gradual Rollout**
   ```
   Week 1: Enable for 5% of deployments (monitoring only)
   Week 2: Enable for 25% of deployments (use results)
   Week 3: Enable for 50% of deployments
   Week 4: Enable for 100% of deployments
   ```

4. **Monitoring Dashboard**
   ```
   Metrics to Track:
   - Provider API latency (p50, p95, p99)
   - Error rates by provider and error category
   - Deployment success rates
   - Rollback frequency
   - Cost estimation accuracy
   - Resource creation time
   ```

**Rollback Plan:**

```go
// If errors spike, instant rollback
if metrics.ErrorRate() > 5.0 {
    flags.UseCloudProvider = false
    log.Error("Rolling back to old deployment system")
    alerts.SendCritical("CloudProvider rollback triggered")
}
```

**Success Criteria:**
- [ ] Zero downtime during migration
- [ ] Error rates < 0.1%
- [ ] Deployment times improved by 20%+
- [ ] All monitoring dashboards operational
- [ ] Documentation complete and reviewed

## Testing Strategy

### 1. Unit Tests

Test each provider in isolation:

```bash
go test ./lib/cloud/providers/aws -v -cover
go test ./lib/cloud/providers/vercel -v -cover
```

### 2. Integration Tests

Test against real provider APIs (requires credentials):

```bash
export AWS_PROFILE=byteport-test
export VERCEL_TOKEN=xxx
export RENDER_API_KEY=xxx

go test ./lib/cloud/... -tags=integration -v
```

### 3. Contract Tests

Ensure providers behave consistently:

```bash
go test ./lib/cloud -run TestProviderCompliance -v
```

### 4. Load Tests

Test at scale:

```bash
go test ./lib/cloud -run BenchmarkProvider -bench=. -benchtime=10s
```

## Common Implementation Patterns

### 1. Parsing Provider-Specific Spec

```go
func parseSpec(spec map[string]any, target interface{}) error {
    data, err := json.Marshal(spec)
    if err != nil {
        return err
    }
    return json.Unmarshal(data, target)
}
```

### 2. Polling for State Changes

```go
func waitForState(ctx context.Context, provider cloud.CloudProvider, resourceID string, desiredState cloud.DeploymentState, timeout time.Duration) error {
    ctx, cancel := context.WithTimeout(ctx, timeout)
    defer cancel()

    ticker := time.NewTicker(5 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            resource, err := provider.GetResource(ctx, resourceID)
            if err != nil {
                return err
            }
            if resource.Status == desiredState {
                return nil
            }
            if resource.Status == cloud.DeploymentStateFailed {
                return fmt.Errorf("resource entered failed state")
            }
        }
    }
}
```

### 3. Automatic Retries

```go
func createResourceWithRetry(ctx context.Context, provider cloud.CloudProvider, config cloud.ResourceConfig) (*cloud.Resource, error) {
    var lastErr error

    for attempt := 0; attempt < cloud.DefaultRetryConfig.MaxRetries; attempt++ {
        resource, err := provider.CreateResource(ctx, config)
        if err == nil {
            return resource, nil
        }

        lastErr = err
        if !cloud.ShouldRetry(err, cloud.DefaultRetryConfig) {
            return nil, err
        }

        backoff := cloud.CalculateBackoff(attempt, cloud.DefaultRetryConfig)
        time.Sleep(backoff)
    }

    return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}
```

## Troubleshooting

### Provider Registration Issues

**Problem:** Provider not found in registry

**Solution:**
```go
// Ensure provider's init() function is called
import _ "github.com/byteport/api/lib/cloud/providers/aws"

// Or explicitly register
cloud.MustRegister(metadata, factory)
```

### Authentication Errors

**Problem:** Invalid credentials error

**Solution:**
```go
// Validate credentials before using
provider, _ := cloud.GetRegistry().Get("aws", credentials)
if err := provider.ValidateCredentials(ctx); err != nil {
    // Handle auth error
    log.Fatalf("Invalid credentials: %v", err)
}
```

### Timeout Issues

**Problem:** Operations timing out

**Solution:**
```go
// Set appropriate context timeouts
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
defer cancel()

resource, err := provider.CreateResource(ctx, config)
```

## Best Practices

1. **Always use context with timeout**
2. **Check provider capabilities before calling optional methods**
3. **Handle all error types explicitly**
4. **Log provider API calls for debugging**
5. **Tag resources for cost tracking**
6. **Use mock providers for unit tests**
7. **Implement health checks for all deployments**
8. **Version all deployments for rollback capability**
9. **Monitor provider API quotas**
10. **Clean up test resources in defer statements**

## Next Steps

1. **Start Phase 2**: Implement AWS provider wrapper
2. **Set up CI/CD**: Automated testing for all providers
3. **Create monitoring**: Dashboards and alerts
4. **Write provider guides**: Documentation for each provider
5. **Performance tuning**: Optimize common operations

## Support and Resources

- **Design Document**: `/lib/cloud/DESIGN.md`
- **User Guide**: `/lib/cloud/README.md`
- **Example Code**: `/lib/cloud/example_provider.go`
- **Test Templates**: `/lib/cloud/example_test.go`
- **YAML Examples**: `/lib/cloud/examples/`
- **Team Slack**: #byteport-cloud-abstraction
- **Weekly Sync**: Thursdays 2pm PT

## Success Metrics

- **Coverage**: 95%+ test coverage across all providers
- **Performance**: p95 latency < 2 seconds
- **Reliability**: 99.9% success rate for deployments
- **Cost Accuracy**: Estimates within 10% of actual
- **Provider Support**: 9+ providers fully functional
- **Zero Downtime**: Seamless migration from AWS-only code
