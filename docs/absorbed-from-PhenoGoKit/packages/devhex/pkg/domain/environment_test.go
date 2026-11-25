package domain_test

import (
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

func TestBackendTypeConstants(t *testing.T) {
	tests := []struct {
		name    string
		backend domain.BackendType
		want    string
	}{
		{"docker", domain.BackendDocker, "docker"},
		{"podman", domain.BackendPodman, "podman"},
		{"nix", domain.BackendNix, "nix"},
		{"native", domain.BackendNative, "native"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if string(tc.backend) != tc.want {
				t.Errorf("BackendType %q: got %q, want %q", tc.name, tc.backend, tc.want)
			}
		})
	}
}

func TestStatusCodeConstants(t *testing.T) {
	tests := []struct {
		name string
		code domain.StatusCode
		want string
	}{
		{"running", domain.StatusRunning, "running"},
		{"stopped", domain.StatusStopped, "stopped"},
		{"starting", domain.StatusStarting, "starting"},
		{"stopping", domain.StatusStopping, "stopping"},
		{"error", domain.StatusError, "error"},
		{"unknown", domain.StatusUnknown, "unknown"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if string(tc.code) != tc.want {
				t.Errorf("StatusCode %q: got %q, want %q", tc.name, tc.code, tc.want)
			}
		})
	}
}

func TestConfigZeroValue(t *testing.T) {
	// Zero-value Config must be valid (no panics) and have empty fields.
	var cfg domain.Config
	if cfg.Name != "" {
		t.Errorf("expected empty Name, got %q", cfg.Name)
	}
	if cfg.Backend != "" {
		t.Errorf("expected empty Backend, got %q", cfg.Backend)
	}
	if cfg.Env != nil {
		t.Errorf("expected nil Env map")
	}
}

func TestStatusZeroValue(t *testing.T) {
	var s domain.Status
	if s.Code != "" {
		t.Errorf("expected empty StatusCode, got %q", s.Code)
	}
	if s.StartedAt != nil || s.StoppedAt != nil {
		t.Error("expected nil time pointers in zero Status")
	}
}
