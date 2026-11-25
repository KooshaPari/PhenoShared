package postgres

import (
	"context"
	"fmt"

	"github.com/byteport/api/internal/domain/deployment"
	"gorm.io/gorm"
)

// DeploymentRepository implements the domain Repository interface using PostgreSQL
type DeploymentRepository struct {
	db *gorm.DB
}

// NewDeploymentRepository creates a new PostgreSQL repository
func NewDeploymentRepository(db *gorm.DB) *DeploymentRepository {
	return &DeploymentRepository{db: db}
}

// Create saves a new deployment
func (r *DeploymentRepository) Create(ctx context.Context, dep *deployment.Deployment) error {
	model, err := DomainToModel(dep)
	if err != nil {
		return fmt.Errorf("failed to convert to model: %w", err)
	}

	result := r.db.WithContext(ctx).Create(model)
	if result.Error != nil {
		return fmt.Errorf("failed to create deployment: %w", result.Error)
	}

	return nil
}

// Update saves changes to an existing deployment
func (r *DeploymentRepository) Update(ctx context.Context, dep *deployment.Deployment) error {
	model, err := DomainToModel(dep)
	if err != nil {
		return fmt.Errorf("failed to convert to model: %w", err)
	}

	result := r.db.WithContext(ctx).
		Model(&DeploymentModel{}).
		Where("uuid = ?", dep.UUID()).
		Updates(model)

	if result.Error != nil {
		return fmt.Errorf("failed to update deployment: %w", result.Error)
	}

	if result.RowsAffected == 0 {
		return fmt.Errorf("deployment not found: %s", dep.UUID())
	}

	return nil
}

// Delete soft-deletes a deployment
func (r *DeploymentRepository) Delete(ctx context.Context, uuid string) error {
	result := r.db.WithContext(ctx).
		Where("uuid = ?", uuid).
		Delete(&DeploymentModel{})

	if result.Error != nil {
		return fmt.Errorf("failed to delete deployment: %w", result.Error)
	}

	if result.RowsAffected == 0 {
		return fmt.Errorf("deployment not found: %s", uuid)
	}

	return nil
}

// FindByUUID retrieves a deployment by UUID
func (r *DeploymentRepository) FindByUUID(ctx context.Context, uuid string) (*deployment.Deployment, error) {
	var model DeploymentModel
	result := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&model)

	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil // Not found is not an error, return nil
		}
		return nil, fmt.Errorf("failed to find deployment: %w", result.Error)
	}

	dep, err := ModelToDomain(&model)
	if err != nil {
		return nil, fmt.Errorf("failed to convert to domain: %w", err)
	}

	return dep, nil
}

// FindByOwner retrieves all deployments for an owner
func (r *DeploymentRepository) FindByOwner(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
	var models []DeploymentModel
	result := r.db.WithContext(ctx).Where("owner = ?", owner).Find(&models)

	if result.Error != nil {
		return nil, fmt.Errorf("failed to find deployments by owner: %w", result.Error)
	}

	deployments := make([]*deployment.Deployment, 0, len(models))
	for _, model := range models {
		dep, err := ModelToDomain(&model)
		if err != nil {
			return nil, fmt.Errorf("failed to convert to domain: %w", err)
		}
		deployments = append(deployments, dep)
	}

	return deployments, nil
}

// FindByProject retrieves all deployments for a project
func (r *DeploymentRepository) FindByProject(ctx context.Context, projectUUID string) ([]*deployment.Deployment, error) {
	var models []DeploymentModel
	result := r.db.WithContext(ctx).Where("project_uuid = ?", projectUUID).Find(&models)

	if result.Error != nil {
		return nil, fmt.Errorf("failed to find deployments by project: %w", result.Error)
	}

	deployments := make([]*deployment.Deployment, 0, len(models))
	for _, model := range models {
		dep, err := ModelToDomain(&model)
		if err != nil {
			return nil, fmt.Errorf("failed to convert to domain: %w", err)
		}
		deployments = append(deployments, dep)
	}

	return deployments, nil
}

// FindByStatus retrieves all deployments with a specific status
func (r *DeploymentRepository) FindByStatus(ctx context.Context, status deployment.Status) ([]*deployment.Deployment, error) {
	var models []DeploymentModel
	result := r.db.WithContext(ctx).Where("status = ?", status.String()).Find(&models)

	if result.Error != nil {
		return nil, fmt.Errorf("failed to find deployments by status: %w", result.Error)
	}

	deployments := make([]*deployment.Deployment, 0, len(models))
	for _, model := range models {
		dep, err := ModelToDomain(&model)
		if err != nil {
			return nil, fmt.Errorf("failed to convert to domain: %w", err)
		}
		deployments = append(deployments, dep)
	}

	return deployments, nil
}

// List retrieves deployments with pagination
func (r *DeploymentRepository) List(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
	var models []DeploymentModel
	result := r.db.WithContext(ctx).
		Offset(offset).
		Limit(limit).
		Order("created_at DESC").
		Find(&models)

	if result.Error != nil {
		return nil, fmt.Errorf("failed to list deployments: %w", result.Error)
	}

	deployments := make([]*deployment.Deployment, 0, len(models))
	for _, model := range models {
		dep, err := ModelToDomain(&model)
		if err != nil {
			return nil, fmt.Errorf("failed to convert to domain: %w", err)
		}
		deployments = append(deployments, dep)
	}

	return deployments, nil
}

// Count returns the total number of deployments
func (r *DeploymentRepository) Count(ctx context.Context) (int64, error) {
	var count int64
	result := r.db.WithContext(ctx).Model(&DeploymentModel{}).Count(&count)

	if result.Error != nil {
		return 0, fmt.Errorf("failed to count deployments: %w", result.Error)
	}

	return count, nil
}

// CountByOwner returns the number of deployments for an owner
func (r *DeploymentRepository) CountByOwner(ctx context.Context, owner string) (int64, error) {
	var count int64
	result := r.db.WithContext(ctx).
		Model(&DeploymentModel{}).
		Where("owner = ?", owner).
		Count(&count)

	if result.Error != nil {
		return 0, fmt.Errorf("failed to count deployments by owner: %w", result.Error)
	}

	return count, nil
}
