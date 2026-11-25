package container

import (
	"github.com/byteport/api/internal/application/deployment"
	domaindep "github.com/byteport/api/internal/domain/deployment"
	"github.com/byteport/api/internal/infrastructure/http/handlers"
	"github.com/byteport/api/internal/infrastructure/persistence/postgres"
	"gorm.io/gorm"
)

// Container holds all dependencies
type Container struct {
	// Database
	DB *gorm.DB

	// Repositories
	DeploymentRepository domaindep.Repository

	// Domain Services
	DeploymentDomainService domaindep.Service

	// Use Cases
	CreateDeploymentUseCase    *deployment.CreateDeploymentUseCase
	GetDeploymentUseCase       *deployment.GetDeploymentUseCase
	ListDeploymentsUseCase     *deployment.ListDeploymentsUseCase
	TerminateDeploymentUseCase *deployment.TerminateDeploymentUseCase
	UpdateStatusUseCase        *deployment.UpdateStatusUseCase

	// HTTP Handlers
	DeploymentHandler *handlers.DeploymentHandler
}

// NewContainer creates a new dependency injection container
func NewContainer(db *gorm.DB) *Container {
	c := &Container{
		DB: db,
	}

	// Initialize dependencies in order
	c.initRepositories()
	c.initDomainServices()
	c.initUseCases()
	c.initHandlers()

	return c
}

// initRepositories initializes repository implementations
func (c *Container) initRepositories() {
	c.DeploymentRepository = postgres.NewDeploymentRepository(c.DB)
}

// initDomainServices initializes domain services
func (c *Container) initDomainServices() {
	c.DeploymentDomainService = domaindep.NewDomainService(c.DeploymentRepository)
}

// initUseCases initializes application use cases
func (c *Container) initUseCases() {
	c.CreateDeploymentUseCase = deployment.NewCreateDeploymentUseCase(
		c.DeploymentRepository,
		c.DeploymentDomainService,
	)

	c.GetDeploymentUseCase = deployment.NewGetDeploymentUseCase(
		c.DeploymentRepository,
		c.DeploymentDomainService,
	)

	c.ListDeploymentsUseCase = deployment.NewListDeploymentsUseCase(
		c.DeploymentRepository,
	)

	c.TerminateDeploymentUseCase = deployment.NewTerminateDeploymentUseCase(
		c.DeploymentRepository,
		c.DeploymentDomainService,
	)

	c.UpdateStatusUseCase = deployment.NewUpdateStatusUseCase(
		c.DeploymentRepository,
		c.DeploymentDomainService,
	)
}

// initHandlers initializes HTTP handlers
func (c *Container) initHandlers() {
	c.DeploymentHandler = handlers.NewDeploymentHandler(
		c.CreateDeploymentUseCase,
		c.GetDeploymentUseCase,
		c.ListDeploymentsUseCase,
		c.TerminateDeploymentUseCase,
		c.UpdateStatusUseCase,
	)
}
