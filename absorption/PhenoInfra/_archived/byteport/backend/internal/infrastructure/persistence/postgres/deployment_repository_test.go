package postgres

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/byteport/api/internal/domain/deployment"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDeploymentRepository_Create(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("creates deployment successfully", func(t *testing.T) {
		dep, err := deployment.NewDeployment("test-deployment", "user-123", nil)
		require.NoError(t, err)
		dep.SetEnvVar("KEY", "value")
		dep.SetProvider("aws", map[string]interface{}{"region": "us-east-1"})

		err = repo.Create(ctx, dep)
		require.NoError(t, err)

		// Verify it was created
		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		require.NotNil(t, found)
		assert.Equal(t, dep.UUID(), found.UUID())
		assert.Equal(t, dep.Name(), found.Name())
		assert.Equal(t, dep.Owner(), found.Owner())
		assert.Equal(t, dep.Status(), found.Status())
	})

	t.Run("creates deployment with services", func(t *testing.T) {
		dep, err := deployment.NewDeployment("svc-deployment", "user-456", nil)
		require.NoError(t, err)
		svc := deployment.DeploymentService{
			Name:     "web",
			Type:     "frontend",
			Provider: "aws",
			Status:   "running",
			URL:      "https://web.example.com",
		}
		require.NoError(t, dep.AddService(svc))

		err = repo.Create(ctx, dep)
		require.NoError(t, err)

		// Verify services persisted
		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		require.NotNil(t, found)
		assert.Len(t, found.Services(), 1)
		assert.Equal(t, "web", found.Services()[0].Name)
	})

	t.Run("handles duplicate UUID", func(t *testing.T) {
		dep1, err := deployment.NewDeployment("dep1", "user-789", nil)
		require.NoError(t, err)
		err = repo.Create(ctx, dep1)
		require.NoError(t, err)

		// Create another with same UUID (reconstruct to force UUID)
		dep2 := deployment.ReconstructDeployment(
			dep1.UUID(),
			"dep2",
			"user-999",
			nil,
			deployment.StatusPending,
			time.Now(),
			time.Now(),
			nil,
			nil,
		)

		err = repo.Create(ctx, dep2)
		assert.Error(t, err, "should fail on duplicate UUID")
	})
}

