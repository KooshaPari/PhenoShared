package cloud

import (
	"context"
)

// CloudProvider is the core interface that all cloud providers must implement.
// It provides a unified API for managing resources across different cloud platforms.
//
// Providers should return NotSupportedError for operations they don't support.
// Use GetCapabilities() to check what a provider supports before calling operations.
type CloudProvider interface {
	// GetMetadata returns information about the provider and its capabilities
	GetMetadata() ProviderMetadata

	// SupportsResource checks if the provider supports a specific resource type
	SupportsResource(resourceType ResourceType) bool

	// GetCapabilities returns the list of optional capabilities this provider supports
	GetCapabilities() []Capability

	// Initialize sets up the provider with credentials and validates connectivity
	Initialize(ctx context.Context, credentials Credentials) error

	// ValidateCredentials checks if the provided credentials are valid
	ValidateCredentials(ctx context.Context) error

	// CreateResource creates a new cloud resource based on the configuration
	CreateResource(ctx context.Context, config ResourceConfig) (*Resource, error)

	// GetResource retrieves information about a specific resource
	GetResource(ctx context.Context, id string) (*Resource, error)

	// UpdateResource modifies an existing resource
	UpdateResource(ctx context.Context, id string, config ResourceConfig) (*Resource, error)

	// DeleteResource removes a resource
	DeleteResource(ctx context.Context, id string) error

	// ListResources returns resources matching the filter criteria
	ListResources(ctx context.Context, filter ResourceFilter) ([]*Resource, error)

	// Deploy deploys code or configuration to a resource
	Deploy(ctx context.Context, deployment DeploymentConfig) (*Deployment, error)

	// GetDeploymentStatus retrieves the current status of a deployment
	GetDeploymentStatus(ctx context.Context, id string) (*DeploymentStatus, error)

	// RollbackDeployment reverts a deployment to the previous version
	RollbackDeployment(ctx context.Context, id string) error

	// GetLogs retrieves logs from a resource
	GetLogs(ctx context.Context, resource *Resource, opts LogOptions) (LogStream, error)

	// GetMetrics retrieves performance metrics from a resource
	GetMetrics(ctx context.Context, resource *Resource, opts MetricOptions) ([]Metric, error)

	// EstimateCost estimates the cost of a resource configuration
	EstimateCost(ctx context.Context, config ResourceConfig) (*CostEstimate, error)

	// GetActualCost retrieves the actual incurred cost for a resource
	GetActualCost(ctx context.Context, resource *Resource, timeRange TimeRange) (*Cost, error)
}

// Scalable is an optional interface for resources that support scaling
type Scalable interface {
	// SetScale manually sets the scale configuration
	SetScale(ctx context.Context, resourceID string, config ScaleConfig) error

	// GetScaleConfig retrieves the current scale configuration
	GetScaleConfig(ctx context.Context, resourceID string) (*ScaleConfig, error)

	// AutoScale enables or disables auto-scaling
	AutoScale(ctx context.Context, resourceID string, enabled bool) error
}

// Loggable is an optional interface for resources that support logging
type Loggable interface {
	// StreamLogs provides a real-time stream of logs
	StreamLogs(ctx context.Context, resourceID string, opts LogOptions) (LogStream, error)

	// SetLogLevel changes the logging level
	SetLogLevel(ctx context.Context, resourceID string, level string) error

	// GetLogRetention retrieves log retention settings
	GetLogRetention(ctx context.Context, resourceID string) (int, error)
}

// Executable is an optional interface for resources that support command execution
type Executable interface {
	// Exec executes a command in the resource environment
	Exec(ctx context.Context, resourceID string, command string) (string, error)

	// RunCommand runs a command and streams output
	RunCommand(ctx context.Context, resourceID string, command string) (LogStream, error)

	// GetShell opens an interactive shell (if supported)
	GetShell(ctx context.Context, resourceID string, instanceID string) error
}

