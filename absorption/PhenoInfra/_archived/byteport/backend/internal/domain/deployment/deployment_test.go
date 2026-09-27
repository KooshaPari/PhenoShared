package deployment

import (
	"strings"
	"testing"
	"time"
)

func TestNewDeployment(t *testing.T) {
	tests := []struct {
		name        string
		depName     string
		owner       string
		projectUUID *string
		wantErr     bool
	}{
		{
			name:        "valid deployment",
			depName:     "test-deployment",
			owner:       "user-123",
			projectUUID: nil,
			wantErr:     false,
		},
		{
			name:        "empty name",
			depName:     "",
			owner:       "user-123",
			projectUUID: nil,
			wantErr:     true,
		},
		{
			name:        "empty owner",
			depName:     "test-deployment",
			owner:       "",
			projectUUID: nil,
			wantErr:     true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dep, err := NewDeployment(tt.depName, tt.owner, tt.projectUUID)

			if tt.wantErr {
				if err == nil {
					t.Errorf("NewDeployment() error = nil, wantErr %v", tt.wantErr)
				}
				return
			}

			if err != nil {
				t.Errorf("NewDeployment() unexpected error = %v", err)
				return
			}

			if dep.Name() != tt.depName {
				t.Errorf("Name() = %v, want %v", dep.Name(), tt.depName)
			}

			if dep.Owner() != tt.owner {
				t.Errorf("Owner() = %v, want %v", dep.Owner(), tt.owner)
			}

			if dep.Status() != StatusPending {
				t.Errorf("Status() = %v, want %v", dep.Status(), StatusPending)
			}

			if dep.UUID() == "" {
				t.Error("UUID() should not be empty")
			}
		})
	}
}

func TestDeployment_StatusTransitions(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	tests := []struct {
		name       string
		fromStatus Status
		toStatus   Status
		wantErr    bool
	}{
		{"pending to detecting", StatusPending, StatusDetecting, false},
		{"detecting to provisioning", StatusDetecting, StatusProvisioning, false},
		{"provisioning to deploying", StatusProvisioning, StatusDeploying, false},
		{"deploying to deployed", StatusDeploying, StatusDeployed, false},
		{"deployed to terminated", StatusDeployed, StatusTerminated, false},
		{"pending to deployed (invalid)", StatusPending, StatusDeployed, true},
		{"terminated to deploying (invalid)", StatusTerminated, StatusDeploying, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Reset to from status
			dep, _ = NewDeployment("test", "owner", nil)
			// Chain transitions to reach fromStatus
			if tt.fromStatus == StatusDetecting {
				_ = dep.SetStatus(StatusDetecting)
			} else if tt.fromStatus == StatusProvisioning {
				_ = dep.SetStatus(StatusDetecting)
				_ = dep.SetStatus(StatusProvisioning)
			} else if tt.fromStatus == StatusDeploying {
				_ = dep.SetStatus(StatusDetecting)
				_ = dep.SetStatus(StatusProvisioning)
				_ = dep.SetStatus(StatusDeploying)
			} else if tt.fromStatus == StatusDeployed {
				_ = dep.SetStatus(StatusDetecting)
				_ = dep.SetStatus(StatusProvisioning)
				_ = dep.SetStatus(StatusDeploying)
				_ = dep.SetStatus(StatusDeployed)
			} else if tt.fromStatus == StatusTerminated {
				_ = dep.SetStatus(StatusTerminated)
			}
			// fromStatus is now set properly

			err := dep.SetStatus(tt.toStatus)

			if tt.wantErr {
				if err == nil {
					t.Errorf("SetStatus() error = nil, wantErr %v", tt.wantErr)
				}
			} else {
				if err != nil {
					t.Errorf("SetStatus() unexpected error = %v", err)
				}
				if dep.Status() != tt.toStatus {
					t.Errorf("Status() = %v, want %v", dep.Status(), tt.toStatus)
				}
			}
		})
	}
}

func TestDeployment_SetStatus_Timestamps(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	// Test deployed timestamp
	_ = dep.SetStatus(StatusDetecting)
	_ = dep.SetStatus(StatusProvisioning)
	_ = dep.SetStatus(StatusDeploying)

	beforeDeploy := time.Now().UTC()
	_ = dep.SetStatus(StatusDeployed)
	afterDeploy := time.Now().UTC()

	if dep.DeployedAt() == nil {
		t.Error("DeployedAt() should not be nil after StatusDeployed")
	} else {
		if dep.DeployedAt().Before(beforeDeploy) || dep.DeployedAt().After(afterDeploy) {
			t.Error("DeployedAt() timestamp is out of expected range")
		}
	}

	// Test terminated timestamp
	beforeTerminate := time.Now().UTC()
	_ = dep.SetStatus(StatusTerminated)
	afterTerminate := time.Now().UTC()

	if dep.TerminatedAt() == nil {
		t.Error("TerminatedAt() should not be nil after StatusTerminated")
	} else {
		if dep.TerminatedAt().Before(beforeTerminate) || dep.TerminatedAt().After(afterTerminate) {
			t.Error("TerminatedAt() timestamp is out of expected range")
		}
	}
}

