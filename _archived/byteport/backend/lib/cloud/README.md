# CloudProvider Abstraction Layer

A unified interface for deploying and managing resources across multiple cloud providers.

## Supported Providers

- **AWS** - EC2, RDS, S3, Lambda
- **GCP** - Compute Engine, Cloud SQL, Cloud Storage, Cloud Functions
- **Azure** - Virtual Machines, Azure SQL, Blob Storage
- **Vercel** - Edge Functions, Serverless Functions
- **Render** - Web Services, Background Workers, Databases
- **Supabase** - PostgreSQL, Authentication, Storage
- **Fly.io** - Container Hosting, PostgreSQL
- **Neon** - Serverless PostgreSQL
- **PlanetScale** - Serverless MySQL

## Quick Start

### Installation

```go
import "github.com/byteport/api/lib/cloud"
```

### Basic Usage

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/byteport/api/lib/cloud"
)

func main() {
    ctx := context.Background()

    // Get a provider from the registry
    credentials := cloud.Credentials{
        Type: "api_key",
        Data: map[string]string{
            "api_key": "your-api-key",
        },
    }

    provider, err := cloud.GetRegistry().Get("vercel", credentials)
    if err != nil {
        log.Fatal(err)
    }

    // Initialize the provider
    if err := provider.Initialize(ctx, credentials); err != nil {
        log.Fatal(err)
    }

    // Create a resource
    config := cloud.ResourceConfig{
        Name:     "my-edge-function",
        Type:     cloud.ResourceTypeComputeEdge,
        Provider: "vercel",
        Region:   "sfo1",
        Spec: map[string]any{
            "runtime": "nodejs20",
            "entry":   "./src/handler.ts",
        },
    }

    resource, err := provider.CreateResource(ctx, config)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Created resource: %s (ID: %s)\n", resource.Name, resource.ID)
}
```

## Project Configuration

Create a `byteport.yaml` file to define your multi-cloud project:

```yaml
version: "1.0"
environment: production

project:
  name: myapp
  region: us-west-2
  tags:
    team: platform

providers:
  vercel:
    auth:
      type: token
      token_env: VERCEL_TOKEN

  supabase:
    auth:
      type: api_key
      key_env: SUPABASE_KEY

resources:
  - name: edge-api
    type: compute.edge
    provider: vercel
    spec:
      runtime: nodejs20
      entry: ./src/edge.ts

  - name: postgres
    type: database.serverless
    provider: supabase
    spec:
      engine: postgresql
      version: "15"
```

Deploy your project:

```bash
byteport deploy -f byteport.yaml
```

## Architecture

### Core Interfaces

1. **CloudProvider** - Base interface all providers implement
2. **Scalable** - Optional interface for auto-scaling support
3. **Loggable** - Optional interface for log streaming
4. **Executable** - Optional interface for command execution
5. **Backupable** - Optional interface for backup/restore
6. **Monitorable** - Optional interface for metrics and alerts

### Resource Types

Resources are categorized by type:

- `compute.vm` - Virtual machines
- `compute.container` - Container services
- `compute.function` - Serverless functions
- `compute.edge` - Edge computing
- `database.sql` - SQL databases
- `database.nosql` - NoSQL databases
- `database.serverless` - Serverless databases
- `storage.object` - Object storage
- `network.loadbalancer` - Load balancers
- `network.cdn` - Content delivery

### Deployment States

Deployments progress through states:

```
PENDING → VALIDATING → BUILDING → PROVISIONING →
DEPLOYING → HEALTH_CHECK → ACTIVE
```

Failed deployments can automatically rollback:

```
ACTIVE → UPDATING → FAILED → ROLLING_BACK → ACTIVE
```

## Provider Implementation

### Creating a New Provider

```go
package myprovider

import (
    "context"
    "github.com/byteport/api/lib/cloud"
)

type MyProvider struct {
    client *MyAPIClient
    credentials cloud.Credentials
}

func NewMyProvider(credentials cloud.Credentials) (cloud.CloudProvider, error) {
    client, err := NewAPIClient(credentials.Data["api_key"])
    if err != nil {
        return nil, err
    }

    return &MyProvider{
        client: client,
        credentials: credentials,
    }, nil
}

