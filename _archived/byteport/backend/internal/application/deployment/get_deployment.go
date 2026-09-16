package deployment

import (
	"context"

	"github.com/byteport/api/internal/domain/deployment"
)

// GetDeploymentUseCase handles retrieving a deployment by UUID
type GetDeploymentUseCase struct {
	repository deployment.Repository
	service    deployment.Service
}

// NewGetDeploymentUseCase creates a new use case instance
func NewGetDeploymentUseCase(
	repository deployment.Repository,
	service deployment.Service,
) *GetDeploymentUseCase {
	return &GetDeploymentUseCase{
		repository: repository,
		service:    service,
	}
}

// Execute retrieves a deployment and checks access
func (uc *GetDeploymentUseCase) Execute(
	ctx context.Context,
	uuid string,
	userUUID string,
) (*GetDeploymentResponse, error) {
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

	// Map to response DTO
	response := mapToGetDeploymentResponse(dep)

	return response, nil
}

// mapToGetDeploymentResponse maps domain entity to DTO
func mapToGetDeploymentResponse(dep *deployment.Deployment) *GetDeploymentResponse {
	response := &GetDeploymentResponse{
		UUID:         dep.UUID(),
		Name:         dep.Name(),
		Owner:        dep.Owner(),
		Status:       dep.Status().String(),
		Providers:    dep.Providers(),
		ProjectUUID:  dep.ProjectUUID(),
		Services:     make([]ServiceDTO, 0, len(dep.Services())),
		CreatedAt:    dep.CreatedAt(),
		UpdatedAt:    dep.UpdatedAt(),
		DeployedAt:   dep.DeployedAt(),
		TerminatedAt: dep.TerminatedAt(),
	}

	// Map services
	for _, svc := range dep.Services() {
		response.Services = append(response.Services, ServiceDTO{
			Name:     svc.Name,
			Type:     svc.Type,
			Provider: svc.Provider,
			Status:   svc.Status,
			URL:      svc.URL,
		})
	}

	// Map cost info
	if costInfo := dep.CostInfo(); costInfo != nil {
		response.CostInfo = &CostInfoDTO{
			Monthly:   costInfo.Monthly,
			Breakdown: costInfo.Breakdown,
		}
	}

	return response
}
