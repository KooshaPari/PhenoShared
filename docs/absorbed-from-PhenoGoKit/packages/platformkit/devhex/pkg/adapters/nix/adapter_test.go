package nix

import (
	"context"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

func TestNew(t *testing.T) {
	adapter := New()
	if adapter == nil {
		t.Fatal("New returned nil")
	}
}

func TestAdapter_ImplementsEnvironment(t *testing.T) {
	// Compile-time interface check
	var env domain.Environment = New()
	_ = env
}

func TestAdapter_Start(t *testing.T) {
	adapter := New()

	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test",
		Backend: domain.BackendNix,
		Image:   "github:DeterminateSystems/nix-direnv",
	})

	if err == nil {
		t.Error("expected error from unimplemented Start")
	}
}

func TestAdapter_Stop_NoShell(t *testing.T) {
	adapter := New()

	err := adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected error when no shell running")
	}
}

func TestAdapter_Status_NoShell(t *testing.T) {
	adapter := New()

	status, err := adapter.Status(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if status.Code != domain.StatusStopped {
		t.Errorf("expected Status=stopped when no shell, got %s", status.Code)
	}
}

func TestAdapter_Exec(t *testing.T) {
	adapter := New()

	_, err := adapter.Exec(context.Background(), []string{"echo", "hello"})
	if err == nil {
		t.Error("expected error from unimplemented Exec")
	}
}

func TestAdapter_Logs(t *testing.T) {
	adapter := New()

	_, err := adapter.Logs(context.Background())
	if err == nil {
		t.Error("expected error from unimplemented Logs")
	}
}

func TestAdapter_Lifecycle(t *testing.T) {
	adapter := New()

	// Start should fail (not implemented)
	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test-env",
		Backend: domain.BackendNix,
		Image:   "nixpkgs#hello",
	})
	if err == nil {
		t.Error("expected Start to fail")
	}

	// Status should work even when not started
	status, err := adapter.Status(context.Background())
	if err != nil {
		t.Fatalf("Status failed: %v", err)
	}
	if status.Code != domain.StatusStopped {
		t.Errorf("expected Status=stopped, got %s", status.Code)
	}

	// Stop should fail when not started
	err = adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected Stop to fail when no shell")
	}
}

func TestAdapter_Start_NotImplemented(t *testing.T) {
	adapter := New()
	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test-shell",
		Backend: domain.BackendNix,
		Image:   "nixpkgs#python3",
	})
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if err.Error() != "nix adapter: Start not yet implemented" {
		t.Errorf("unexpected error message: %s", err.Error())
	}
}

func TestAdapter_Stop_NotImplemented(t *testing.T) {
	// Use concrete type to access shellPID
	adapter := &Adapter{shellPID: 12345}

	err := adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if err.Error() != "nix adapter: Stop not yet implemented" {
		t.Errorf("unexpected error message: %s", err.Error())
	}
}

func TestAdapter_Status_NotImplemented(t *testing.T) {
	// Use concrete type to access shellPID
	adapter := &Adapter{shellPID: 12345}

	status, err := adapter.Status(context.Background())
	if err == nil {
		t.Error("expected not-implemented error")
	}
	if status.Code != domain.StatusUnknown {
		t.Errorf("expected Status=unknown, got %s", status.Code)
	}
}
