package windows

import (
	"testing"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

func TestNewWSL2Adapter(t *testing.T) {
	adapter := NewWSL2Adapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "wsl2" {
		t.Errorf("expected name 'wsl2', got '%s'", adapter.Name())
	}
}

func TestWSL2Adapter_Initialize(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWSL2Adapter_CreateVM(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	config := &domain.VMConfig{
		Name:     "test-wsl2",
		MemoryMB: 4096,
		CPUs:     2,
	}
	
	_, err := adapter.CreateVM(config)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWSL2Adapter_StartVM(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	err := adapter.StartVM("test-wsl2")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWSL2Adapter_StopVM(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	err := adapter.StopVM("test-wsl2")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWSL2Adapter_DeleteVM(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	err := adapter.DeleteVM("test-wsl2")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWSL2Adapter_ListVMs(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	vms, err := adapter.ListVMs()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if vms == nil {
		t.Error("expected non-nil VM list")
	}
}

func TestWSL2Adapter_ExecuteCommand(t *testing.T) {
	adapter := NewWSL2Adapter()
	
	output, err := adapter.ExecuteCommand("test-wsl2", "echo hello")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if output == nil {
		t.Error("expected non-nil output")
	}
}

func TestWSL2Adapter_ParseWslOutput(t *testing.T) {
	output := `  NAME                   STATE           VERSION
* Ubuntu                   Running         2
  docker-desktop           Stopped        2`

	vms, err := adapter{}.parseWslOutput(output)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if len(vms) != 2 {
		t.Errorf("expected 2 VMs, got %d", len(vms))
	}
}

func TestNewHyperVAdapter(t *testing.T) {
	adapter := NewHyperVAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "hyperv" {
		t.Errorf("expected name 'hyperv', got '%s'", adapter.Name())
	}
}

func TestHyperVAdapter_Initialize(t *testing.T) {
	adapter := NewHyperVAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewCloudHypervisorAdapter(t *testing.T) {
	adapter := NewCloudHypervisorAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "cloud-hypervisor" {
		t.Errorf("expected name 'cloud-hypervisor', got '%s'", adapter.Name())
	}
}

func TestCloudHypervisorAdapter_Initialize(t *testing.T) {
	adapter := NewCloudHypervisorAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}
