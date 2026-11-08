# SPEC: Grafana Dashboard Generator

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [API Specification](#api-specification)
5. [Implementation Details](#implementation-details)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Guide](#deployment-guide)
8. [Security Considerations](#security-considerations)
9. [Performance Characteristics](#performance-characteristics)
10. [Operational Guide](#operational-guide)
11. [Dashboard Examples](#dashboard-examples)
12. [Troubleshooting](#troubleshooting)
13. [Appendices](#appendices)

## Overview

### Purpose

This specification defines the Phenotype Grafana Dashboard Generator, a Go-based framework for creating, managing, and deploying Grafana dashboards as code.

### Scope

**In Scope**:
- Dashboard definition in Go
- JSON generation for Grafana
- Multi-environment deployment
- Panel template library
- Dashboard validation

**Out of Scope**:
- Grafana server management
- Data source configuration
- Alert rule management
- User permissions

### Goals

1. **Code-First**: Dashboards defined as version-controlled code
2. **Type Safety**: Go structs prevent invalid configurations
3. **Reusability**: Template library for common patterns
4. **Automation**: CI/CD integration for deployment
5. **Consistency**: Standardized dashboards across environments

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Dashboard Generator                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dashboard  │  │    Panel     │  │   Template   │          │
│  │   Builder    │  │   Library    │  │    Engine    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                    ┌──────┴──────┐                             │
│                    │   Config    │                             │
│                    │   Engine    │                             │
│                    └──────┬──────┘                             │
│                           │                                     │
│                    ┌──────┴──────┐                             │
│                    │   Grafana   │                             │
│                    │    JSON     │                             │
│                    └─────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Component Description

**Dashboard Builder**: Fluent API for constructing dashboards with panels, variables, and configuration.

**Panel Library**: Reusable panel templates for common visualizations (graphs, stats, tables).

**Template Engine**: Environment-specific configuration injection.

**Config Engine**: Environment-based overrides and data source mapping.

## Data Models

### Dashboard Structure

```go
// GrafanaDashboard represents a complete Grafana dashboard
type GrafanaDashboard struct {
    ID              int            `json:"id,omitempty"`
    UID             string         `json:"uid"`
    Title           string         `json:"title"`
    Tags            []string       `json:"tags"`
    Timezone        string         `json:"timezone,omitempty"`
    SchemaVersion   int            `json:"schemaVersion"`
    Version         int            `json:"version"`
    Refresh         string         `json:"refresh,omitempty"`
    Time            TimeSettings   `json:"time"`
    Timepicker      Timepicker     `json:"timepicker"`
    Templating      Templating     `json:"templating,omitempty"`
    Annotations     Annotations    `json:"annotations,omitempty"`
    Panels          []Panel        `json:"panels"`
}

// TimeSettings defines default time range
type TimeSettings struct {
    From string `json:"from"`
    To   string `json:"to"`
}

// Timepicker configuration
type Timepicker struct {
    RefreshIntervals []string `json:"refresh_intervals"`
    TimeOptions      []string `json:"time_options"`
}
```

### Panel Structure

```go
// Panel represents a dashboard panel
type Panel struct {
    ID          int                    `json:"id"`
    Type        string                 `json:"type"`
    Title       string                 `json:"title"`
    Description string                 `json:"description,omitempty"`
    GridPos     GridPos                `json:"gridPos"`
    Targets     []Target               `json:"targets,omitempty"`
    Options     map[string]interface{} `json:"options,omitempty"`
    FieldConfig FieldConfig            `json:"fieldConfig,omitempty"`
    Datasource  DatasourceRef          `json:"datasource,omitempty"`
}

// GridPos defines panel position and size
type GridPos struct {
    X int `json:"x"`
    Y int `json:"y"`
    W int `json:"w"`
    H int `json:"h"`
}

// Target defines data query
type Target struct {
    Expr         string `json:"expr"`
    LegendFormat string `json:"legendFormat,omitempty"`
    RefID        string `json:"refId"`
    Datasource   DatasourceRef `json:"datasource,omitempty"`
}
```

### Field Configuration

```go
// FieldConfig for panel field settings
type FieldConfig struct {
    Defaults  FieldDefaults   `json:"defaults"`
    Overrides []FieldOverride   `json:"overrides,omitempty"`
}

// FieldDefaults for default field settings
type FieldDefaults struct {
    Unit       string            `json:"unit,omitempty"`
    Min        *float64          `json:"min,omitempty"`
    Max        *float64          `json:"max,omitempty"`
    Decimals   int               `json:"decimals,omitempty"`
    Thresholds ThresholdsConfig  `json:"thresholds,omitempty"`
    Color      ColorConfig       `json:"color,omitempty"`
}
```

## API Specification

### Dashboard Builder Interface

```go
// DashboardBuilder constructs dashboards fluently
type DashboardBuilder interface {
    // WithTag adds a tag to the dashboard
    WithTag(tag string) DashboardBuilder
    
    // WithRefresh sets auto-refresh interval
    WithRefresh(interval string) DashboardBuilder
    
    // WithTimeRange sets default time range
    WithTimeRange(from, to string) DashboardBuilder
    
    // WithPanel adds a panel
    WithPanel(panel Panel) DashboardBuilder
    
    // WithVariable adds a template variable
    WithVariable(v Variable) DashboardBuilder
    
    // Build returns the final dashboard
    Build() GrafanaDashboard
    
    // ToJSON serializes to Grafana JSON
    ToJSON() ([]byte, error)
}
```

### Panel Builder Interface

```go
// PanelBuilder constructs panels fluently
type PanelBuilder interface {
    // Type sets panel type (graph, stat, table, etc.)
    Type(panelType string) PanelBuilder
    
    // Title sets panel title
    Title(title string) PanelBuilder
    
    // Description sets panel description
    Description(desc string) PanelBuilder
    
    // AtPosition sets grid position
    AtPosition(x, y, w, h int) PanelBuilder
    
    // WithTarget adds a query target
    WithTarget(t Target) PanelBuilder
    
    // WithPrometheusTarget adds Prometheus query
    WithPrometheusTarget(expr, legend string) PanelBuilder
    
    // WithUnit sets field unit
    WithUnit(unit string) PanelBuilder
    
    // WithThreshold adds color threshold
    WithThreshold(value float64, color string) PanelBuilder
    
    // Build returns the panel
    Build() Panel
}
```

### Deployer Interface

```go
// Deployer handles dashboard deployment
type Deployer interface {
    // Deploy deploys dashboard to Grafana
    Deploy(ctx context.Context, dashboard GrafanaDashboard) error
    
    // DeployAll deploys multiple dashboards
    DeployAll(ctx context.Context, dashboards []GrafanaDashboard) error
    
    // Undeploy removes dashboard
    Undeploy(ctx context.Context, uid string) error
    
    // Get retrieves deployed dashboard
    Get(ctx context.Context, uid string) (*GrafanaDashboard, error)
    
    // List retrieves all dashboards
    List(ctx context.Context) ([]GrafanaDashboardSummary, error)
}
```

## Implementation Details

### Builder Pattern

```go
// NewDashboard creates a new dashboard builder
func NewDashboard(uid string) DashboardBuilder {
    return &dashboardBuilder{
        dashboard: GrafanaDashboard{
            UID:           uid,
            SchemaVersion: 30,
            Version:       1,
            Tags:          []string{},
            Panels:        []Panel{},
            Time: TimeSettings{
                From: "now-1h",
                To:   "now",
            },
            Timepicker: Timepicker{
                RefreshIntervals: []string{"10s", "30s", "1m", "5m"},
                TimeOptions:      []string{"1h", "6h", "12h", "24h", "7d"},
            },
        },
        nextPanelID: 1,
    }
}

func (b *dashboardBuilder) WithPanel(panel Panel) DashboardBuilder {
    panel.ID = b.nextPanelID
    b.nextPanelID++
    b.dashboard.Panels = append(b.dashboard.Panels, panel)
    return b
}

func (b *dashboardBuilder) Build() GrafanaDashboard {
    return b.dashboard
}
```

### Panel Library

```go
// GraphPanel creates a graph panel builder
func GraphPanel(title string) PanelBuilder {
    return &panelBuilder{
        panel: Panel{
            Type:  "graph",
            Title: title,
            GridPos: GridPos{
                W: 12,
                H: 8,
            },
            Targets: []Target{},
        },
    }
}

// StatPanel creates a stat panel builder
func StatPanel(title string) PanelBuilder {
    return &panelBuilder{
        panel: Panel{
            Type:  "stat",
            Title: title,
            GridPos: GridPos{
                W: 6,
                H: 4,
            },
            Targets: []Target{},
        },
    }
}
```

### Environment Configuration

```go
// EnvironmentConfig holds environment-specific settings
type EnvironmentConfig struct {
    GrafanaURL    string
    DataSources   map[string]DatasourceRef
    AlertContacts []string
    Tags          []string
}

// ApplyConfig applies environment config to dashboard
func (d *GrafanaDashboard) ApplyConfig(cfg EnvironmentConfig) *GrafanaDashboard {
    clone := d.Clone()
    
    // Update data sources
    for i, panel := range clone.Panels {
        for j, target := range panel.Targets {
            if ds, ok := cfg.DataSources[target.Datasource.UID]; ok {
                clone.Panels[i].Targets[j].Datasource = ds
            }
        }
    }
    
    // Add environment tags
    clone.Tags = append(clone.Tags, cfg.Tags...)
    
    return clone
}
```

## Testing Strategy

### Unit Testing

```go
func TestDashboardBuilder(t *testing.T) {
    dashboard := NewDashboard("test-dashboard").
        WithTag("test").
        WithPanel(
            GraphPanel("Request Rate").
                WithPrometheusTarget("rate(http_requests_total[1m])", "{{method}}").
                AtPosition(0, 0, 12, 8).
                Build(),
        ).
        Build()
    
    assert.Equal(t, "test-dashboard", dashboard.UID)
    assert.Contains(t, dashboard.Tags, "test")
    assert.Len(t, dashboard.Panels, 1)
    assert.Equal(t, "Request Rate", dashboard.Panels[0].Title)
}

func TestJSONSerialization(t *testing.T) {
    dashboard := OperationalDashboard()
    
    json, err := json.Marshal(dashboard)
    require.NoError(t, err)
    
    // Validate JSON structure
    var result map[string]interface{}
    err = json.Unmarshal(json, &result)
    require.NoError(t, err)
    
    assert.Equal(t, "phenotype-operational", result["uid"])
}
```

### Integration Testing

```go
func TestDeployer_Deploy(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }
    
    ctx := context.Background()
    client := NewGrafanaClient("http://grafana:3000", "admin:admin")
    
    deployer := NewDeployer(client)
    
    dashboard := OperationalDashboard()
    
    err := deployer.Deploy(ctx, dashboard)
    require.NoError(t, err)
    
    // Verify deployment
    deployed, err := deployer.Get(ctx, dashboard.UID)
    require.NoError(t, err)
    assert.Equal(t, dashboard.Title, deployed.Title)
}
```

## Deployment Guide

### Prerequisites

1. Grafana 9.0+ instance
2. Go 1.21+ runtime
3. Grafana API credentials
4. Data sources configured

### Configuration

```go
// Initialize deployer
client := grafana.NewClient(
    "https://grafana.example.com",
    os.Getenv("GRAFANA_API_KEY"),
)

deployer := dashboards.NewDeployer(client, slog.Default())
```

### Deployment

```go
func main() {
    ctx := context.Background()
    
    // Generate dashboards
    dashboards := []dashboards.GrafanaDashboard{
        dashboards.OperationalDashboard(),
        dashboards.DatabaseDashboard(),
        dashboards.HealthDashboard(),
    }
    
    // Deploy all
    for _, d := range dashboards {
        if err := deployer.Deploy(ctx, d); err != nil {
            log.Fatal(err)
        }
        log.Printf("Deployed: %s", d.Title)
    }
}
```

### CI/CD Integration

```yaml
deploy-dashboards:
  stage: deploy
  script:
    - go run ./cmd/deploy-dashboards --env=$CI_ENVIRONMENT_NAME
  environment:
    name: production
  only:
    - main
```

## Security Considerations

### API Key Management

1. **Storage**: Store API keys in environment variables or secret management
2. **Rotation**: Regular API key rotation
3. **Scope**: Use service account with minimal permissions
4. **Encryption**: Encrypt at rest

### Access Control

1. **Dashboard Permissions**: Set appropriate folder permissions
2. **Data Source Access**: Control data source query access
3. **User Roles**: Align with Grafana RBAC

## Performance Characteristics

### Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Dashboard Generation | 1-10ms | Depends on panel count |
| JSON Serialization | 1-5ms | Dashboard size dependent |
| API Deployment | 100-500ms | Network latency |
| Batch Deployment | 1-5s | 10 dashboards |

## Operational Guide

### Health Checks

```bash
# Verify Grafana connectivity
curl -H "Authorization: Bearer $API_KEY" \
  http://grafana:3000/api/health

# List dashboards
curl -H "Authorization: Bearer $API_KEY" \
  http://grafana:3000/api/search?type=dash-db
```

### Monitoring

**Metrics**:
- Deployment success rate
- API response times
- Dashboard generation time

**Alerting**:
- Deployment failures
- Grafana connectivity issues

## Dashboard Examples

### Operational Dashboard

```go
func OperationalDashboard() GrafanaDashboard {
    return NewDashboard("phenotype-operational").
        WithTag("operational").
        WithTag("phenotype").
        WithRefresh("30s").
        WithTimeRange("now-1h", "now").
        WithPanel(
            GraphPanel("HTTP Request Rate").
                WithPrometheusTarget(
                    "sum(rate(phenotype_http_requests_total[1m])) by (method, path)",
                    "{{method}} {{path}}",
                ).
                AtPosition(0, 0, 12, 8).
                Build(),
        ).
        WithPanel(
            GraphPanel("Error Rate (%)").
                WithPrometheusTarget(
                    "sum(rate(phenotype_http_requests_total{status=~'5..'}[1m])) / sum(rate(phenotype_http_requests_total[1m])) * 100",
                    "Error Rate",
                ).
                AtPosition(12, 0, 12, 8).
                WithThreshold(0, "green").
                WithThreshold(5, "yellow").
                WithThreshold(10, "red").
                Build(),
        ).
        WithPanel(
            GraphPanel("P99 Latency").
                WithPrometheusTarget(
                    "histogram_quantile(0.99, sum(rate(phenotype_http_request_duration_seconds_bucket[1m])) by (le))",
                    "P99",
                ).
                AtPosition(0, 8, 12, 8).
                WithUnit("s").
                Build(),
        ).
        Build()
}
```

### Database Dashboard

```go
func DatabaseDashboard() GrafanaDashboard {
    return NewDashboard("phenotype-database").
        WithTag("database").
        WithTag("phenotype").
        WithRefresh("30s").
        WithPanel(
            GraphPanel("Query Duration (P95)").
                WithPrometheusTarget(
                    "histogram_quantile(0.95, sum(rate(phenotype_db_query_duration_seconds_bucket[1m])) by (le, query_type))",
                    "P95 {{query_type}}",
                ).
                AtPosition(0, 0, 12, 8).
                Build(),
        ).
        WithPanel(
            GraphPanel("Active Connections").
                WithPrometheusTarget("db_connections_active", "Active").
                WithPrometheusTarget("db_connections_idle", "Idle").
                AtPosition(12, 0, 12, 8).
                Build(),
        ).
        Build()
}
```

## Troubleshooting

### Deployment Failures

**Invalid JSON**:
- Validate JSON schema
- Check for nil values
- Verify required fields

**Permission Errors**:
- Verify API key permissions
- Check folder access
- Confirm data source permissions

**Network Issues**:
- Test Grafana connectivity
- Check firewall rules
- Verify TLS certificates

## Appendices

### Appendix A: Panel Types

| Type | Description | Use Case |
|------|-------------|----------|
| graph | Time-series graph | Metrics over time |
| stat | Single stat display | Key metrics |
| table | Data table | Structured data |
| gauge | Gauge visualization | Current values |
| logs | Log entries | Log browsing |
| heatmap | Heat map | Distribution |

### Appendix B: Units

| Unit | Description |
|------|-------------|
| percent | Percentage |
| percentunit | Percentage (0-1) |
| seconds | Time duration |
| bytes | Data size |
| bps | Bits per second |
| cps | Count per second |

### Appendix C: Environment Variables

| Variable | Description |
|----------|-------------|
| GRAFANA_URL | Grafana server URL |
| GRAFANA_API_KEY | API authentication key |
| ENVIRONMENT | Target environment |
| DATASOURCE_PROMETHEUS | Prometheus data source UID |

---

*Specification Version: 1.0*
*Last Updated: 2026-04-05*
