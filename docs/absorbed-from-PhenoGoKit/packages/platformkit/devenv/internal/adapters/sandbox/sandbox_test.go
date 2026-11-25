package sandbox

import (
	"context"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

func TestNewGvisorAdapter(t *testing.T) {
	adapter := NewGvisorAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "gvisor" {
		t.Errorf("expected name 'gvisor', got '%s'", adapter.Name())
	}
}

func TestGvisorAdapter_Initialize(t *testing.T) {
	ctx := context.Background()
	adapter := NewGvisorAdapter()
	
	err := adapter.Initialize(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestGvisorAdapter_CreateSandbox(t *testing.T) {
	ctx := context.Background()
	adapter := NewGvisorAdapter()
	
	config := &domain.SandboxConfig{
		Name: "test-sandbox",
	}
	
	_, err := adapter.CreateSandbox(ctx, config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestGvisorAdapter_DeleteSandbox(t *testing.T) {
	ctx := context.Background()
	adapter := NewGvisorAdapter()
	
	err := adapter.DeleteSandbox(ctx, "test-sandbox")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewLandlockAdapter(t *testing.T) {
	adapter := NewLandlockAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "landlock" {
		t.Errorf("expected name 'landlock', got '%s'", adapter.Name())
	}
}

func TestLandlockAdapter_Initialize(t *testing.T) {
	ctx := context.Background()
	adapter := NewLandlockAdapter()
	
	err := adapter.Initialize(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewSeccompAdapter(t *testing.T) {
	adapter := NewSeccompAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "seccomp" {
		t.Errorf("expected name 'seccomp', got '%s'", adapter.Name())
	}
}

func TestNewBwrapAdapter(t *testing.T) {
	adapter := NewBwrapAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "bwrap" {
		t.Errorf("expected name 'bwrap', got '%s'", adapter.Name())
	}
}

func TestBwrapAdapter_Initialize(t *testing.T) {
	ctx := context.Background()
	adapter := NewBwrapAdapter()
	
	err := adapter.Initialize(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestBwrapAdapter_CreateSandbox(t *testing.T) {
	ctx := context.Background()
	adapter := NewBwrapAdapter()
	
	config := &domain.SandboxConfig{
		Name: "test-sandbox",
		NativeSandbox: &domain.NativeSandboxConfig{
			BindMounts: []string{"/tmp:/tmp"},
		},
	}
	
	_, err := adapter.CreateSandbox(ctx, config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewFirejailAdapter(t *testing.T) {
	adapter := NewFirejailAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "firejail" {
		t.Errorf("expected name 'firejail', got '%s'", adapter.Name())
	}
}

func TestNewUnshareAdapter(t *testing.T) {
	adapter := NewUnshareAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "unshare" {
		t.Errorf("expected name 'unshare', got '%s'", adapter.Name())
	}
}

func TestNewSandboxExecAdapter(t *testing.T) {
	adapter := NewSandboxExecAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "sandbox-exec" {
		t.Errorf("expected name 'sandbox-exec', got '%s'", adapter.Name())
	}
}

func TestSandboxAdapter_ListSandboxes(t *testing.T) {
	ctx := context.Background()
	adapter := NewGvisorAdapter()
	
	sandboxes, err := adapter.ListSandboxes(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if sandboxes == nil {
		t.Error("expected non-nil sandbox list")
	}
}