func TestDeployment_AddService(t *testing.T) {
	tests := []struct {
		name    string
		service DeploymentService
		wantErr bool
	}{
		{
			name: "valid service",
			service: DeploymentService{
				Name:     "frontend",
				Type:     "frontend",
				Provider: "vercel",
				Status:   "pending",
			},
			wantErr: false,
		},
		{
			name: "empty name",
			service: DeploymentService{
				Name:     "",
				Type:     "frontend",
				Provider: "vercel",
			},
			wantErr: true,
		},
		{
			name: "empty type",
			service: DeploymentService{
				Name:     "frontend",
				Type:     "",
				Provider: "vercel",
			},
			wantErr: true,
		},
		{
			name: "empty provider",
			service: DeploymentService{
				Name:     "frontend",
				Type:     "frontend",
				Provider: "",
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dep, _ := NewDeployment("test", "owner", nil)
			err := dep.AddService(tt.service)

			if tt.wantErr {
				if err == nil {
					t.Errorf("AddService() error = nil, wantErr %v", tt.wantErr)
				}
			} else {
				if err != nil {
					t.Errorf("AddService() unexpected error = %v", err)
				}
				services := dep.Services()
				if len(services) != 1 {
					t.Errorf("Services() length = %v, want 1", len(services))
				}
			}
		})
	}
}

func TestDeployment_AddService_Duplicate(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	service := DeploymentService{
		Name:     "frontend",
		Type:     "frontend",
		Provider: "vercel",
	}

	err := dep.AddService(service)
	if err != nil {
		t.Fatalf("AddService() first call failed: %v", err)
	}

	// Try to add duplicate
	err = dep.AddService(service)
	if err == nil {
		t.Error("AddService() should fail for duplicate service name")
	}
}

func TestDeployment_RemoveService(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	service := DeploymentService{
		Name:     "frontend",
		Type:     "frontend",
		Provider: "vercel",
	}

	_ = dep.AddService(service)

	// Remove existing service
	err := dep.RemoveService("frontend")
	if err != nil {
		t.Errorf("RemoveService() unexpected error = %v", err)
	}

	if len(dep.Services()) != 0 {
		t.Errorf("Services() length = %v, want 0", len(dep.Services()))
	}

	// Try to remove non-existent service
	err = dep.RemoveService("backend")
	if err == nil {
		t.Error("RemoveService() should fail for non-existent service")
	}
}

func TestDeployment_SetEnvVar(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	dep.SetEnvVar("API_KEY", "secret-key")
	dep.SetEnvVar("DB_URL", "postgres://...")

	envVars := dep.EnvVars()
	if len(envVars) != 2 {
		t.Errorf("EnvVars() length = %v, want 2", len(envVars))
	}

	if envVars["API_KEY"] != "secret-key" {
		t.Errorf("EnvVars()[API_KEY] = %v, want 'secret-key'", envVars["API_KEY"])
	}
}

func TestDeployment_CalculateTotalCost(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	// No cost info
	if dep.CalculateTotalCost() != 0.0 {
		t.Errorf("CalculateTotalCost() = %v, want 0.0", dep.CalculateTotalCost())
	}

	// With cost info
	costInfo := &CostInfo{
		Monthly: 0.0, // Will be calculated
		Breakdown: map[string]float64{
			"vercel": 0.0,
			"render": 7.0,
			"neon":   0.0,
		},
	}
	dep.SetCostInfo(costInfo)

	expectedTotal := 7.0
	if dep.CalculateTotalCost() != expectedTotal {
		t.Errorf("CalculateTotalCost() = %v, want %v", dep.CalculateTotalCost(), expectedTotal)
	}
}

func TestDeployment_IsActive(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	// Pending - not active
	if dep.IsActive() {
		t.Error("IsActive() = true for pending deployment, want false")
	}

	// Deploying - active
	_ = dep.SetStatus(StatusDetecting)
	_ = dep.SetStatus(StatusProvisioning)
	_ = dep.SetStatus(StatusDeploying)
	if !dep.IsActive() {
		t.Error("IsActive() = false for deploying deployment, want true")
	}

	// Deployed - active
	_ = dep.SetStatus(StatusDeployed)
	if !dep.IsActive() {
		t.Error("IsActive() = false for deployed deployment, want true")
	}

	// Terminated - not active
	_ = dep.SetStatus(StatusTerminated)
	if dep.IsActive() {
		t.Error("IsActive() = true for terminated deployment, want false")
	}
}

func TestDeployment_IsFailed(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	if dep.IsFailed() {
		t.Error("IsFailed() = true for pending deployment, want false")
	}

	_ = dep.SetStatus(StatusFailed)
	if !dep.IsFailed() {
		t.Error("IsFailed() = false for failed deployment, want true")
	}
}

