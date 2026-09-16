package deployment

import (
	"context"

	"github.com/byteport/api/internal/domain/deployment"
)

// ListDeploymentsUseCase handles listing deployments with filtering and pagination
type ListDeploymentsUseCase struct {
	repository deployment.Repository
}

// NewListDeploymentsUseCase creates a new use case instance
func NewListDeploymentsUseCase(repository deployment.Repository) *ListDeploymentsUseCase {
	return &ListDeploymentsUseCase{
		repository: repository,
	}
}

// Execute lists deployments based on filters
func (uc *ListDeploymentsUseCase) Execute(
	ctx context.Context,
	req ListDeploymentsRequest,
) (*ListDeploymentsResponse, error) {
	// Set defaults
	if req.Limit <= 0 {
		req.Limit = 50
	}
	if req.Limit > 100 {
		req.Limit = 100
	}

	var deployments []*deployment.Deployment
	var err error

	// Apply filters
	if req.Owner != "" {
		deployments, err = uc.repository.FindByOwner(ctx, req.Owner)
	} else if req.Status != "" {
		status := deployment.Status(req.Status)
		if !status.IsValid() {
			return nil, NewValidationError("invalid status value")
		}
		deployments, err = uc.repository.FindByStatus(ctx, status)
	} else {
		deployments, err = uc.repository.List(ctx, req.Offset, req.Limit)
	}

	if err != nil {
		return nil, NewInternalError("failed to list deployments", err)
	}

	// Get total count
	var total int64
	if req.Owner != "" {
		total, err = uc.repository.CountByOwner(ctx, req.Owner)
	} else {
		total, err = uc.repository.Count(ctx)
	}
	if err != nil {
		// Don't fail if count fails, just log it
		total = int64(len(deployments))
	}

	// Map to response DTOs
	summaries := make([]DeploymentSummaryDTO, 0, len(deployments))
	for _, dep := range deployments {
		summary := DeploymentSummaryDTO{
			UUID:         dep.UUID(),
			Name:         dep.Name(),
			Owner:        dep.Owner(),
			Status:       dep.Status().String(),
			ServiceCount: len(dep.Services()),
			MonthlyCost:  dep.CalculateTotalCost(),
			CreatedAt:    dep.CreatedAt(),
			DeployedAt:   dep.DeployedAt(),
		}
		summaries = append(summaries, summary)
	}

	response := &ListDeploymentsResponse{
		Deployments: summaries,
		Total:       total,
		Offset:      req.Offset,
		Limit:       req.Limit,
	}

	return response, nil
}
