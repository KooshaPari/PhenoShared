package models

import (
	"gorm.io/datatypes"
	"time"
)

// Host represents a self-hosted deployment target
type Host struct {
	UUID  string `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"uuid"`
	Owner string `gorm:"type:uuid;not null;index" json:"owner"`
	Name  string `gorm:"type:varchar(255);not null" json:"name"`

	// Host connection information
	HostURL string `gorm:"type:varchar(500);not null" json:"host_url"`
	// URL of the host agent API
	APIKey string `gorm:"type:varchar(255);not null" json:"api_key"`
	// API key for authenticating with host agent

	// Host specifications
	Specs datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"specs"`
	// CPU, RAM, storage, etc.

	// Host status
	Status string `gorm:"type:varchar(50);not null;default:'pending'" json:"status"`
	// Status: pending, online, offline, error
	LastHeartbeat *time.Time `json:"last_heartbeat,omitempty"`
	// Last successful ping from host agent

	// Host capabilities
	Capabilities datatypes.JSON `gorm:"type:jsonb;default:'[]'" json:"capabilities"`
	// Supported features: docker, kubernetes, etc.

	// Host metadata
	Metadata datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata"`
	Region   *string        `gorm:"type:varchar(100)" json:"region,omitempty"`
	// Geographic region or datacenter

	// Resource limits
	MaxDeployments     int `gorm:"default:10" json:"max_deployments"`
	CurrentDeployments int `gorm:"default:0" json:"current_deployments"`

	// Timestamps
	CreatedAt time.Time  `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time  `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt *time.Time `gorm:"index" json:"deleted_at,omitempty"`
}

// HostDeployment maps deployments to hosts
type HostDeployment struct {
	ID             int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	DeploymentUUID string `gorm:"type:uuid;not null;index" json:"deployment_uuid"`
	HostUUID       string `gorm:"type:uuid;not null;index" json:"host_uuid"`

	// Container/service information
	ContainerID *string `gorm:"type:varchar(255)" json:"container_id,omitempty"`
	ServiceName string  `gorm:"type:varchar(255);not null" json:"service_name"`

	// Port mappings
	PortMappings datatypes.JSON `gorm:"type:jsonb;default:'[]'" json:"port_mappings"`
	// Example: [{"host": 8080, "container": 3000}]

	// Environment configuration
	EnvConfig datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"env_config"`

	// Resource allocation
	Resources datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"resources"`
	// CPU, memory limits

	Status string `gorm:"type:varchar(50);not null;default:'pending'" json:"status"`
	// Status: pending, starting, running, stopped, error

	// Health check
	HealthCheckURL  *string    `gorm:"type:varchar(500)" json:"health_check_url,omitempty"`
	LastHealthCheck *time.Time `json:"last_health_check,omitempty"`
	HealthStatus    *string    `gorm:"type:varchar(50)" json:"health_status,omitempty"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`
}

// HostMetric stores time-series metrics from hosts
type HostMetric struct {
	ID       int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	HostUUID string `gorm:"type:uuid;not null;index" json:"host_uuid"`

	// CPU metrics
	CPUUsage *float64 `gorm:"type:decimal(5,2)" json:"cpu_usage,omitempty"`
	CPUCores *int     `json:"cpu_cores,omitempty"`

	// Memory metrics
	MemoryUsed  *int64 `json:"memory_used,omitempty"`
	MemoryTotal *int64 `json:"memory_total,omitempty"`

	// Storage metrics
	StorageUsed  *int64 `json:"storage_used,omitempty"`
	StorageTotal *int64 `json:"storage_total,omitempty"`

	// Network metrics
	NetworkRx *int64 `json:"network_rx,omitempty"`
	NetworkTx *int64 `json:"network_tx,omitempty"`

	// Additional metrics
	Metrics datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metrics"`

	Timestamp time.Time `gorm:"autoCreateTime;index" json:"timestamp"`
}

// HostLog stores logs from host agents
type HostLog struct {
	ID        int64          `gorm:"primaryKey;autoIncrement" json:"id"`
	HostUUID  string         `gorm:"type:uuid;not null;index" json:"host_uuid"`
	Level     string         `gorm:"type:varchar(20);not null;default:'info'" json:"level"`
	Message   string         `gorm:"type:text;not null" json:"message"`
	Metadata  datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata"`
	Timestamp time.Time      `gorm:"autoCreateTime;index" json:"timestamp"`
}

// TableName overrides
func (Host) TableName() string {
	return "hosts"
}

func (HostDeployment) TableName() string {
	return "host_deployments"
}

func (HostMetric) TableName() string {
	return "host_metrics"
}

func (HostLog) TableName() string {
	return "host_logs"
}

// Helper methods for Host

// IsOnline returns true if host is online
func (h *Host) IsOnline() bool {
	if h.Status != "online" {
		return false
	}

	if h.LastHeartbeat == nil {
		return false
	}

	// Consider offline if no heartbeat in last 2 minutes
	return time.Since(*h.LastHeartbeat) < 2*time.Minute
}

// CanAcceptDeployment checks if host can accept new deployments
func (h *Host) CanAcceptDeployment() bool {
	return h.IsOnline() && h.CurrentDeployments < h.MaxDeployments
}

// UpdateHeartbeat updates the last heartbeat timestamp
func (h *Host) UpdateHeartbeat() {
	now := time.Now().UTC()
	h.LastHeartbeat = &now
	h.Status = "online"
	h.UpdatedAt = now
}

// Helper methods for HostDeployment

// IsRunning returns true if deployment is running
func (hd *HostDeployment) IsRunning() bool {
	return hd.Status == "running"
}

// SetStatus updates the deployment status
func (hd *HostDeployment) SetStatus(status string) {
	hd.Status = status
	hd.UpdatedAt = time.Now().UTC()
}