func TestDeployment_IsTerminated(t *testing.T) {
	dep, _ := NewDeployment("test", "owner", nil)

	if dep.IsTerminated() {
		t.Error("IsTerminated() = true for pending deployment, want false")
	}

	_ = dep.SetStatus(StatusTerminated)
	if !dep.IsTerminated() {
		t.Error("IsTerminated() = false for terminated deployment, want true")
	}
}

func TestDeployment_Validate(t *testing.T) {
	tests := []struct {
		name    string
		setup   func() *Deployment
		wantErr bool
		errMsg   string
	}{
		{
			name: "valid deployment",
			setup: func() *Deployment {
				dep, _ := NewDeployment("test", "owner", nil)
				return dep
			},
			wantErr: false,
		},
		{
			name: "reconstructed valid deployment",
			setup: func() *Deployment {
				return ReconstructDeployment(
					"uuid-123",
					"test",
					"owner",
					nil,
					StatusPending,
					time.Now().UTC(),
					time.Now().UTC(),
					nil,
					nil,
				)
			},
			wantErr: false,
		},
		{
			name: "empty uuid",
			setup: func() *Deployment {
				dep := ReconstructDeployment(
					"",
					"test",
					"owner",
					nil,
					StatusPending,
					time.Now().UTC(),
					time.Now().UTC(),
					nil,
					nil,
				)
				return dep
			},
			wantErr: true,
			errMsg:   "UUID cannot be empty",
		},
		{
			name: "empty name",
			setup: func() *Deployment {
				dep := ReconstructDeployment(
					"uuid-123",
					"",
					"owner",
					nil,
					StatusPending,
					time.Now().UTC(),
					time.Now().UTC(),
					nil,
					nil,
				)
				return dep
			},
			wantErr: true,
			errMsg:   "name cannot be empty",
		},
		{
			name: "empty owner",
			setup: func() *Deployment {
				dep := ReconstructDeployment(
					"uuid-123",
					"test",
					"",
					nil,
					StatusPending,
					time.Now().UTC(),
					time.Now().UTC(),
					nil,
					nil,
				)
				return dep
			},
			wantErr: true,
			errMsg:   "owner cannot be empty",
		},
		{
			name: "invalid status",
			setup: func() *Deployment {
				dep := ReconstructDeployment(
					"uuid-123",
					"test",
					"owner",
					nil,
					Status("invalid-status"),
					time.Now().UTC(),
					time.Now().UTC(),
					nil,
					nil,
				)
				return dep
			},
			wantErr: true,
			errMsg:   "invalid deployment status",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dep := tt.setup()
			err := dep.Validate()

			if tt.wantErr {
				if err == nil {
					t.Errorf("Validate() error = nil, wantErr %v", tt.wantErr)
				}
				if tt.errMsg != "" && err != nil && !strings.Contains(strings.ToLower(err.Error()), strings.ToLower(tt.errMsg)) {
					t.Errorf("Validate() error message should contain '%s', got '%s'", tt.errMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("Validate() unexpected error = %v", err)
				}
			}
		})
	}
}

// TestDeployment_SetEnvVar_NilMap tests env var setting with nil map
func TestDeployment_SetEnvVar_NilMap(t *testing.T) {
	dep := ReconstructDeployment(
		"uuid-123",
		"test",
		"owner",
		nil,
		StatusPending,
		time.Now().UTC(),
		time.Now().UTC(),
		nil,
		nil,
	)
	// Ensure envVars is nil
	dep.envVars = nil
	
	// Should initialize the map
	dep.SetEnvVar("TEST_KEY", "test_value")
	
	if dep.EnvVars() == nil {
		t.Error("EnvVars() should not be nil after SetEnvVar")
	}
	
	if len(dep.EnvVars()) != 1 {
		t.Errorf("EnvVars() length = %d, want 1", len(dep.EnvVars()))
	}
	
	if dep.EnvVars()["TEST_KEY"] != "test_value" {
		t.Errorf("EnvVars()[TEST_KEY] = %s, want 'test_value'", dep.EnvVars()["TEST_KEY"])
	}
}

func TestReconstructDeployment(t *testing.T) {
	uuid := "uuid-123"
	name := "test-deployment"
	owner := "owner-456"
	status := StatusDeployed
	now := time.Now().UTC()
	deployedAt := time.Now().UTC()

	dep := ReconstructDeployment(
		uuid,
		name,
		owner,
		nil,
		status,
		now,
		now,
		&deployedAt,
		nil,
	)

	if dep.UUID() != uuid {
		t.Errorf("UUID() = %v, want %v", dep.UUID(), uuid)
	}
	if dep.Name() != name {
		t.Errorf("Name() = %v, want %v", dep.Name(), name)
	}
	if dep.Owner() != owner {
		t.Errorf("Owner() = %v, want %v", dep.Owner(), owner)
	}
	if dep.Status() != status {
		t.Errorf("Status() = %v, want %v", dep.Status(), status)
	}
	if dep.DeployedAt() == nil || !dep.DeployedAt().Equal(deployedAt) {
		t.Error("DeployedAt() timestamp mismatch")
	}
}
