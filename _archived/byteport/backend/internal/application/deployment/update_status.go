package deployment

import (
	"context"

	"github.com/byteport/api/internal/domain/deployment"
)

// UpdateStatusUseCase handles updating deployment status
type UpdateStatusUseCase struct {
	repository deployment.Repository
	service    deployment.Service
}

// NewUpdateStatusUseCase creates a new use case instance
func NewUpdateStatusUseCase(
	repository deployment.Repository,
	service deployment.Service,
) *UpdateStatusUseCase {
	return &UpdateStatusUseCase{
		repository: repository,
		service:    service,
	}
}

// Execute updates the deployment status
func (uc *UpdateStatusUseCase) Execute(
	ctx context.Context,
	uuid string,
	req UpdateStatusRequest,
	userUUID string,
) error {
	// Input validation
	if uuid == "" {
		return NewValidationError("deployment UUID is required")
	}
	if req.Status == "" {
		return NewValidationError("status is required")
	}
	if userUUID == "" {
		return NewUnauthorizedError("user authentication required")
	}

	// Validate status
	newStatus := deployment.Status(req.Status)
	if !newStatus.IsValid() {
		return NewValidationError("invalid status value")
	}

	// Retrieve deployment
	dep, err := uc.repository.FindByUUID(ctx, uuid)
	if err != nil {
		return NewInternalError("failed to retrieve deployment", err)
	}
	if dep == nil {
		return NewNotFoundError("deployment")
	}

	// Check access permissions
	hasAccess, err := uc.service.CanUserAccessDeployment(ctx, userUUID, uuid)
	if err != nil {
		return NewInternalError("failed to check permissions", err)
	}
	if !hasAccess {
		return NewForbiddenError("you do not have access to this deployment")
	}

	// Update status with domain validation
	if err := dep.SetStatus(newStatus); err != nil {
		return NewConflictError(err.Error())
	}

	// Persist the update
	if err := uc.repository.Update(ctx, dep); err != nil {
		return NewInternalError("failed to update deployment status", err)
	}

	return nil
}