// Backupable is an optional interface for resources that support backups
type Backupable interface {
	// CreateBackup creates a new backup
	CreateBackup(ctx context.Context, resourceID string, config BackupConfig) (*Backup, error)

	// RestoreBackup restores from a backup
	RestoreBackup(ctx context.Context, resourceID string, backupID string) error

	// ListBackups lists available backups
	ListBackups(ctx context.Context, resourceID string) ([]*Backup, error)

	// DeleteBackup removes a backup
	DeleteBackup(ctx context.Context, backupID string) error

	// GetBackupConfig retrieves backup configuration
	GetBackupConfig(ctx context.Context, resourceID string) (*BackupConfig, error)

	// SetBackupConfig updates backup configuration
	SetBackupConfig(ctx context.Context, resourceID string, config BackupConfig) error
}

// Monitorable is an optional interface for resources that support monitoring
type Monitorable interface {
	// SetAlert configures an alert for a metric
	SetAlert(ctx context.Context, resourceID string, alert AlertConfig) error

	// ListAlerts lists configured alerts
	ListAlerts(ctx context.Context, resourceID string) ([]AlertConfig, error)

	// DeleteAlert removes an alert
	DeleteAlert(ctx context.Context, alertID string) error

	// GetHealthCheck retrieves health check status
	GetHealthCheck(ctx context.Context, resourceID string) (*HealthCheckStatus, error)
}

// DatabaseProvider is an extended interface for database-specific operations
type DatabaseProvider interface {
	CloudProvider

	// GetConnectionString returns the connection string for a database
	GetConnectionString(ctx context.Context, resourceID string) (string, error)

	// ExecuteMigration runs a database migration
	ExecuteMigration(ctx context.Context, resourceID string, migration Migration) error

	// ListMigrations lists applied migrations
	ListMigrations(ctx context.Context, resourceID string) ([]Migration, error)

	// CreateDatabase creates a database within the resource
	CreateDatabase(ctx context.Context, resourceID string, dbName string) error

	// ListDatabases lists databases within the resource
	ListDatabases(ctx context.Context, resourceID string) ([]string, error)

	// SetConnectionPooling configures connection pooling
	SetConnectionPooling(ctx context.Context, resourceID string, config PoolConfig) error
}

// AlertConfig represents an alert configuration
type AlertConfig struct {
	ID         string            `json:"id"`
	ResourceID string            `json:"resource_id"`
	MetricName string            `json:"metric_name"`
	Condition  string            `json:"condition"` // >, <, >=, <=, ==
	Threshold  float64           `json:"threshold"`
	Duration   int               `json:"duration"` // seconds
	Severity   string            `json:"severity"` // info, warning, critical
	Actions    []AlertAction     `json:"actions"`
	Enabled    bool              `json:"enabled"`
	Metadata   map[string]string `json:"metadata,omitempty"`
}

// AlertAction defines what happens when an alert triggers
type AlertAction struct {
	Type   string            `json:"type"` // email, webhook, sns, pagerduty
	Target string            `json:"target"`
	Config map[string]string `json:"config,omitempty"`
}

// HealthCheckStatus represents the current health check status
type HealthCheckStatus struct {
	Status            HealthStatus `json:"status"`
	LastCheck         string       `json:"last_check"`
	ConsecutivePasses int          `json:"consecutive_passes"`
	ConsecutiveFails  int          `json:"consecutive_fails"`
	Details           string       `json:"details,omitempty"`
}

// Migration represents a database migration
type Migration struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	SQL        string `json:"sql,omitempty"`
	ScriptPath string `json:"script_path,omitempty"`
	Checksum   string `json:"checksum,omitempty"`
	AppliedAt  string `json:"applied_at,omitempty"`
	Status     string `json:"status"` // pending, applied, failed, rolled_back
}

