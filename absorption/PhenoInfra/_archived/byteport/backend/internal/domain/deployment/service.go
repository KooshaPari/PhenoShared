package deployment

import (
	"context"
	"errors"
)

// Service provides domain services for deployment business logic
// Handles operations that don't naturally fit within a single entity
type Service interface {
	// ValidateDeployment validates a deployment before creation/update
	ValidateDeployment(ctx context.Context, deployment *Deployment) error
	
	// CanUserAccessDeployment checks if user has access to deployment
	CanUserAccessDeployment(ctx context.Context, userUUID, deploymentUUID string) (bool, error)
	
	// CalculateEstimatedCost calculates estimated cost for a deployment
	CalculateEstimatedCost(ctx context.Context, deployment *Deployment) (*CostInfo, error)
	
	// SelectOptimalProvider selects the best provider for a service type
	SelectOptimalProvider(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error)
}

// DomainService implements the Service interface
type DomainService struct {
	repository Repository
}

// NewDomainService creates a new domain service
func NewDomainService(repository Repository) Service {
	return &DomainService{
		repository: repository,
	}
}

// ValidateDeployment validates a deployment
func (s *DomainService) ValidateDeployment(ctx context.Context, deployment *Deployment) error {
	if deployment == nil {
		return errors.New("deployment cannot be nil")
	}
	
	// Perform domain validation
	if err := deployment.Validate(); err != nil {
		return err
	}
	
	// Check for name conflicts within owner's deployments
	ownerDeployments, err := s.repository.FindByOwner(ctx, deployment.Owner())
	if err != nil {
		return err
	}
	
	for _, existing := range ownerDeployments {
		if existing.UUID() != deployment.UUID() && existing.Name() == deployment.Name() {
			return NewInvalidDeploymentError("deployment name already exists for this owner")
		}
	}
	
	return nil
}

// CanUserAccessDeployment checks if user can access deployment
func (s *DomainService) CanUserAccessDeployment(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
	deployment, err := s.repository.FindByUUID(ctx, deploymentUUID)
	if err != nil {
		return false, err
	}
	
	if deployment == nil {
		return false, NewDeploymentNotFoundError(deploymentUUID)
	}
	
	// User can access if they own the deployment
	return deployment.Owner() == userUUID, nil
}

// CalculateEstimatedCost calculates estimated cost
func (s *DomainService) CalculateEstimatedCost(ctx context.Context, deployment *Deployment) (*CostInfo, error) {
	// Cost calculation logic based on services and providers
	// This is a simplified implementation
	
	breakdown := make(map[string]float64)
	
	for _, svc := range deployment.Services() {
		// Simplified cost estimation
		cost := estimateServiceCost(svc.Type, svc.Provider)
		breakdown[svc.Provider] += cost
	}
	
	total := 0.0
	for _, cost := range breakdown {
		total += cost
	}
	
	return &CostInfo{
		Monthly:   total,
		Breakdown: breakdown,
	}, nil
}

// SelectOptimalProvider selects the best provider
func (s *DomainService) SelectOptimalProvider(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error) {
	// Provider selection logic based on service type and constraints
	// This is a simplified implementation
	
	providerMap := map[string]string{
		"frontend": "vercel",
		"backend":  "render",
		"database": "supabase",
	}
	
	provider, exists := providerMap[serviceType]
	if !exists {
		return "railway", nil // Default fallback
	}
	
	return provider, nil
}

// estimateServiceCost estimates cost for a service
func estimateServiceCost(serviceType, provider string) float64 {
	// Simplified cost estimation
	// In production, this would query a pricing service
	
	costs := map[string]map[string]float64{
		"frontend": {
			"vercel":   0.0,  // Free tier
			"netlify":  0.0,  // Free tier
			"cloudflare": 0.0,
		},
		"backend": {
			"render":   7.0,  // Hobby plan
			"railway":  5.0,
			"fly":      0.0,  // Free tier
		},
		"database": {
			"supabase": 0.0,  // Free tier
			"neon":     0.0,  // Free tier
		},
	}
	
	if providerCosts, ok := costs[serviceType]; ok {
		if cost, ok := providerCosts[provider]; ok {
			return cost
		}
	}
	
	return 0.0
}
