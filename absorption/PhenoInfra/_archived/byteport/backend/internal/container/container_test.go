package container

import (
	"testing"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// TestNewContainer tests container initialization
func TestNewContainer(t *testing.T) {
	// Create an in-memory SQLite database for testing
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := NewContainer(db)

	if container == nil {
		t.Fatal("Expected container to be created, got nil")
	}

	// Verify database is set
	if container.DB == nil {
		t.Error("Expected DB to be set")
	}

	// Verify repositories are initialized
	if container.DeploymentRepository == nil {
		t.Error("Expected DeploymentRepository to be initialized")
	}

	// Verify domain services are initialized
	if container.DeploymentDomainService == nil {
		t.Error("Expected DeploymentDomainService to be initialized")
	}

	// Verify use cases are initialized
	if container.CreateDeploymentUseCase == nil {
		t.Error("Expected CreateDeploymentUseCase to be initialized")
	}
	if container.GetDeploymentUseCase == nil {
		t.Error("Expected GetDeploymentUseCase to be initialized")
	}
	if container.ListDeploymentsUseCase == nil {
		t.Error("Expected ListDeploymentsUseCase to be initialized")
	}
	if container.TerminateDeploymentUseCase == nil {
		t.Error("Expected TerminateDeploymentUseCase to be initialized")
	}
	if container.UpdateStatusUseCase == nil {
		t.Error("Expected UpdateStatusUseCase to be initialized")
	}

	// Verify handlers are initialized
	if container.DeploymentHandler == nil {
		t.Error("Expected DeploymentHandler to be initialized")
	}
}

// TestInitRepositories tests repository initialization
func TestInitRepositories(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := &Container{DB: db}
	container.initRepositories()

	if container.DeploymentRepository == nil {
		t.Error("Expected DeploymentRepository to be initialized")
	}
}

// TestInitDomainServices tests domain service initialization
func TestInitDomainServices(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := &Container{DB: db}
	container.initRepositories()
	container.initDomainServices()

	if container.DeploymentDomainService == nil {
		t.Error("Expected DeploymentDomainService to be initialized")
	}
}

// TestInitUseCases tests use case initialization
func TestInitUseCases(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := &Container{DB: db}
	container.initRepositories()
	container.initDomainServices()
	container.initUseCases()

	if container.CreateDeploymentUseCase == nil {
		t.Error("Expected CreateDeploymentUseCase to be initialized")
	}
	if container.GetDeploymentUseCase == nil {
		t.Error("Expected GetDeploymentUseCase to be initialized")
	}
	if container.ListDeploymentsUseCase == nil {
		t.Error("Expected ListDeploymentsUseCase to be initialized")
	}
	if container.TerminateDeploymentUseCase == nil {
		t.Error("Expected TerminateDeploymentUseCase to be initialized")
	}
	if container.UpdateStatusUseCase == nil {
		t.Error("Expected UpdateStatusUseCase to be initialized")
	}
}

// TestInitHandlers tests handler initialization
func TestInitHandlers(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := &Container{DB: db}
	container.initRepositories()
	container.initDomainServices()
	container.initUseCases()
	container.initHandlers()

	if container.DeploymentHandler == nil {
		t.Error("Expected DeploymentHandler to be initialized")
	}
}

// TestContainerIntegration tests full integration
func TestContainerIntegration(t *testing.T) {
	// This is a smoke test to ensure all dependencies wire correctly
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	container := NewContainer(db)

	// Verify the entire dependency chain is properly wired
	// Repository -> Domain Service -> Use Cases -> Handlers
	if container.DeploymentHandler == nil {
		t.Fatal("Handler not initialized")
	}

	// All dependencies should be non-nil at this point
	tests := []struct {
		name  string
		value interface{}
	}{
		{"DB", container.DB},
		{"DeploymentRepository", container.DeploymentRepository},
		{"DeploymentDomainService", container.DeploymentDomainService},
		{"CreateDeploymentUseCase", container.CreateDeploymentUseCase},
		{"GetDeploymentUseCase", container.GetDeploymentUseCase},
		{"ListDeploymentsUseCase", container.ListDeploymentsUseCase},
		{"TerminateDeploymentUseCase", container.TerminateDeploymentUseCase},
		{"UpdateStatusUseCase", container.UpdateStatusUseCase},
		{"DeploymentHandler", container.DeploymentHandler},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.value == nil {
				t.Errorf("%s is nil", tt.name)
			}
		})
	}
}
