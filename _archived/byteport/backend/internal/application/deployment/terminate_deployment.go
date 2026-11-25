package deployment

import (
	"context"
	"time"

	"github.com/byteport/api/internal/domain/deployment"
)

// TerminateDeploymentUseCase handles terminating a deployment
type TerminateDeploymentUseCase struct {
	repository deployment.Repository
	service    deployment.Service
}

// NewTerminateDeploymentUseCase creates a new use case instance
func NewTerminateDeploymentUseCase(
	repository deployment.Repository,
	service deployment.Service,
) *TerminateDeploymentUseCase {
	return &TerminateDeploymentUseCase{
		repository: repository,
		service:    service,
	}
}

// Execute terminates a deployment
func (uc *TerminateDeploymentUseCase) Execute(
	ctx context.Context,
	uuid string,
	userUUID string,
) (*TerminateDeploymentResponse, error) {
	// Input validation
	if uuid == "" {
		return nil, NewValidationError("deployment UUID is required")
	}
	if userUUID == "" {
		return nil, NewUnauthorizedError("user authentication required")
	}

	// Retrieve deployment
	dep, err := uc.repository.FindByUUID(ctx, uuid)
	if err != nil {
		return nil, NewInternalError("failed to retrieve deployment", err)
	}
	if dep == nil {
		return nil, NewNotFoundError("deployment")
	}

	// Check access permissions
	hasAccess, err := uc.service.CanUserAccessDeployment(ctx, userUUID, uuid)
	if err != nil {
		return nil, NewInternalError("failed to check permissions", err)
	}
	if !hasAccess {
		return nil, NewForbiddenError("you do not have access to this deployment")
	}

	// Check if already terminated
	if dep.IsTerminated() {
		return nil, NewConflictError("deployment is already terminated")
	}

	// Update status to terminated
	if err := dep.SetStatus(deployment.StatusTerminated); err != nil {
		return nil, NewConflictError(err.Error())
	}

	// Persist the update
	if err := uc.repository.Update(ctx, dep); err != nil {
		return nil, NewInternalError("failed to terminate deployment", err)
	}

	// Map to response DTO
	response := &TerminateDeploymentResponse{
		UUID:       dep.UUID(),
		Status:     dep.Status().String(),
		Message:    "Deployment terminated successfully",
		Terminated: time.Now().UTC(),
	}

	return response, nil
}
