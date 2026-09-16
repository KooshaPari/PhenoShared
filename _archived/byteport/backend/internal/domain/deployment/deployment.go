package deployment

import (
	"errors"
	"time"

	"github.com/google/uuid"
)

// Deployment represents the core deployment domain entity
// Contains only business logic, no infrastructure dependencies
type Deployment struct {
	uuid        string
	name        string
	owner       string
	projectUUID *string
	status      Status
	providers   map[string]interface{}
	services    []DeploymentService
	costInfo    *CostInfo
	metadata    map[string]interface{}
	envVars     map[string]string
	buildConfig *BuildConfig
	createdAt   time.Time
	updatedAt   time.Time
	deployedAt  *time.Time
	terminatedAt *time.Time
}

// DeploymentService represents a service within a deployment
type DeploymentService struct {
	Name     string
	Type     string // frontend, backend, database
	Provider string
	Status   string
	URL      string
}

// CostInfo represents cost tracking information
type CostInfo struct {
	Monthly   float64
	Breakdown map[string]float64
}

// BuildConfig represents build configuration
type BuildConfig struct {
	Framework      string
	BuildCommand   string
	StartCommand   string
	InstallCommand string
}

// NewDeployment creates a new deployment with validation
func NewDeployment(name, owner string, projectUUID *string) (*Deployment, error) {
	if name == "" {
		return nil, errors.New("deployment name cannot be empty")
	}
	if owner == "" {
		return nil, errors.New("owner cannot be empty")
	}
	
	now := time.Now().UTC()
	
		return &Deployment{
			uuid:        uuid.New().String(),
			name:        name,
			owner:       owner,
			projectUUID: projectUUID,
			status:      StatusPending,
			providers:   make(map[string]interface{}),
			services:    make([]DeploymentService, 0),
			metadata:    make(map[string]interface{}),
			envVars:     make(map[string]string),
			createdAt:   now,
			updatedAt:   now,
		}, nil
}

// ReconstructDeployment reconstructs a deployment from persistence
// This is used by the infrastructure layer to reconstitute domain entities
func ReconstructDeployment(
	uuid, name, owner string,
	projectUUID *string,
	status Status,
	createdAt, updatedAt time.Time,
	deployedAt, terminatedAt *time.Time,
) *Deployment {
		return &Deployment{
			uuid:         uuid,
			name:         name,
			owner:        owner,
			projectUUID:  projectUUID,
			status:       status,
			providers:    make(map[string]interface{}),
			services:     make([]DeploymentService, 0),
			metadata:     make(map[string]interface{}),
			envVars:      make(map[string]string),
			createdAt:    createdAt,
			updatedAt:    updatedAt,
			deployedAt:   deployedAt,
			terminatedAt: terminatedAt,
		}
}

// UUID returns the deployment UUID
func (d *Deployment) UUID() string {
	return d.uuid
}

// Name returns the deployment name
func (d *Deployment) Name() string {
	return d.name
}

// Owner returns the deployment owner
func (d *Deployment) Owner() string {
	return d.owner
}

// Status returns the current status
func (d *Deployment) Status() Status {
	return d.status
}

// Providers returns the provider configuration
func (d *Deployment) Providers() map[string]interface{} {
	return d.providers
}

// Services returns the list of services
func (d *Deployment) Services() []DeploymentService {
	return d.services
}

// CostInfo returns the cost information
func (d *Deployment) CostInfo() *CostInfo {
	return d.costInfo
}

// CreatedAt returns the creation timestamp
func (d *Deployment) CreatedAt() time.Time {
	return d.createdAt
}

// UpdatedAt returns the last update timestamp
func (d *Deployment) UpdatedAt() time.Time {
	return d.updatedAt
}

// DeployedAt returns the deployment timestamp
func (d *Deployment) DeployedAt() *time.Time {
	return d.deployedAt
}

// TerminatedAt returns the termination timestamp
func (d *Deployment) TerminatedAt() *time.Time {
	return d.terminatedAt
}

// ProjectUUID returns the project UUID
func (d *Deployment) ProjectUUID() *string {
	return d.projectUUID
}

// EnvVars returns the environment variables
func (d *Deployment) EnvVars() map[string]string {
	return d.envVars
}

// BuildConfig returns the build configuration
func (d *Deployment) BuildConfig() *BuildConfig {
	return d.buildConfig
}