// Implement CloudProvider interface methods...

func (p *MyProvider) GetMetadata() cloud.ProviderMetadata {
    return cloud.ProviderMetadata{
        Name:    "myprovider",
        Version: "1.0.0",
        SupportedResources: []cloud.ResourceType{
            cloud.ResourceTypeComputeContainer,
        },
        Capabilities: []cloud.Capability{
            cloud.CapabilityScalable,
            cloud.CapabilityLoggable,
        },
        // ...
    }
}

// Register at init time
func init() {
    cloud.MustRegister(
        cloud.ProviderMetadata{ /* ... */ },
        NewMyProvider,
    )
}
```

## Error Handling

All errors are typed for consistent handling:

```go
resource, err := provider.CreateResource(ctx, config)
if err != nil {
    switch e := err.(type) {
    case *cloud.AuthenticationError:
        // Handle auth errors - not retryable
        log.Fatal("Invalid credentials")

    case *cloud.QuotaError:
        // Handle quota errors - retryable
        time.Sleep(time.Until(e.ResetTime))
        // Retry...

    case *cloud.ValidationError:
        // Handle validation errors - not retryable
        log.Fatalf("Invalid config field: %s", e.Field)

    case *cloud.NetworkError:
        // Handle network errors - retryable
        // Automatic retry with exponential backoff

    default:
        log.Fatal(err)
    }
}
```

### Automatic Retries

Use the built-in retry mechanism:

```go
config := cloud.RetryConfig{
    MaxRetries:   5,
    InitialDelay: 1 * time.Second,
    MaxDelay:     16 * time.Second,
    Multiplier:   2.0,
    Jitter:       true,
}

// Retries are automatic for retryable errors
resource, err := provider.CreateResource(ctx, config)
```

## Capabilities and Feature Detection

Check provider capabilities before calling optional methods:

```go
metadata := provider.GetMetadata()

// Check if provider supports a resource type
if !provider.SupportsResource(cloud.ResourceTypeComputeEdge) {
    log.Fatal("Provider doesn't support edge computing")
}

// Check for specific capability
hasAutoScale := false
for _, cap := range metadata.Capabilities {
    if cap == cloud.CapabilityAutoScale {
        hasAutoScale = true
        break
    }
}

if hasAutoScale {
    // Use auto-scaling features
    scalable := provider.(cloud.Scalable)
    scalable.AutoScale(ctx, resourceID, true)
}
```

## Cost Management

### Estimate Costs

```go
config := cloud.ResourceConfig{
    Name: "api-server",
    Type: cloud.ResourceTypeComputeContainer,
    Spec: map[string]any{
        "instance_type": "medium",
        "instances":     5,
    },
}

estimate, err := provider.EstimateCost(ctx, config)
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Estimated monthly cost: $%.2f\n", estimate.MonthlyUSD)
fmt.Printf("Breakdown:\n")
for component, cost := range estimate.Breakdown {
    fmt.Printf("  %s: $%.2f\n", component, cost)
}
```

### Track Actual Costs

```go
timeRange := cloud.TimeRange{
    Start: time.Now().AddDate(0, -1, 0), // Last month
    End:   time.Now(),
}

cost, err := provider.GetActualCost(ctx, resource, timeRange)
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Actual cost: $%.2f\n", cost.TotalUSD)
```

## Logging and Monitoring

### Stream Logs

```go
opts := cloud.LogOptions{
    Since:  timePtr(time.Now().Add(-1 * time.Hour)),
    Follow: true,
    Filter: "error",
}

logStream, err := provider.GetLogs(ctx, resource, opts)
if err != nil {
    log.Fatal(err)
}
defer logStream.Close()

for {
    entry, err := logStream.Next()
    if err != nil {
        break
    }
    fmt.Printf("[%s] %s: %s\n", entry.Timestamp, entry.Level, entry.Message)
}
```

### Get Metrics

```go
opts := cloud.MetricOptions{
    Since:       timePtr(time.Now().Add(-1 * time.Hour)),
    Granularity: "5m",
    MetricNames: []string{"cpu_usage", "memory_usage", "request_count"},
}

