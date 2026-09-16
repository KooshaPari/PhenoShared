package deployment

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDeployment_Getters(t *testing.T) {
	// Test Providers()
	deployment, err := NewDeployment("test-app", "test-user", nil)
	require.NoError(t, err)

	providers := deployment.Providers()
	assert.NotNil(t, providers)
	assert.Empty(t, providers)

	// Test CostInfo()
	costInfo := deployment.CostInfo()
	assert.Nil(t, costInfo)

	// Test CreatedAt()
	createdAt := deployment.CreatedAt()
	assert.False(t, createdAt.IsZero())

	// Test UpdatedAt()
	updatedAt := deployment.UpdatedAt()
	assert.False(t, updatedAt.IsZero())

	// Test ProjectUUID()
	projectUUID := deployment.ProjectUUID()
	assert.Nil(t, projectUUID)

	// Test BuildConfig()
	buildConfig := deployment.BuildConfig()
	assert.Nil(t, buildConfig)
}

func TestDeployment_Setters(t *testing.T) {
	deployment, err := NewDeployment("test-app", "test-user", nil)
	require.NoError(t, err)

	originalUpdatedAt := deployment.UpdatedAt()

	// Small delay to ensure different timestamp
	time.Sleep(time.Millisecond)

	// Test SetProvider()
	config := map[string]interface{}{
		"region": "us-west-2",
		"type":   "t3.micro",
	}
	deployment.SetProvider("aws", config)

	providers := deployment.Providers()
	assert.Contains(t, providers, "aws")
	assert.Equal(t, config, providers["aws"])
	assert.True(t, deployment.UpdatedAt().After(originalUpdatedAt))

	// Test SetBuildConfig()
	buildConfig := &BuildConfig{
		Framework:    "react",
		BuildCommand: "npm run build",
	}
	deployment.SetBuildConfig(buildConfig)

	retrievedConfig := deployment.BuildConfig()
	assert.Equal(t, buildConfig, retrievedConfig)
	assert.Equal(t, "react", retrievedConfig.Framework)
}

func TestDeployment_WithProjectUUID(t *testing.T) {
	projectUUID := "project-123"
	deployment, err := NewDeployment("test-app", "test-user", &projectUUID)
	require.NoError(t, err)

	retrievedUUID := deployment.ProjectUUID()
	assert.NotNil(t, retrievedUUID)
	assert.Equal(t, projectUUID, *retrievedUUID)
}