func TestDeploymentRepository_Update(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("updates deployment successfully", func(t *testing.T) {
		dep, err := deployment.NewDeployment("update-test", "user-123", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		// Update status (follow proper transition: Pending → Detecting)
		require.NoError(t, dep.SetStatus(deployment.StatusDetecting))
		dep.SetEnvVar("NEW_KEY", "new_value")

		err = repo.Update(ctx, dep)
		require.NoError(t, err)

		// Verify updates
		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		assert.Equal(t, deployment.StatusDetecting, found.Status())
		assert.Equal(t, "new_value", found.EnvVars()["NEW_KEY"])
	})

	t.Run("fails on non-existent deployment", func(t *testing.T) {
		dep, err := deployment.NewDeployment("non-existent", "user-456", nil)
		require.NoError(t, err)
		err = repo.Update(ctx, dep)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found")
	})

	t.Run("updates complex fields", func(t *testing.T) {
		dep, err := deployment.NewDeployment("complex-update", "user-789", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		// Add build config
		buildConfig := &deployment.BuildConfig{
			Framework:      "nodejs",
			BuildCommand:   "npm run build",
			StartCommand:   "npm start",
			InstallCommand: "npm install",
		}
		dep.SetBuildConfig(buildConfig)

		// Add cost info
		costInfo := &deployment.CostInfo{
			Monthly:   99.99,
			Breakdown: map[string]float64{"compute": 50.0, "storage": 49.99},
		}
		dep.SetCostInfo(costInfo)

		err = repo.Update(ctx, dep)
		require.NoError(t, err)

		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		assert.NotNil(t, found.BuildConfig())
		assert.Equal(t, "npm run build", found.BuildConfig().BuildCommand)
		assert.NotNil(t, found.CostInfo())
		assert.Equal(t, 99.99, found.CostInfo().Monthly)
	})
}

func TestDeploymentRepository_Delete(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("soft deletes deployment", func(t *testing.T) {
		dep, err := deployment.NewDeployment("delete-test", "user-123", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		err = repo.Delete(ctx, dep.UUID())
		require.NoError(t, err)

		// Should not find it anymore (soft deleted)
		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		assert.Nil(t, found, "soft deleted deployment should not be found")
	})

	t.Run("fails on non-existent deployment", func(t *testing.T) {
		err := repo.Delete(ctx, "non-existent-uuid")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found")
	})

	t.Run("cannot delete same deployment twice", func(t *testing.T) {
		dep, err := deployment.NewDeployment("double-delete", "user-456", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		err = repo.Delete(ctx, dep.UUID())
		require.NoError(t, err)

		err = repo.Delete(ctx, dep.UUID())
		assert.Error(t, err, "second delete should fail")
	})
}

func TestDeploymentRepository_FindByUUID(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("finds existing deployment", func(t *testing.T) {
		dep, err := deployment.NewDeployment("find-test", "user-123", nil)
		require.NoError(t, err)
		dep.SetEnvVar("TEST_VAR", "test_value")
		require.NoError(t, repo.Create(ctx, dep))

		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		require.NotNil(t, found)
		assert.Equal(t, dep.UUID(), found.UUID())
		assert.Equal(t, "test_value", found.EnvVars()["TEST_VAR"])
	})

	t.Run("returns nil for non-existent deployment", func(t *testing.T) {
		found, err := repo.FindByUUID(ctx, "non-existent-uuid")
		require.NoError(t, err)
		assert.Nil(t, found)
	})

	t.Run("reconstructs complex deployment correctly", func(t *testing.T) {
		dep, err := deployment.NewDeployment("complex-find", "user-456", nil)
		require.NoError(t, err)

		// Add multiple services
		svc1 := deployment.DeploymentService{
			Name:     "web",
			Type:     "frontend",
			Provider: "aws",
			Status:   "running",
			URL:      "https://web.example.com",
		}
		svc2 := deployment.DeploymentService{
			Name:     "api",
			Type:     "backend",
			Provider: "aws",
			Status:   "running",
			URL:      "https://api.example.com",
		}
		require.NoError(t, dep.AddService(svc1))
		require.NoError(t, dep.AddService(svc2))

		// Add providers
		dep.SetProvider("aws", map[string]interface{}{"region": "us-west-2"})
		dep.SetProvider("gcp", map[string]interface{}{"zone": "us-central1-a"})

		// Add env vars
		dep.SetEnvVar("DB_HOST", "localhost")
		dep.SetEnvVar("DB_PORT", "5432")

		require.NoError(t, repo.Create(ctx, dep))

		found, err := repo.FindByUUID(ctx, dep.UUID())
		require.NoError(t, err)
		require.NotNil(t, found)

		// Verify services
		assert.Len(t, found.Services(), 2)

		// Verify providers
		providers := found.Providers()
		assert.Len(t, providers, 2)
		assert.Contains(t, providers, "aws")
		assert.Contains(t, providers, "gcp")

		// Verify env vars
		assert.Equal(t, "localhost", found.EnvVars()["DB_HOST"])
		assert.Equal(t, "5432", found.EnvVars()["DB_PORT"])
	})
}

func TestDeploymentRepository_FindByOwner(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("finds all deployments for owner", func(t *testing.T) {
		owner := "user-owner-test"

		// Create multiple deployments for same owner
		dep1, err := deployment.NewDeployment("dep1", owner, nil)
		require.NoError(t, err)
		dep2, err := deployment.NewDeployment("dep2", owner, nil)
		require.NoError(t, err)
		dep3, err := deployment.NewDeployment("dep3", "other-user", nil)
		require.NoError(t, err)

		require.NoError(t, repo.Create(ctx, dep1))
		require.NoError(t, repo.Create(ctx, dep2))
		require.NoError(t, repo.Create(ctx, dep3))

		found, err := repo.FindByOwner(ctx, owner)
		require.NoError(t, err)
		assert.Len(t, found, 2)

		// Verify they're the right ones
		uuids := []string{found[0].UUID(), found[1].UUID()}
		assert.Contains(t, uuids, dep1.UUID())
		assert.Contains(t, uuids, dep2.UUID())
	})

	t.Run("returns empty slice for owner with no deployments", func(t *testing.T) {
		found, err := repo.FindByOwner(ctx, "no-deployments-user")
		require.NoError(t, err)
		assert.Empty(t, found)
	})
}

func TestDeploymentRepository_FindByProject(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("finds all deployments for project", func(t *testing.T) {
		projectUUID := "project-123"

		// Create deployments with project
		dep1 := deployment.ReconstructDeployment(
			"dep1",
			"deployment1",
			"user-123",
			&projectUUID,
			deployment.StatusPending,
			time.Now(),
			time.Now(),
			nil,
			nil,
		)
		dep2 := deployment.ReconstructDeployment(
			"dep2",
			"deployment2",
			"user-123",
			&projectUUID,
			deployment.StatusPending,
			time.Now(),
			time.Now(),
			nil,
			nil,
		)

		require.NoError(t, repo.Create(ctx, dep1))
		require.NoError(t, repo.Create(ctx, dep2))

		found, err := repo.FindByProject(ctx, projectUUID)
		require.NoError(t, err)
		assert.Len(t, found, 2)
	})

	t.Run("returns empty slice for project with no deployments", func(t *testing.T) {
		found, err := repo.FindByProject(ctx, "non-existent-project")
		require.NoError(t, err)
		assert.Empty(t, found)
	})
}

func TestDeploymentRepository_FindByStatus(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("finds all deployments with status", func(t *testing.T) {
		dep1, err := deployment.NewDeployment("running1", "user-123", nil)
		require.NoError(t, err)
		// Proper transition: Pending → Detecting
		require.NoError(t, dep1.SetStatus(deployment.StatusDetecting))

		dep2, err := deployment.NewDeployment("running2", "user-456", nil)
		require.NoError(t, err)
		// Proper transition: Pending → Detecting
		require.NoError(t, dep2.SetStatus(deployment.StatusDetecting))

		dep3, err := deployment.NewDeployment("pending", "user-789", nil)
		require.NoError(t, err)
		// dep3 stays in pending status

		require.NoError(t, repo.Create(ctx, dep1))
		require.NoError(t, repo.Create(ctx, dep2))
		require.NoError(t, repo.Create(ctx, dep3))

		found, err := repo.FindByStatus(ctx, deployment.StatusDetecting)
		require.NoError(t, err)
		assert.Len(t, found, 2)

		for _, dep := range found {
			assert.Equal(t, deployment.StatusDetecting, dep.Status())
		}
	})

	t.Run("returns empty slice for status with no deployments", func(t *testing.T) {
		found, err := repo.FindByStatus(ctx, deployment.StatusFailed)
		require.NoError(t, err)
		assert.Empty(t, found)
	})
}

func TestDeploymentRepository_List(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("lists deployments with pagination", func(t *testing.T) {
		// Create 5 deployments
		for i := 0; i < 5; i++ {
			dep, err := deployment.NewDeployment(fmt.Sprintf("list-test-%d", i), "user-123", nil)
			require.NoError(t, err)
			require.NoError(t, repo.Create(ctx, dep))
			time.Sleep(10 * time.Millisecond) // Ensure different timestamps
		}

		// Get first page
		page1, err := repo.List(ctx, 0, 2)
		require.NoError(t, err)
		assert.Len(t, page1, 2)

		// Get second page
		page2, err := repo.List(ctx, 2, 2)
		require.NoError(t, err)
		assert.Len(t, page2, 2)

		// Get third page
		page3, err := repo.List(ctx, 4, 2)
		require.NoError(t, err)
		assert.Len(t, page3, 1)

		// Verify they're different
		assert.NotEqual(t, page1[0].UUID(), page2[0].UUID())
	})

	t.Run("orders by created_at DESC", func(t *testing.T) {
		// Create deployments with slight delays
		dep1, err := deployment.NewDeployment("order-1", "user-456", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep1))
		time.Sleep(50 * time.Millisecond)

		dep2, err := deployment.NewDeployment("order-2", "user-456", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep2))
		time.Sleep(50 * time.Millisecond)

		dep3, err := deployment.NewDeployment("order-3", "user-456", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep3))

		// List all
		deployments, err := repo.List(ctx, 0, 10)
		require.NoError(t, err)
		require.GreaterOrEqual(t, len(deployments), 3)

		// Most recent should be first
		assert.Equal(t, dep3.UUID(), deployments[0].UUID())
		assert.Equal(t, dep2.UUID(), deployments[1].UUID())
		assert.Equal(t, dep1.UUID(), deployments[2].UUID())
	})

	t.Run("returns empty slice when offset exceeds count", func(t *testing.T) {
		deployments, err := repo.List(ctx, 1000, 10)
		require.NoError(t, err)
		assert.Empty(t, deployments)
	})
}

func TestDeploymentRepository_Count(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("counts all deployments", func(t *testing.T) {
		initialCount, err := repo.Count(ctx)
		require.NoError(t, err)

		// Create deployments
		for i := 0; i < 3; i++ {
			dep, err := deployment.NewDeployment(fmt.Sprintf("count-test-%d", i), "user-123", nil)
			require.NoError(t, err)
			require.NoError(t, repo.Create(ctx, dep))
		}

		newCount, err := repo.Count(ctx)
		require.NoError(t, err)
		assert.Equal(t, initialCount+3, newCount)
	})

	t.Run("does not count soft-deleted deployments", func(t *testing.T) {
		dep, err := deployment.NewDeployment("count-delete", "user-456", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		countBefore, err := repo.Count(ctx)
		require.NoError(t, err)

		require.NoError(t, repo.Delete(ctx, dep.UUID()))

		countAfter, err := repo.Count(ctx)
		require.NoError(t, err)
		assert.Equal(t, countBefore-1, countAfter)
	})
}

func TestDeploymentRepository_CountByOwner(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("counts deployments by owner", func(t *testing.T) {
		owner := "user-count-owner"

		// Create deployments for this owner
		for i := 0; i < 4; i++ {
			dep, err := deployment.NewDeployment(fmt.Sprintf("owner-count-%d", i), owner, nil)
			require.NoError(t, err)
			require.NoError(t, repo.Create(ctx, dep))
		}

		// Create deployment for different owner
		otherDep, err := deployment.NewDeployment("other-owner-dep", "other-user", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, otherDep))

		count, err := repo.CountByOwner(ctx, owner)
		require.NoError(t, err)
		assert.Equal(t, int64(4), count)
	})

	t.Run("returns zero for owner with no deployments", func(t *testing.T) {
		count, err := repo.CountByOwner(ctx, "no-deployments-owner")
		require.NoError(t, err)
		assert.Equal(t, int64(0), count)
	})
}

func TestDeploymentRepository_ConcurrentAccess(t *testing.T) {
	testDB := setupTestDB(t)
	if testDB.Container == nil {
		t.Skip("skipping concurrency test when running against in-memory database")
	}
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	t.Run("handles concurrent creates", func(t *testing.T) {
		const concurrency = 10
		errChan := make(chan error, concurrency)

		for i := 0; i < concurrency; i++ {
			go func(id int) {
				dep, err := deployment.NewDeployment(fmt.Sprintf("concurrent-%d", id), fmt.Sprintf("user-%d", id), nil)
				if err != nil {
					errChan <- err
					return
				}
				errChan <- repo.Create(ctx, dep)
			}(i)
		}

		// Collect results
		for i := 0; i < concurrency; i++ {
			err := <-errChan
			assert.NoError(t, err)
		}
	})
}
