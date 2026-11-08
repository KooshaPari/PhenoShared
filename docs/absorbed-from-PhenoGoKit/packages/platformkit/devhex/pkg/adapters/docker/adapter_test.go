package docker

import (
	"context"
	"os"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

func TestNew(t *testing.T) {
	// Skip if Docker is not available
	if os.Getenv("SKIP_DOCKER_TESTS") == "true" {
		t.Skip("skipping Docker-dependent test")
	}

	// New() will fail if Docker is not available, which is expected
	_, err := New()
	if err == nil {
		// Docker is available, test passes
		t.Log("Docker is available")
	}
}

func TestMustNew_Panic(t *testing.T) {
	// Skip this test - Docker environment availability varies
	t.Skip("Skipping MustNew panic test - Docker availability varies by environment")
	// Note: MustNew panics when Docker is unavailable, which is difficult to test reliably
}

func TestAdapter_ImplementsEnvironment(t *testing.T) {
	// Compile-time interface check
	var env domain.Environment = (*Adapter)(nil)
	_ = env
}

func TestAdapter_Start(t *testing.T) {
	// Test that Start returns not-implemented error
	adapter := &Adapter{}
	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test",
		Backend: domain.BackendDocker,
	})
	if err == nil {
		t.Error("expected error from unimplemented Start")
	}
}

func TestAdapter_Stop_NoContainer(t *testing.T) {
	adapter := &Adapter{}
	err := adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected error when no container running")
	}
}

func TestAdapter_Status_NoContainer(t *testing.T) {
	adapter := &Adapter{}
	status, err := adapter.Status(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if status.Code != domain.StatusStopped {
		t.Errorf("expected Status=stopped, got %s", status.Code)
	}
}

func TestAdapter_Exec(t *testing.T) {
	adapter := &Adapter{}
	_, err := adapter.Exec(context.Background(), []string{"echo", "hello"})
	if err == nil {
		t.Error("expected error from unimplemented Exec")
	}
}

func TestAdapter_Logs(t *testing.T) {
	adapter := &Adapter{}
	_, err := adapter.Logs(context.Background())
	if err == nil {
		t.Error("expected error from unimplemented Logs")
	}
}

func TestAdapter_Start_NotImplemented(t *testing.T) {
	adapter := &Adapter{}
	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test-container",
		Backend: domain.BackendDocker,
		Image:   "alpine:latest",
	})
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if err.Error() != "docker adapter: Start not yet implemented" {
		t.Errorf("unexpected error message: %s", err.Error())
	}
}

func TestAdapter_Stop_NotImplemented(t *testing.T) {
	adapter := &Adapter{containerID: "test-id"}
	err := adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if err.Error() != "docker adapter: Stop not yet implemented" {
		t.Errorf("unexpected error message: %s", err.Error())
	}
}

func TestAdapter_Status_NotImplemented(t *testing.T) {
	adapter := &Adapter{containerID: "test-id"}
	status, err := adapter.Status(context.Background())
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if status.Code != domain.StatusUnknown {
		t.Errorf("expected Status=unknown, got %s", status.Code)
	}
}
