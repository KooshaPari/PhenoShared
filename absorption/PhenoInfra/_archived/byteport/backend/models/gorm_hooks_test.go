package models

import (
	"encoding/json"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

// TestGORMHooks tests the GORM hooks directly without requiring a database
func TestProject_BeforeSave(t *testing.T) {
	// Create a mock GORM DB instance
	db := &gorm.DB{}

	t.Run("generates UUID when empty", func(t *testing.T) {
		project := &Project{
			ID:    "test-project",
			Owner: "user-123",
			Name:  "Test Project",
		}

		// Call BeforeSave hook directly
		err := project.BeforeSave(db)
		require.NoError(t, err)

		// UUID should be generated
		assert.NotEmpty(t, project.UUID)
		assert.NotEqual(t, "", project.UUID)

		// Verify it's a valid UUID
		_, err = uuid.Parse(project.UUID)
		assert.NoError(t, err)
	})

	t.Run("preserves existing UUID", func(t *testing.T) {
		existingUUID := "existing-uuid-123"
		project := &Project{
			UUID:  existingUUID,
			ID:    "test-project-2",
			Owner: "user-456",
			Name:  "Test Project 2",
		}

		err := project.BeforeSave(db)
		require.NoError(t, err)

		assert.Equal(t, existingUUID, project.UUID)
	})

	t.Run("serializes deployments to JSON", func(t *testing.T) {
		project := &Project{
			ID:    "test-project-3",
			Owner: "user-789",
			Name:  "Test Project 3",
		}

		// Set deployments
		deployments := map[string]Instance{
			"prod": {
				UUID:   "instance-prod",
				Name:   "Production",
				Status: "running",
			},
			"staging": {
				UUID:   "instance-staging",
				Name:   "Staging",
				Status: "stopped",
			},
		}
		project.SetDeploy(deployments)

		err := project.BeforeSave(db)
		require.NoError(t, err)

		// DeploymentsJSON should be set
		assert.NotEmpty(t, project.DeploymentsJSON)

		// Verify JSON content
		var deserializedDeployments map[string]Instance
		err = json.Unmarshal([]byte(project.DeploymentsJSON), &deserializedDeployments)
		require.NoError(t, err)

		assert.Equal(t, "instance-prod", deserializedDeployments["prod"].UUID)
		assert.Equal(t, "Production", deserializedDeployments["prod"].Name)
		assert.Equal(t, "running", deserializedDeployments["prod"].Status)
		assert.Equal(t, "instance-staging", deserializedDeployments["staging"].UUID)
		assert.Equal(t, "Staging", deserializedDeployments["staging"].Name)
		assert.Equal(t, "stopped", deserializedDeployments["staging"].Status)
	})

	t.Run("handles nil deployments", func(t *testing.T) {
		project := &Project{
			ID:    "test-project-4",
			Owner: "user-101",
			Name:  "Test Project 4",
		}

		// Don't set deployments (should be nil)
		err := project.BeforeSave(db)
		require.NoError(t, err)

		// DeploymentsJSON should remain empty
		assert.Empty(t, project.DeploymentsJSON)
	})

	t.Run("handles empty deployments map", func(t *testing.T) {
		project := &Project{
			ID:    "test-project-5",
			Owner: "user-102",
			Name:  "Test Project 5",
		}

		// Set empty deployments map
		project.SetDeploy(make(map[string]Instance))

		err := project.BeforeSave(db)
		require.NoError(t, err)

		// DeploymentsJSON should be set to empty JSON object
		assert.Equal(t, "{}", project.DeploymentsJSON)
	})
}

func TestProject_AfterFind(t *testing.T) {
	// Create a mock GORM DB instance
	db := &gorm.DB{}

	t.Run("deserializes deployments from JSON", func(t *testing.T) {
		project := &Project{
			UUID:            "test-uuid-123",
			ID:              "test-project",
			Owner:           "user-123",
			Name:            "Test Project",
			DeploymentsJSON: `{"prod":{"uuid":"instance-prod","name":"Production","status":"running"},"staging":{"uuid":"instance-staging","name":"Staging","status":"stopped"}}`,
		}

		// Call AfterFind hook directly
		err := project.AfterFind(db)
		require.NoError(t, err)

		// Deployments should be deserialized
		deployments := project.GetDeploy()
		assert.NotNil(t, deployments)
		assert.Len(t, deployments, 2)

		assert.Equal(t, "instance-prod", deployments["prod"].UUID)
		assert.Equal(t, "Production", deployments["prod"].Name)
		assert.Equal(t, "running", deployments["prod"].Status)
		assert.Equal(t, "instance-staging", deployments["staging"].UUID)
		assert.Equal(t, "Staging", deployments["staging"].Name)
		assert.Equal(t, "stopped", deployments["staging"].Status)
	})

	t.Run("handles empty JSON", func(t *testing.T) {
		project := &Project{
			UUID:            "test-uuid-456",
			ID:              "test-project-2",
			Owner:           "user-456",
			Name:            "Test Project 2",
			DeploymentsJSON: "",
		}

		err := project.AfterFind(db)
		require.NoError(t, err)

		// Deployments should be initialized as empty map
		deployments := project.GetDeploy()
		assert.NotNil(t, deployments)
		assert.Len(t, deployments, 0)
	})

	t.Run("handles empty JSON object", func(t *testing.T) {
		project := &Project{
			UUID:            "test-uuid-789",
			ID:              "test-project-3",
			Owner:           "user-789",
			Name:            "Test Project 3",
			DeploymentsJSON: "{}",
		}

		err := project.AfterFind(db)
		require.NoError(t, err)

		// Deployments should be initialized as empty map
		deployments := project.GetDeploy()
		assert.NotNil(t, deployments)
		assert.Len(t, deployments, 0)
	})

	t.Run("handles invalid JSON gracefully", func(t *testing.T) {
		project := &Project{
			UUID:            "test-uuid-invalid",
			ID:              "test-project-invalid",
			Owner:           "user-invalid",
			Name:            "Test Project Invalid",
			DeploymentsJSON: "invalid json",
		}

		// AfterFind should return an error for invalid JSON
		err := project.AfterFind(db)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "invalid character")
	})
}

