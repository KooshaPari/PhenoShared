package postgres

import (
	"errors"
	"math"
	"testing"
	"time"

	"github.com/byteport/api/internal/domain/deployment"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDomainToModel_ErrorOnUnmarshalableProvider(t *testing.T) {
	dep, err := deployment.NewDeployment("bad-providers", "owner", nil)
	require.NoError(t, err)

	// Inject a value the JSON encoder cannot handle to force the error branch.
	dep.SetProvider("invalid", make(chan int))

	_, err = DomainToModel(dep)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "providers")
}

func TestDomainToModel_ErrorOnCostInfo(t *testing.T) {
	dep, err := deployment.NewDeployment("bad-cost", "owner", nil)
	require.NoError(t, err)

	dep.SetCostInfo(&deployment.CostInfo{
		Monthly:   math.NaN(),
		Breakdown: map[string]float64{"compute": math.NaN()},
	})

	_, err = DomainToModel(dep)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "cost info")
}

func TestDomainToModel_ErrorOnServicesMarshal(t *testing.T) {
	dep, err := deployment.NewDeployment("bad-services", "owner", nil)
	require.NoError(t, err)
	require.NoError(t, dep.AddService(deployment.DeploymentService{Name: "svc", Type: "type", Provider: "aws"}))

	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		switch v.(type) {
		case []deployment.DeploymentService:
			return nil, errors.New("marshal services failed")
		default:
			return original(v)
		}
	}
	t.Cleanup(func() { jsonMarshal = original })

	_, err = DomainToModel(dep)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "services")
}

func TestDomainToModel_ErrorOnEnvVarsMarshal(t *testing.T) {
	dep, err := deployment.NewDeployment("bad-env", "owner", nil)
	require.NoError(t, err)
	dep.SetEnvVar("KEY", "value")

	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		switch v.(type) {
		case map[string]string:
			return nil, errors.New("marshal env failed")
		default:
			return original(v)
		}
	}
	t.Cleanup(func() { jsonMarshal = original })

	_, err = DomainToModel(dep)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "env vars")
}

func TestDomainToModel_ErrorOnBuildConfigMarshal(t *testing.T) {
	dep, err := deployment.NewDeployment("bad-build", "owner", nil)
	require.NoError(t, err)
	dep.SetBuildConfig(&deployment.BuildConfig{Framework: "go"})

	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		switch v.(type) {
		case *deployment.BuildConfig:
			return nil, errors.New("marshal build failed")
		default:
			return original(v)
		}
	}
	t.Cleanup(func() { jsonMarshal = original })

	_, err = DomainToModel(dep)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "build config")
}

func TestDomainToModel_AssignsNullsForEmptyCollections(t *testing.T) {
	dep, err := deployment.NewDeployment("empty", "owner", nil)
	require.NoError(t, err)

	model, err := DomainToModel(dep)
	require.NoError(t, err)

	assert.Equal(t, "null", model.Providers)
	assert.Equal(t, "null", model.Services)
	assert.Equal(t, "null", model.EnvVars)
	assert.Equal(t, "null", model.BuildConfig)
	assert.Equal(t, "null", model.CostInfo)
}

func TestModelToDomain_ErrorPaths(t *testing.T) {
	now := time.Now()
	base := DeploymentModel{
		UUID:      "uuid",
		Name:      "name",
		Owner:     "owner",
		Status:    deployment.StatusPending.String(),
		CreatedAt: now,
		UpdatedAt: now,
	}

	tests := []struct {
		name    string
		mutate  func(m *DeploymentModel)
		wantErr string
	}{
		{
			name: "invalid providers JSON",
			mutate: func(m *DeploymentModel) {
				m.Providers = "{"
			},
			wantErr: "providers",
		},
		{
			name: "invalid services JSON",
			mutate: func(m *DeploymentModel) {
				m.Services = "{"
			},
			wantErr: "services",
		},
		{
			name: "invalid env vars JSON",
			mutate: func(m *DeploymentModel) {
				m.EnvVars = "{"
			},
			wantErr: "env vars",
		},
		{
			name: "invalid build config JSON",
			mutate: func(m *DeploymentModel) {
				m.BuildConfig = "{"
			},
			wantErr: "build config",
		},
		{
			name: "invalid cost info JSON",
			mutate: func(m *DeploymentModel) {
				m.CostInfo = "{"
			},
			wantErr: "cost info",
		},
		{
			name: "duplicate services decode",
			mutate: func(m *DeploymentModel) {
				m.Services = `[{"name":"svc","type":"type","provider":"aws"},{"name":"svc","type":"type","provider":"aws"}]`
			},
			wantErr: "add service",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			model := base
			tt.mutate(&model)

			_, err := ModelToDomain(&model)
			require.Error(t, err)
			assert.Contains(t, err.Error(), tt.wantErr)
		})
	}
}