// SetStatus updates the deployment status with validation
func (d *Deployment) SetStatus(status Status) error {
	if !d.CanTransitionTo(status) {
		return NewInvalidStatusTransitionError(d.status, status)
	}
	
	d.status = status
	d.updatedAt = time.Now().UTC()
	
	// Set special timestamps
	if status == StatusDeployed {
		now := time.Now().UTC()
		d.deployedAt = &now
	} else if status == StatusTerminated {
		now := time.Now().UTC()
		d.terminatedAt = &now
	}
	
	return nil
}

// CanTransitionTo checks if status transition is valid
func (d *Deployment) CanTransitionTo(newStatus Status) bool {
	validTransitions := map[Status][]Status{
		StatusPending:      {StatusDetecting, StatusFailed, StatusTerminated},
		StatusDetecting:    {StatusProvisioning, StatusFailed, StatusTerminated},
		StatusProvisioning: {StatusDeploying, StatusFailed, StatusTerminated},
		StatusDeploying:    {StatusDeployed, StatusFailed, StatusTerminated},
		StatusDeployed:     {StatusDeploying, StatusTerminated}, // Allow redeployment
		StatusFailed:       {StatusDeploying, StatusTerminated}, // Allow retry
		StatusTerminated:   {}, // Terminal state
	}
	
	allowed := validTransitions[d.status]
	for _, s := range allowed {
		if s == newStatus {
			return true
		}
	}
	
	return false
}

// AddService adds a new service to the deployment
func (d *Deployment) AddService(service DeploymentService) error {
	if service.Name == "" {
		return errors.New("service name cannot be empty")
	}
	if service.Type == "" {
		return errors.New("service type cannot be empty")
	}
	if service.Provider == "" {
		return errors.New("service provider cannot be empty")
	}
	
	// Check for duplicate service names
	for _, existing := range d.services {
		if existing.Name == service.Name {
			return errors.New("service with this name already exists")
		}
	}
	
	d.services = append(d.services, service)
	d.updatedAt = time.Now().UTC()
	
	return nil
}

// RemoveService removes a service from the deployment
func (d *Deployment) RemoveService(serviceName string) error {
	for i, service := range d.services {
		if service.Name == serviceName {
			d.services = append(d.services[:i], d.services[i+1:]...)
			d.updatedAt = time.Now().UTC()
			return nil
		}
	}
	
	return errors.New("service not found")
}

// SetProvider sets provider configuration
func (d *Deployment) SetProvider(provider string, config interface{}) {
	d.providers[provider] = config
	d.updatedAt = time.Now().UTC()
}

// SetEnvVar sets an environment variable
func (d *Deployment) SetEnvVar(key, value string) {
	if d.envVars == nil {
		d.envVars = make(map[string]string)
	}
	d.envVars[key] = value
	d.updatedAt = time.Now().UTC()
}

// SetCostInfo updates cost information
func (d *Deployment) SetCostInfo(costInfo *CostInfo) {
	d.costInfo = costInfo
	d.updatedAt = time.Now().UTC()
}

// SetBuildConfig sets build configuration
func (d *Deployment) SetBuildConfig(config *BuildConfig) {
	d.buildConfig = config
	d.updatedAt = time.Now().UTC()
}

// IsActive checks if deployment is in an active state
func (d *Deployment) IsActive() bool {
	return d.status == StatusDeploying || d.status == StatusDeployed
}

// IsFailed checks if deployment has failed
func (d *Deployment) IsFailed() bool {
	return d.status == StatusFailed
}

// IsTerminated checks if deployment is terminated
func (d *Deployment) IsTerminated() bool {
	return d.status == StatusTerminated || d.terminatedAt != nil
}

// CalculateTotalCost calculates total cost from breakdown
func (d *Deployment) CalculateTotalCost() float64 {
	if d.costInfo == nil || d.costInfo.Breakdown == nil {
		return 0.0
	}
	
	total := 0.0
	for _, cost := range d.costInfo.Breakdown {
		total += cost
	}
	
	return total
}

// Validate performs comprehensive validation
func (d *Deployment) Validate() error {
	if d.uuid == "" {
		return errors.New("deployment UUID cannot be empty")
	}
	if d.name == "" {
		return errors.New("deployment name cannot be empty")
	}
	if d.owner == "" {
		return errors.New("owner cannot be empty")
	}
	if !d.status.IsValid() {
		return errors.New("invalid deployment status")
	}
	
	return nil
}
