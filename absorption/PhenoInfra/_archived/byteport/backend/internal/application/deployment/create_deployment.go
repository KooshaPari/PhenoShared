package deployment

import (
	"context"
	"log"

	"github.com/byteport/api/internal/domain/deployment"
)

// CreateDeploymentUseCase handles the creation of a new deployment
type CreateDeploymentUseCase struct {
	repository deployment.Repository
	service    deployment.Service
}

// NewCreateDeploymentUseCase creates a new use case instance
func NewCreateDeploymentUseCase(
	repository deployment.Repository,
	service deployment.Service,
) *CreateDeploymentUseCase {
	return &CreateDeploymentUseCase{
		repository: repository,
		service:    service,
	}
}

// Execute creates a new deployment
func (uc *CreateDeploymentUseCase) Execute(
	ctx context.Context,
	req CreateDeploymentRequest,
) (*CreateDeploymentResponse, error) {
	// Input validation
	if req.Name == "" {
		return nil, NewValidationError("deployment name is required")
	}
	if req.Owner == "" {
		return nil, NewValidationError("owner is required")
	}

	// Create domain entity
	dep, err := deployment.NewDeployment(req.Name, req.Owner, req.ProjectUUID)
	if err != nil {
		return nil, NewValidationError(err.Error())
	}

	// Set environment variables if provided
	for key, value := range req.EnvVars {
		dep.SetEnvVar(key, value)
	}

	// Validate with domain service
	if err := uc.service.ValidateDeployment(ctx, dep); err != nil {
		return nil, NewConflictError(err.Error())
	}

	// Persist the deployment
	if err := uc.repository.Create(ctx, dep); err != nil {
		log.Printf("Failed to create deployment: %v", err)
		return nil, NewInternalError("failed to create deployment", err)
	}

	// Map to response DTO
	response := &CreateDeploymentResponse{
		UUID:      dep.UUID(),
		Name:      dep.Name(),
		Owner:     dep.Owner(),
		Status:    dep.Status().String(),
		CreatedAt: dep.CreatedAt(),
		Message:   "Deployment created successfully",
	}

	return response, nil
}