func TestProject_GetSetDeploy(t *testing.T) {
	t.Run("get and set deployments", func(t *testing.T) {
		project := &Project{
			UUID: "test-uuid",
			ID:   "test-project",
			Name: "Test Project",
		}

		// Initially should be nil
		deployments := project.GetDeploy()
		assert.Nil(t, deployments)

		// Set deployments
		testDeployments := map[string]Instance{
			"prod": {
				UUID:   "instance-prod",
				Name:   "Production",
				Status: "running",
			},
			"staging": {
				UUID:   "instance-staging",
				Name:   "Staging",
				Status: "stopped",
			},
		}
		project.SetDeploy(testDeployments)

		// Get deployments should return the same data
		retrievedDeployments := project.GetDeploy()
		assert.NotNil(t, retrievedDeployments)
		assert.Len(t, retrievedDeployments, 2)
		assert.Equal(t, "instance-prod", retrievedDeployments["prod"].UUID)
		assert.Equal(t, "Production", retrievedDeployments["prod"].Name)
		assert.Equal(t, "running", retrievedDeployments["prod"].Status)
	})

	t.Run("set nil deployments", func(t *testing.T) {
		project := &Project{
			UUID: "test-uuid-2",
			ID:   "test-project-2",
			Name: "Test Project 2",
		}

		// Set nil deployments
		project.SetDeploy(nil)

		// Get deployments should return nil
		deployments := project.GetDeploy()
		assert.Nil(t, deployments)
	})

	t.Run("set empty deployments", func(t *testing.T) {
		project := &Project{
			UUID: "test-uuid-3",
			ID:   "test-project-3",
			Name: "Test Project 3",
		}

		// Set empty deployments
		project.SetDeploy(make(map[string]Instance))

		// Get deployments should return empty map
		deployments := project.GetDeploy()
		assert.NotNil(t, deployments)
		assert.Len(t, deployments, 0)
	})
}

func TestProject_HookIntegration(t *testing.T) {
	t.Run("BeforeSave and AfterFind round-trip", func(t *testing.T) {
		// Create project with deployments
		originalProject := &Project{
			ID:    "integration-test",
			Owner: "user-integration",
			Name:  "Integration Test Project",
		}

		deployments := map[string]Instance{
			"prod": {
				UUID:   "instance-prod-integration",
				Name:   "Production Integration",
				Status: "running",
			},
			"staging": {
				UUID:   "instance-staging-integration",
				Name:   "Staging Integration",
				Status: "stopped",
			},
		}
		originalProject.SetDeploy(deployments)

		// Mock GORM DB
		db := &gorm.DB{}

		// Call BeforeSave hook
		err := originalProject.BeforeSave(db)
		require.NoError(t, err)

		// Verify UUID was generated
		assert.NotEmpty(t, originalProject.UUID)

		// Verify DeploymentsJSON was set
		assert.NotEmpty(t, originalProject.DeploymentsJSON)

		// Create a new project instance to simulate database retrieval
		retrievedProject := &Project{
			UUID:            originalProject.UUID,
			ID:              originalProject.ID,
			Owner:           originalProject.Owner,
			Name:            originalProject.Name,
			DeploymentsJSON: originalProject.DeploymentsJSON,
		}

		// Call AfterFind hook
		err = retrievedProject.AfterFind(db)
		require.NoError(t, err)

		// Verify deployments were deserialized correctly
		retrievedDeployments := retrievedProject.GetDeploy()
		assert.NotNil(t, retrievedDeployments)
		assert.Len(t, retrievedDeployments, 2)

		assert.Equal(t, "instance-prod-integration", retrievedDeployments["prod"].UUID)
		assert.Equal(t, "Production Integration", retrievedDeployments["prod"].Name)
		assert.Equal(t, "running", retrievedDeployments["prod"].Status)
		assert.Equal(t, "instance-staging-integration", retrievedDeployments["staging"].UUID)
		assert.Equal(t, "Staging Integration", retrievedDeployments["staging"].Name)
		assert.Equal(t, "stopped", retrievedDeployments["staging"].Status)
	})
}