metrics, err := provider.GetMetrics(ctx, resource, opts)
if err != nil {
    log.Fatal(err)
}

for _, metric := range metrics {
    fmt.Printf("%s: %.2f %s at %s\n",
        metric.Name, metric.Value, metric.Unit, metric.Timestamp)
}
```

## Deployment Strategies

### Rolling Deployment

```go
config := cloud.DeploymentConfig{
    ResourceID: resource.ID,
    Version:    "v2.0.0",
    Source: &cloud.DeploymentSource{
        Type:       "git",
        Repository: "https://github.com/myorg/myapp",
        Branch:     "main",
    },
    Strategy: cloud.DeploymentStrategyRolling,
}

deployment, err := provider.Deploy(ctx, config)
```

### Blue-Green Deployment

```go
config.Strategy = cloud.DeploymentStrategyBlueGreen
deployment, err := provider.Deploy(ctx, config)
```

### Canary Deployment

```go
config.Strategy = cloud.DeploymentStrategyCanary
deployment, err := provider.Deploy(ctx, config)
```

## Health Checks

Configure health checks for automatic rollback:

```yaml
deploy:
  strategy: rolling
  health_check:
    type: http
    path: /health
    port: 8080
    interval: 30s
    timeout: 5s
    success_threshold: 2
    failure_threshold: 3
  rollback:
    enabled: true
    max_retries: 2
```

Monitor deployment progress:

```go
for {
    status, err := provider.GetDeploymentStatus(ctx, deployment.ID)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("State: %s, Progress: %d%%\n",
        status.Deployment.State, status.Deployment.Progress)

    if status.Deployment.State == cloud.DeploymentStateActive {
        fmt.Println("Deployment successful!")
        break
    }

    if status.Deployment.State == cloud.DeploymentStateFailed {
        fmt.Printf("Deployment failed: %s\n", status.Deployment.Error.Message)
        break
    }

    time.Sleep(5 * time.Second)
}
```

## Testing

### Unit Tests

Use the mock provider for testing:

```go
func TestMyApp(t *testing.T) {
    provider := &cloud.MockProvider{
        Resources: make(map[string]*cloud.Resource),
    }

    // Test your application logic
    resource, err := createResource(provider, config)
    assert.NoError(t, err)
    assert.Equal(t, "my-resource", resource.Name)
}
```

### Integration Tests

Test against real providers:

```go
func TestAWSIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }

    provider, _ := cloud.GetRegistry().Get("aws", credentials)

    resource, err := provider.CreateResource(ctx, config)
    require.NoError(t, err)
    defer provider.DeleteResource(ctx, resource.ID)

    // Verify resource was created
    fetched, err := provider.GetResource(ctx, resource.ID)
    require.NoError(t, err)
    assert.Equal(t, resource.ID, fetched.ID)
}
```

## Best Practices

1. **Always check capabilities** before using optional features
2. **Use typed errors** for proper error handling
3. **Set appropriate timeouts** on context for long-running operations
4. **Enable health checks** for production deployments
5. **Monitor costs** with regular cost tracking
6. **Test with mock provider** before deploying to real providers
7. **Use retry logic** for transient errors
8. **Tag resources** for organization and cost tracking
9. **Version deployments** for easy rollbacks
10. **Clean up resources** in defer statements for tests

## Examples

See the `examples/` directory for complete working examples:

- `examples/simple/` - Basic resource creation
- `examples/multi-cloud/` - Deploy across multiple providers
- `examples/deployment/` - Advanced deployment strategies
- `examples/monitoring/` - Logging and metrics
- `examples/database/` - Database-specific operations

## Contributing

To add a new cloud provider:

1. Create `providers/{provider}/provider.go`
2. Implement the `CloudProvider` interface
3. Implement optional interfaces (Scalable, Loggable, etc.)
4. Register the provider in `init()`
5. Add comprehensive tests
6. Update documentation

See `DESIGN.md` for detailed architecture and `example_provider.go` for a template.

## License

MIT License - see LICENSE file for details