// PoolConfig represents connection pooling configuration
type PoolConfig struct {
	MinConnections    int `json:"min_connections"`
	MaxConnections    int `json:"max_connections"`
	ConnectionTimeout int `json:"connection_timeout"` // seconds
	IdleTimeout       int `json:"idle_timeout"`       // seconds
	MaxLifetime       int `json:"max_lifetime"`       // seconds
}

// ProviderFactory creates instances of CloudProvider
type ProviderFactory func(credentials Credentials) (CloudProvider, error)

// ProviderRegistry manages registered cloud providers
type ProviderRegistry interface {
	// Register adds a provider to the registry
	Register(metadata ProviderMetadata, factory ProviderFactory) error

	// Unregister removes a provider from the registry
	Unregister(providerName string) error

	// Get creates a provider instance with the given credentials
	Get(providerName string, credentials Credentials) (CloudProvider, error)

	// List returns metadata for all registered providers
	List() []ProviderMetadata

	// Supports checks if a provider supports a specific resource type
	Supports(providerName string, resourceType ResourceType) bool

	// GetMetadata retrieves metadata for a specific provider
	GetMetadata(providerName string) (*ProviderMetadata, error)
}

// DeploymentOrchestrator manages multi-provider deployments
type DeploymentOrchestrator interface {
	// DeployProject deploys an entire project across multiple providers
	DeployProject(ctx context.Context, config ProjectConfig) (*ProjectDeployment, error)

	// UpdateProject updates a deployed project
	UpdateProject(ctx context.Context, projectID string, config ProjectConfig) (*ProjectDeployment, error)

	// GetProjectStatus retrieves the status of a project deployment
	GetProjectStatus(ctx context.Context, projectID string) (*ProjectStatus, error)

	// DeleteProject removes all resources for a project
	DeleteProject(ctx context.Context, projectID string) error

	// RollbackProject rolls back all resources to previous versions
	RollbackProject(ctx context.Context, projectID string) error
}

// ProjectConfig represents a multi-resource project configuration
type ProjectConfig struct {
	Name         string                 `json:"name" yaml:"name"`
	Version      string                 `json:"version" yaml:"version"`
	Environment  string                 `json:"environment" yaml:"environment"`
	Region       string                 `json:"region,omitempty" yaml:"region,omitempty"`
	Tags         map[string]string      `json:"tags,omitempty" yaml:"tags,omitempty"`
	Providers    map[string]Credentials `json:"providers" yaml:"providers"`
	Resources    []ResourceConfig       `json:"resources" yaml:"resources"`
	Dependencies []ResourceDependency   `json:"dependencies,omitempty" yaml:"dependencies,omitempty"`
}

// ResourceDependency defines dependencies between resources
type ResourceDependency struct {
	Resource  string   `json:"resource" yaml:"resource"`
	DependsOn []string `json:"depends_on" yaml:"depends_on"`
	WaitFor   string   `json:"wait_for,omitempty" yaml:"wait_for,omitempty"` // state to wait for
}

// ProjectDeployment represents a deployed project
type ProjectDeployment struct {
	ID          string          `json:"id"`
	Name        string          `json:"name"`
	Environment string          `json:"environment"`
	Version     string          `json:"version"`
	Status      DeploymentState `json:"status"`
	Resources   []*Resource     `json:"resources"`
	Deployments []*Deployment   `json:"deployments"`
	StartedAt   string          `json:"started_at"`
	UpdatedAt   string          `json:"updated_at"`
	FinishedAt  *string         `json:"finished_at,omitempty"`
}

// ProjectStatus provides overall project status
type ProjectStatus struct {
	Project      *ProjectDeployment           `json:"project"`
	Health       HealthStatus                 `json:"health"`
	Resources    map[string]*DeploymentStatus `json:"resources"`
	CostEstimate *CostEstimate                `json:"cost_estimate,omitempty"`
	ActualCost   *Cost                        `json:"actual_cost,omitempty"`
}
