package models

import (
	"gorm.io/datatypes"
	"time"
)

// Deployment represents a multi-cloud deployment
type Deployment struct {
	UUID        string  `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"uuid"`
	Name        string  `gorm:"type:varchar(255);not null" json:"name"`
	Owner       string  `gorm:"type:uuid;not null;index" json:"owner"`
	ProjectUUID *string `gorm:"type:uuid;index" json:"project_uuid,omitempty"`

	// Deployment status
	Status string `gorm:"type:varchar(50);not null;index;default:'pending'" json:"status"`
	// Status values: pending, detecting, provisioning, deploying, deployed, failed, terminated

	// Provider configuration (JSONB for flexibility)
	Providers datatypes.JSON `gorm:"type:jsonb;not null;default:'{}'" json:"providers"`
	// Example: {"vercel": {"project_id": "...", "url": "..."}, "supabase": {...}}

	// Services deployed (JSONB array)
	Services datatypes.JSON `gorm:"type:jsonb;not null;default:'[]'" json:"services"`
	// Example: [{"name": "frontend", "type": "frontend", "provider": "vercel", "status": "running"}]

	// Cost tracking
	CostInfo datatypes.JSON `gorm:"type:jsonb" json:"cost_info,omitempty"`
	// Example: {"monthly": 25, "breakdown": {"vercel": 0, "render": 7}}

	// Deployment metadata
	Metadata datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata,omitempty"`
	// Store provider-specific IDs, configurations, etc.

	// Environment variables (encrypted in production)
	EnvVars datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"env_vars,omitempty"`

	// Build information
	BuildConfig datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"build_config,omitempty"`
	// Store build commands, framework detection results, etc.

	// Timestamps
	CreatedAt    time.Time  `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt    time.Time  `gorm:"autoUpdateTime" json:"updated_at"`
	DeployedAt   *time.Time `json:"deployed_at,omitempty"`
	TerminatedAt *time.Time `json:"terminated_at,omitempty"`
	DeletedAt    *time.Time `gorm:"index" json:"deleted_at,omitempty"`
}

// DeploymentLog represents logs from deployment process
type DeploymentLog struct {
	ID             int64   `gorm:"primaryKey;autoIncrement" json:"id"`
	DeploymentUUID string  `gorm:"type:uuid;not null;index" json:"deployment_uuid"`
	ServiceName    *string `gorm:"type:varchar(255)" json:"service_name,omitempty"`
	Level          string  `gorm:"type:varchar(20);not null;default:'info'" json:"level"`
	// Levels: debug, info, warn, error
	Message   string         `gorm:"type:text;not null" json:"message"`
	Metadata  datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata,omitempty"`
	Timestamp time.Time      `gorm:"autoCreateTime;index" json:"timestamp"`
}

// ProviderCredential stores user-specific provider credentials
type ProviderCredential struct {
	ID       int    `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID   string `gorm:"type:uuid;not null;index" json:"user_id"`
	Provider string `gorm:"type:varchar(100);not null" json:"provider"`
	// Providers: vercel, render, supabase, neon, upstash, fly, railway, etc.
	Credentials datatypes.JSON `gorm:"type:jsonb;not null" json:"credentials"`
	// Store encrypted API keys, tokens, etc.
	IsValid       bool       `gorm:"default:true" json:"is_valid"`
	LastValidated *time.Time `json:"last_validated,omitempty"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`
}

// DeploymentEvent represents audit trail for deployments
type DeploymentEvent struct {
	ID             int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	DeploymentUUID string `gorm:"type:uuid;not null;index" json:"deployment_uuid"`
	EventType      string `gorm:"type:varchar(100);not null;index" json:"event_type"`
	// Event types: created, status_changed, service_added, service_removed, failed, terminated
	EventData datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"event_data"`
	UserID    *string        `gorm:"type:uuid" json:"user_id,omitempty"`
	Timestamp time.Time      `gorm:"autoCreateTime;index" json:"timestamp"`
}

// CostRecord tracks historical cost data
type CostRecord struct {
	ID             int64          `gorm:"primaryKey;autoIncrement" json:"id"`
	DeploymentUUID *string        `gorm:"type:uuid;index" json:"deployment_uuid,omitempty"`
	UserID         string         `gorm:"type:uuid;not null;index" json:"user_id"`
	PeriodStart    time.Time      `gorm:"type:date;not null;index" json:"period_start"`
	PeriodEnd      time.Time      `gorm:"type:date;not null;index" json:"period_end"`
	TotalCost      float64        `gorm:"type:decimal(10,2);not null" json:"total_cost"`
	Breakdown      datatypes.JSON `gorm:"type:jsonb;not null" json:"breakdown"`
	// Breakdown by provider
	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
}

// TableName overrides
func (Deployment) TableName() string {
	return "deployments"
}

func (DeploymentLog) TableName() string {
	return "deployment_logs"
}

func (ProviderCredential) TableName() string {
	return "provider_credentials"
}

func (DeploymentEvent) TableName() string {
	return "deployment_events"
}

func (CostRecord) TableName() string {
	return "cost_records"
}

// Helper methods for Deployment

// SetStatus updates the deployment status and creates an event
func (d *Deployment) SetStatus(status string) {
	d.Status = status
	now := time.Now().UTC()
	d.UpdatedAt = now

	switch status {
	case "deployed":
		d.DeployedAt = &now
		d.TerminatedAt = nil
	case "terminated":
		d.TerminatedAt = &now
	default:
		d.TerminatedAt = nil
	}
}

// IsActive returns true if deployment is in an active state
func (d *Deployment) IsActive() bool {
	return d.Status == "deploying" || d.Status == "deployed"
}

// IsFailed returns true if deployment failed
func (d *Deployment) IsFailed() bool {
	return d.Status == "failed"
}

// IsTerminated returns true if deployment is terminated
func (d *Deployment) IsTerminated() bool {
	return d.Status == "terminated" || d.TerminatedAt != nil
}
