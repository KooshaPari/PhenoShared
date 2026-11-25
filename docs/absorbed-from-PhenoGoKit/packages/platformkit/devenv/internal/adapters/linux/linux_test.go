package linux

import (
	"testing"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

func TestNewNativeAdapter(t *testing.T) {
	adapter := NewNativeAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "linux-native" {
		t.Errorf("expected name 'linux-native', got '%s'", adapter.Name())
	}
}

func TestNativeAdapter_Initialize(t *testing.T) {
	adapter := NewNativeAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNativeAdapter_CreateVM(t *testing.T) {
	adapter := NewNativeAdapter()
	
	config := &domain.VMConfig{
		Name:     "test-linux",
		MemoryMB: 4096,
		CPUs:     2,
	}
	
	_, err := adapter.CreateVM(config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNativeAdapter_StartVM(t *testing.T) {
	adapter := NewNativeAdapter()
	
	err := adapter.StartVM("test-linux")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNativeAdapter_StopVM(t *testing.T) {
	adapter := NewNativeAdapter()
	
	err := adapter.StopVM("test-linux")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNativeAdapter_DeleteVM(t *testing.T) {
	adapter := NewNativeAdapter()
	
	err := adapter.DeleteVM("test-linux")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNativeAdapter_ListVMs(t *testing.T) {
	adapter := NewNativeAdapter()
	
	vms, err := adapter.ListVMs()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if vms == nil {
		t.Error("expected non-nil VM list")
	}
}

func TestNativeAdapter_ExecuteCommand(t *testing.T) {
	adapter := NewNativeAdapter()
	
	output, err := adapter.ExecuteCommand("test-linux", "echo hello")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if output == nil {
		t.Error("expected non-nil output")
	}
}

func TestNewFirecrackerAdapter(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "firecracker" {
		t.Errorf("expected name 'firecracker', got '%s'", adapter.Name())
	}
}

func TestFirecrackerAdapter_Initialize(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestFirecrackerAdapter_CreateVM(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	
	config := &domain.VMConfig{
		Name:     "test-fc",
		MemoryMB: 256,
		CPUs:     1,
		Kernel:   "/var/lib/firecracker/vmlinux",
	}
	
	_, err := adapter.CreateVM(config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestFirecrackerAdapter_StartVM(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	
	err := adapter.StartVM("test-fc")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestFirecrackerAdapter_StopVM(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	
	err := adapter.StopVM("test-fc")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestFirecrackerAdapter_DeleteVM(t *testing.T) {
	adapter := NewFirecrackerAdapter()
	
	err := adapter.DeleteVM("test-fc")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewKVMAdapter(t *testing.T) {
	adapter := NewKVMAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "kvm" {
		t.Errorf("expected name 'kvm', got '%s'", adapter.Name())
	}
}

func TestKVMAdapter_Initialize(t *testing.T) {
	adapter := NewKVMAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}
