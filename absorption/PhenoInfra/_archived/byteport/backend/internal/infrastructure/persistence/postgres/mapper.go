package postgres

import (
	"encoding/json"
	"fmt"

	"github.com/byteport/api/internal/domain/deployment"
)

var jsonMarshal = json.Marshal

// DomainToModel converts a domain entity to a GORM model
func DomainToModel(dep *deployment.Deployment) (*DeploymentModel, error) {
	model := &DeploymentModel{
		UUID:         dep.UUID(),
		Name:         dep.Name(),
		Owner:        dep.Owner(),
		ProjectUUID:  dep.ProjectUUID(),
		Status:       dep.Status().String(),
		CreatedAt:    dep.CreatedAt(),
		UpdatedAt:    dep.UpdatedAt(),
		DeployedAt:   dep.DeployedAt(),
		TerminatedAt: dep.TerminatedAt(),
	}

	// Marshal providers map to JSON (use null for empty)
	if providers := dep.Providers(); len(providers) > 0 {
		providersJSON, err := jsonMarshal(providers)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal providers: %w", err)
		}
		model.Providers = string(providersJSON)
	} else {
		model.Providers = "null"
	}

	// Marshal services to JSON (use null for empty)
	if services := dep.Services(); len(services) > 0 {
		servicesJSON, err := jsonMarshal(services)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal services: %w", err)
		}
		model.Services = string(servicesJSON)
	} else {
		model.Services = "null"
	}

	// Marshal env vars to JSON (use null for empty)
	if envVars := dep.EnvVars(); len(envVars) > 0 {
		envVarsJSON, err := jsonMarshal(envVars)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal env vars: %w", err)
		}
		model.EnvVars = string(envVarsJSON)
	} else {
		model.EnvVars = "null"
	}

	// Marshal build config to JSON (use null for nil)
	if buildConfig := dep.BuildConfig(); buildConfig != nil {
		buildConfigJSON, err := jsonMarshal(buildConfig)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal build config: %w", err)
		}
		model.BuildConfig = string(buildConfigJSON)
	} else {
		model.BuildConfig = "null"
	}

	// Marshal cost info to JSON (use null for nil)
	if costInfo := dep.CostInfo(); costInfo != nil {
		costInfoJSON, err := jsonMarshal(costInfo)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal cost info: %w", err)
		}
		model.CostInfo = string(costInfoJSON)
	} else {
		model.CostInfo = "null"
	}

	return model, nil
}

// ModelToDomain converts a GORM model to a domain entity
func ModelToDomain(model *DeploymentModel) (*deployment.Deployment, error) {
	// Reconstruct the deployment entity from persistence
	status := deployment.Status(model.Status)
	dep := deployment.ReconstructDeployment(
		model.UUID,
		model.Name,
		model.Owner,
		model.ProjectUUID,
		status,
		model.CreatedAt,
		model.UpdatedAt,
		model.DeployedAt,
		model.TerminatedAt,
	)

	// Unmarshal providers (skip if null or empty)
	if model.Providers != "" && model.Providers != "null" {
		var providers map[string]interface{}
		if err := json.Unmarshal([]byte(model.Providers), &providers); err != nil {
			return nil, fmt.Errorf("failed to unmarshal providers: %w", err)
		}
		for provider, config := range providers {
			dep.SetProvider(provider, config)
		}
	}

	// Unmarshal services (skip if null or empty)
	if model.Services != "" && model.Services != "null" {
		var services []deployment.DeploymentService
		if err := json.Unmarshal([]byte(model.Services), &services); err != nil {
			return nil, fmt.Errorf("failed to unmarshal services: %w", err)
		}
		for _, svc := range services {
			if err := dep.AddService(svc); err != nil {
				return nil, fmt.Errorf("failed to add service: %w", err)
			}
		}
	}

	// Unmarshal env vars (skip if null or empty)
	if model.EnvVars != "" && model.EnvVars != "null" {
		var envVars map[string]string
		if err := json.Unmarshal([]byte(model.EnvVars), &envVars); err != nil {
			return nil, fmt.Errorf("failed to unmarshal env vars: %w", err)
		}
		for key, value := range envVars {
			dep.SetEnvVar(key, value)
		}
	}

	// Unmarshal build config (skip if null or empty)
	if model.BuildConfig != "" && model.BuildConfig != "null" {
		var buildConfig deployment.BuildConfig
		if err := json.Unmarshal([]byte(model.BuildConfig), &buildConfig); err != nil {
			return nil, fmt.Errorf("failed to unmarshal build config: %w", err)
		}
		dep.SetBuildConfig(&buildConfig)
	}

	// Unmarshal cost info (skip if null or empty)
	if model.CostInfo != "" && model.CostInfo != "null" {
		var costInfo deployment.CostInfo
		if err := json.Unmarshal([]byte(model.CostInfo), &costInfo); err != nil {
			return nil, fmt.Errorf("failed to unmarshal cost info: %w", err)
		}
		dep.SetCostInfo(&costInfo)
	}

	return dep, nil
}
