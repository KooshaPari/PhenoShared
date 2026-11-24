package postgres

import (
	"context"
	"testing"

	"github.com/byteport/api/internal/domain/deployment"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDeploymentRepository_Create_Errors(t *testing.T) {
	ctx := context.Background()

	t.Run("returns error when domain conversion fails", func(t *testing.T) {
		testDB := setupTestDB(t)
		require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

		repo := NewDeploymentRepository(testDB.DB)

		dep, err := deployment.NewDeployment("invalid", "owner", nil)
		require.NoError(t, err)
		dep.SetProvider("bad", make(chan int)) // forces JSON marshal failure

		err = repo.Create(ctx, dep)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "failed to convert to model")
	})

	t.Run("returns error when database insert fails", func(t *testing.T) {
		testDB := setupTestDB(t)
		require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

		sqlDB, err := testDB.DB.DB()
		require.NoError(t, err)
		require.NoError(t, sqlDB.Close())

		repo := NewDeploymentRepository(testDB.DB)

		dep, err := deployment.NewDeployment("db-error", "owner", nil)
		require.NoError(t, err)

		err = repo.Create(ctx, dep)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "failed to create deployment")
	})
}

func TestDeploymentRepository_Update_Errors(t *testing.T) {
	ctx := context.Background()

	t.Run("returns error when domain conversion fails", func(t *testing.T) {
		testDB := setupTestDB(t)
		require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

		repo := NewDeploymentRepository(testDB.DB)

		dep, err := deployment.NewDeployment("update-invalid", "owner", nil)
		require.NoError(t, err)
		// First create valid deployment
		require.NoError(t, repo.Create(ctx, dep))

		// Inject invalid provider to force marshal error during update
		dep.SetProvider("bad", make(chan int))

		err = repo.Update(ctx, dep)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "failed to convert to model")
	})

	t.Run("returns error when database update fails", func(t *testing.T) {
		testDB := setupTestDB(t)
		require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

		repo := NewDeploymentRepository(testDB.DB)

		dep, err := deployment.NewDeployment("update-db-error", "owner", nil)
		require.NoError(t, err)
		require.NoError(t, repo.Create(ctx, dep))

		sqlDB, err := testDB.DB.DB()
		require.NoError(t, err)
		require.NoError(t, sqlDB.Close())

		err = repo.Update(ctx, dep)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "failed to update deployment")
	})
}

func TestDeploymentRepository_Delete_DBError(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	dep, err := deployment.NewDeployment("delete-db-error", "owner", nil)
	require.NoError(t, err)
	require.NoError(t, repo.Create(ctx, dep))

	sqlDB, err := testDB.DB.DB()
	require.NoError(t, err)
	require.NoError(t, sqlDB.Close())

	err = repo.Delete(ctx, dep.UUID())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to delete deployment")
}

func TestDeploymentRepository_ReadMethods_DBError(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	// Prepare some data
	dep, err := deployment.NewDeployment("read-db-error", "owner", nil)
	require.NoError(t, err)
	require.NoError(t, repo.Create(ctx, dep))

	sqlDB, err := testDB.DB.DB()
	require.NoError(t, err)
	require.NoError(t, sqlDB.Close())

	_, err = repo.FindByUUID(ctx, dep.UUID())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to find deployment")

	_, err = repo.FindByOwner(ctx, dep.Owner())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to find deployments by owner")

	_, err = repo.FindByProject(ctx, "proj")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to find deployments by project")

	_, err = repo.FindByStatus(ctx, deployment.StatusPending)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to find deployments by status")

	_, err = repo.List(ctx, 0, 10)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to list deployments")

	_, err = repo.Count(ctx)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to count deployments")

	_, err = repo.CountByOwner(ctx, dep.Owner())
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to count deployments by owner")
}

func TestDeploymentRepository_ModelConversionErrors(t *testing.T) {
	testDB := setupTestDB(t)
	require.NoError(t, testDB.MigrateModels(&DeploymentModel{}))

	repo := NewDeploymentRepository(testDB.DB)
	ctx := context.Background()

	project := "project-uuid"
	model := DeploymentModel{
		UUID:        "invalid-uuid",
		Name:        "invalid",
		Owner:       "owner",
		ProjectUUID: &project,
		Status:      deployment.StatusPending.String(),
		Providers:   "{",
	}
	require.NoError(t, testDB.DB.Create(&model).Error)

	_, err := repo.FindByUUID(ctx, model.UUID)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to convert to domain")

	_, err = repo.FindByOwner(ctx, model.Owner)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to convert to domain")

	_, err = repo.FindByProject(ctx, project)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to convert to domain")

	_, err = repo.FindByStatus(ctx, deployment.StatusPending)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to convert to domain")

	_, err = repo.List(ctx, 0, 5)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to convert to domain")

	// Count functions still operate on the raw table and should succeed.
	total, err := repo.Count(ctx)
	require.NoError(t, err)
	assert.Equal(t, int64(1), total)

	ownerCount, err := repo.CountByOwner(ctx, model.Owner)
	require.NoError(t, err)
	assert.Equal(t, int64(1), ownerCount)
}
