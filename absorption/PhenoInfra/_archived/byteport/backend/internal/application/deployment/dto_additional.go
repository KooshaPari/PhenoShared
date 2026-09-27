package deployment

import "time"

// DeploymentDTO represents a complete deployment for responses
type DeploymentDTO struct {
	UUID         string                 `json:"uuid"`
	Name         string                 `json:"name"`
	Owner        string                 `json:"owner"`
	ProjectUUID  *string                `json:"project_uuid,omitempty"`
	Status       string                 `json:"status"`
	Provider     string                 `json:"provider,omitempty"`
	Region       string                 `json:"region,omitempty"`
	Providers    map[string]interface{} `json:"providers,omitempty"`
	Services     []ServiceDTO           `json:"services,omitempty"`
	CostInfo     *CostInfoDTO           `json:"cost_info,omitempty"`
	EnvVars      map[string]string      `json:"env_vars,omitempty"`
	CreatedAt    time.Time              `json:"created_at"`
	UpdatedAt    time.Time              `json:"updated_at"`
	DeployedAt   *time.Time             `json:"deployed_at,omitempty"`
	TerminatedAt *time.Time             `json:"terminated_at,omitempty"`
}

// DeploymentListDTO represents a list of deployments with metadata
type DeploymentListDTO struct {
	Deployments []DeploymentDTO `json:"deployments"`
	Total       int             `json:"total"`
	Offset      int             `json:"offset,omitempty"`
	Limit       int             `json:"limit,omitempty"`
}

