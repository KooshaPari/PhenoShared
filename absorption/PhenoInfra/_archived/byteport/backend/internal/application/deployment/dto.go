package deployment

import "time"

// CreateDeploymentRequest represents the input for creating a deployment
type CreateDeploymentRequest struct {
	Name        string                 `json:"name" binding:"required"`
	Owner       string                 `json:"owner" binding:"required"`
	ProjectUUID *string                `json:"project_uuid,omitempty"`
	EnvVars     map[string]string      `json:"env_vars,omitempty"`
	Config      map[string]interface{} `json:"config,omitempty"`
}

// CreateDeploymentResponse represents the output after creating a deployment
type CreateDeploymentResponse struct {
	UUID      string    `json:"uuid"`
	Name      string    `json:"name"`
	Owner     string    `json:"owner"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	Message   string    `json:"message"`
}

// GetDeploymentResponse represents a deployment detail response
type GetDeploymentResponse struct {
	UUID         string                 `json:"uuid"`
	Name         string                 `json:"name"`
	Owner        string                 `json:"owner"`
	ProjectUUID  *string                `json:"project_uuid,omitempty"`
	Status       string                 `json:"status"`
	Providers    map[string]interface{} `json:"providers"`
	Services     []ServiceDTO           `json:"services"`
	CostInfo     *CostInfoDTO           `json:"cost_info,omitempty"`
	CreatedAt    time.Time              `json:"created_at"`
	UpdatedAt    time.Time              `json:"updated_at"`
	DeployedAt   *time.Time             `json:"deployed_at,omitempty"`
	TerminatedAt *time.Time             `json:"terminated_at,omitempty"`
}

// ListDeploymentsRequest represents pagination and filtering parameters
type ListDeploymentsRequest struct {
	Owner  string `form:"owner"`
	Status string `form:"status"`
	Offset int    `form:"offset"`
	Limit  int    `form:"limit" binding:"max=100"`
}

// ListDeploymentsResponse represents a list of deployments with pagination
type ListDeploymentsResponse struct {
	Deployments []DeploymentSummaryDTO `json:"deployments"`
	Total       int64                  `json:"total"`
	Offset      int                    `json:"offset"`
	Limit       int                    `json:"limit"`
}

// DeploymentSummaryDTO is a lightweight deployment representation for lists
type DeploymentSummaryDTO struct {
	UUID        string     `json:"uuid"`
	Name        string     `json:"name"`
	Owner       string     `json:"owner"`
	Status      string     `json:"status"`
	ServiceCount int       `json:"service_count"`
	MonthlyCost float64    `json:"monthly_cost"`
	CreatedAt   time.Time  `json:"created_at"`
	DeployedAt  *time.Time `json:"deployed_at,omitempty"`
}

// UpdateStatusRequest represents a status update request
type UpdateStatusRequest struct {
	UUID   string `json:"uuid,omitempty"`
	Status string `json:"status" binding:"required"`
}

// AddServiceRequest represents adding a service to a deployment
type AddServiceRequest struct {
	Name     string `json:"name" binding:"required"`
	Type     string `json:"type" binding:"required"`
	Provider string `json:"provider" binding:"required"`
	URL      string `json:"url,omitempty"`
}

// ServiceDTO represents a service in the deployment
type ServiceDTO struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	Provider string `json:"provider"`
	Status   string `json:"status"`
	URL      string `json:"url,omitempty"`
}

// CostInfoDTO represents cost information
type CostInfoDTO struct {
	Monthly   float64            `json:"monthly"`
	Breakdown map[string]float64 `json:"breakdown"`
}

// TerminateDeploymentResponse represents the result of terminating a deployment
type TerminateDeploymentResponse struct {
	UUID      string    `json:"uuid"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	Terminated time.Time `json:"terminated_at"`
}
