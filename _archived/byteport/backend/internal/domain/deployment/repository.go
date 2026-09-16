package deployment

import "context"

// Repository defines the interface for deployment persistence (Domain Port)
// This interface belongs to the domain layer and will be implemented by infrastructure
type Repository interface {
	// Create saves a new deployment
	Create(ctx context.Context, deployment *Deployment) error
	
	// Update updates an existing deployment
	Update(ctx context.Context, deployment *Deployment) error
	
	// Delete soft deletes a deployment
	Delete(ctx context.Context, uuid string) error
	
	// FindByUUID retrieves a deployment by UUID
	FindByUUID(ctx context.Context, uuid string) (*Deployment, error)
	
	// FindByOwner retrieves all deployments for an owner
	FindByOwner(ctx context.Context, owner string) ([]*Deployment, error)
	
	// FindByProject retrieves all deployments for a project
	FindByProject(ctx context.Context, projectUUID string) ([]*Deployment, error)
	
	// FindByStatus retrieves deployments by status
	FindByStatus(ctx context.Context, status Status) ([]*Deployment, error)
	
	// List retrieves deployments with pagination
	List(ctx context.Context, offset, limit int) ([]*Deployment, error)
	
	// Count returns the total number of deployments
	Count(ctx context.Context) (int64, error)
	
	// CountByOwner returns the number of deployments for an owner
	CountByOwner(ctx context.Context, owner string) (int64, error)
}
