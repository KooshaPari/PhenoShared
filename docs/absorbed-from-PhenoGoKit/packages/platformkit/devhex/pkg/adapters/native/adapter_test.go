package native

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
	var env domain.Environment = New()
	_ = env // Compile-time check
}

func TestAdapter_Name(t *testing.T) {
	// Native adapter doesn't have a Name() method on the adapter,
	// but it implements the Environment interface
	adapter := New()
	if adapter == nil {
		t.Fatal("New returned nil")
	}
}

func TestAdapter_Start(t *testing.T) {
	adapter := New()

	err := adapter.Start(context.Background(), domain.Config{
		Name:    "test",
		Backend: domain.BackendNative,
	})

	if err == nil {
		t.Error("expected error from unimplemented Start")
	}
}

func TestAdapter_Stop(t *testing.T) {
	adapter := New()

	err := adapter.Stop(context.Background())
	if err == nil {
		t.Error("expected error when no process running")
	}
}

func TestAdapter_Status(t *testing.T) {
	adapter := New()

	status, err := adapter.Status(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if status.Code != domain.StatusStopped {
		t.Errorf("expected Status=stopped when no process, got %s", status.Code)
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
		Backend: domain.BackendNative,
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
		t.Error("expected Stop to fail when no process")
	}
}
