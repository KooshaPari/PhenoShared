package mac

import (
	"context"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

func TestNewLimaAdapter(t *testing.T) {
	adapter := NewLimaAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.name != "lima" {
		t.Errorf("expected name 'lima', got '%s'", adapter.name)
	}
}

func TestLimaAdapter_Start(t *testing.T) {
	ctx := context.Background()
	adapter := NewLimaAdapter()
	
	config := &domain.VMConfig{
		Name:   "test-vm",
		Memory: "2GiB",
		CPU:    2,
	}
	
	_, err := adapter.Start(ctx, config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestLimaAdapter_Stop(t *testing.T) {
	ctx := context.Background()
	adapter := NewLimaAdapter()
	
	err := adapter.Stop(ctx, "test-vm")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestLimaAdapter_Delete(t *testing.T) {
	ctx := context.Background()
	adapter := NewLimaAdapter()
	
	err := adapter.Delete(ctx, "test-vm")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestLimaAdapter_List(t *testing.T) {
	ctx := context.Background()
	adapter := NewLimaAdapter()
	
	vms, err := adapter.List(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if vms == nil {
		t.Error("expected non-nil VM list")
	}
}

func TestNewFirecrackerAdapter(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.name != "firecracker" {
		t.Errorf("expected name 'firecracker', got '%s'", adapter.name)
	}
}

func TestFirecrackerAdapter_Start(t *testing.T) {
	ctx := context.Background()
	adapter := NewFirecrackerAdapter()
	
	config := &domain.VMConfig{
		Name:   "test-vm",
		Memory: "256MiB",
		CPU:    1,
	}
	
	_, err := adapter.Start(ctx, config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewHyperKitAdapter(t *testing.T) {
	adapter := NewHyperKitAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.name != "hyperkit" {
		t.Errorf("expected name 'hyperkit', got '%s'", adapter.name)
	}
}

func TestHyperKitAdapter_List(t *testing.T) {
	ctx := context.Background()
	adapter := NewHyperKitAdapter()
	
	vms, err := adapter.List(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if vms == nil {
		t.Error("expected non-nil VM list")
	}
}

func TestLimaAdapter_Info(t *testing.T) {
	ctx := context.Background()
	adapter := NewLimaAdapter()
	
	info, err := adapter.Info(ctx)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if info == nil {
		t.Error("expected non-nil VM info")
	}
}
