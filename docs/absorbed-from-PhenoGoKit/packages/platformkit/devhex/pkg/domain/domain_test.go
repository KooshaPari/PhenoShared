package domain

import (
	"context"
	"io"
	"testing"
	"time"
)

// testAdapter implements Environment for interface verification
type testAdapter struct{}

func (t *testAdapter) Start(ctx context.Context, cfg Config) error { return nil }
func (t *testAdapter) Stop(ctx context.Context) error { return nil }
func (t *testAdapter) Status(ctx context.Context) (Status, error) { return Status{}, nil }
func (t *testAdapter) Exec(ctx context.Context, cmd []string) (ExecResult, error) { return ExecResult{}, nil }
func (t *testAdapter) Logs(ctx context.Context) (io.ReadCloser, error) { return nil, nil }

// Compile-time interface check
var _ Environment = (*testAdapter)(nil)

func TestEnvironmentInterface(t *testing.T) {
	// Verify the Environment interface is properly defined
	// This is a compile-time check
	var env Environment = &testAdapter{}
	_ = env
}

func TestBackendTypeConstants(t *testing.T) {
	backends := []BackendType{
		BackendDocker,
		BackendPodman,
		BackendNix,
		BackendNative,
	}

	for _, b := range backends {
		if b == "" {
			t.Error("BackendType constant is empty")
		}
	}
}

func TestStatusCodeConstants(t *testing.T) {
	codes := []StatusCode{
		StatusRunning,
		StatusStopped,
		StatusStarting,
		StatusStopping,
		StatusError,
		StatusUnknown,
	}

	for _, c := range codes {
		if c == "" {
			t.Error("StatusCode constant is empty")
		}
	}
}

func TestConfig(t *testing.T) {
	cfg := Config{
		Name:    "test-env",
		Backend: BackendDocker,
		Image:   "alpine:latest",
		Ports: []PortMapping{
			{HostPort: 8080, ContainerPort: 80, Protocol: "tcp"},
		},
		Volumes: []VolumeMount{
			{Source: "/data", Target: "/app/data", ReadOnly: false},
		},
		Env:    map[string]string{"KEY": "value"},
		WorkDir: "/app",
	}

	if cfg.Name != "test-env" {
		t.Errorf("expected Name=test-env, got %s", cfg.Name)
	}
	if cfg.Backend != BackendDocker {
		t.Errorf("expected Backend=docker, got %s", cfg.Backend)
	}
	if len(cfg.Ports) != 1 {
		t.Errorf("expected 1 port mapping, got %d", len(cfg.Ports))
	}
	if len(cfg.Volumes) != 1 {
		t.Errorf("expected 1 volume, got %d", len(cfg.Volumes))
	}
}

func TestPortMapping(t *testing.T) {
	pm := PortMapping{
		HostPort:      3000,
		ContainerPort: 80,
		Protocol:      "tcp",
	}

	if pm.HostPort != 3000 {
		t.Errorf("expected HostPort=3000, got %d", pm.HostPort)
	}
	if pm.ContainerPort != 80 {
		t.Errorf("expected ContainerPort=80, got %d", pm.ContainerPort)
	}
	if pm.Protocol != "tcp" {
		t.Errorf("expected Protocol=tcp, got %s", pm.Protocol)
	}
}

func TestVolumeMount(t *testing.T) {
	vm := VolumeMount{
		Source:   "/host/path",
		Target:   "/container/path",
		ReadOnly: true,
	}

	if vm.Source != "/host/path" {
		t.Errorf("expected Source=/host/path, got %s", vm.Source)
	}
	if vm.Target != "/container/path" {
		t.Errorf("expected Target=/container/path, got %s", vm.Target)
	}
	if !vm.ReadOnly {
		t.Error("expected ReadOnly=true")
	}
}

func TestStatus(t *testing.T) {
	now := time.Now()
	status := Status{
		Code:      StatusRunning,
		Message:   "Running normally",
		StartedAt: &now,
		Metadata:  map[string]string{"container_id": "abc123"},
	}

	if status.Code != StatusRunning {
		t.Errorf("expected Code=running, got %s", status.Code)
	}
	if status.Message != "Running normally" {
		t.Errorf("expected Message='Running normally', got %s", status.Message)
	}
	if status.StartedAt == nil {
		t.Error("expected StartedAt to be set")
	}
	if status.Metadata["container_id"] != "abc123" {
		t.Errorf("expected container_id=abc123, got %s", status.Metadata["container_id"])
	}
}

func TestExecResult(t *testing.T) {
	result := ExecResult{
		ExitCode: 0,
		Stdout:   []byte("Hello, World!"),
		Stderr:   []byte(""),
		Duration: 100 * time.Millisecond,
	}

	if result.ExitCode != 0 {
		t.Errorf("expected ExitCode=0, got %d", result.ExitCode)
	}
	if string(result.Stdout) != "Hello, World!" {
		t.Errorf("expected Stdout='Hello, World!', got %s", result.Stdout)
	}
	if result.Duration != 100*time.Millisecond {
		t.Errorf("expected Duration=100ms, got %v", result.Duration)
	}
}
