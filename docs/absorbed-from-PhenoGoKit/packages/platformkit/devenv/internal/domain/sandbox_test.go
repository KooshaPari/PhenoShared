package domain

import (
	"testing"
	"time"
)

func TestParseImage(t *testing.T) {
	tests := []struct {
		name        string
		image       string
		wantName    string
		wantTag     string
		wantErr     bool
	}{
		{
			name:     "simple image name",
			image:    "alpine",
			wantName: "alpine",
			wantTag:  "",
		},
		{
			name:     "image with tag",
			image:    "alpine:latest",
			wantName: "alpine",
			wantTag:  "latest",
		},
		{
			name:     "image with registry and tag",
			image:    "docker.io/library/alpine:3.18",
			wantName: "docker.io/library/alpine",
			wantTag:  "3.18",
		},
		{
			name:     "image with registry",
			image:    "ghcr.io/user/image",
			wantName: "ghcr.io/user/image",
			wantTag:  "",
		},
		{
			name:     "empty string",
			image:    "",
			wantErr:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := ParseImage(tt.image)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseImage() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr {
				if result.Name != tt.wantName {
					t.Errorf("ParseImage() Name = %v, want %v", result.Name, tt.wantName)
				}
				if result.Tag != tt.wantTag {
					t.Errorf("ParseImage() Tag = %v, want %v", result.Tag, tt.wantTag)
				}
			}
		})
	}
}

func TestSplitImageString(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected int // number of parts
	}{
		{"single part", "alpine", 1},
		{"two parts", "alpine:latest", 2},
		{"empty", "", 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			parts := splitImageString(tt.input)
			if len(parts) != tt.expected {
				t.Errorf("splitImageString() returned %d parts, want %d", len(parts), tt.expected)
			}
		})
	}
}

func TestGenerateID(t *testing.T) {
	t.Run("default prefix", func(t *testing.T) {
		id := GenerateID()
		if id == "" {
			t.Error("GenerateID returned empty string")
		}
		// Should start with "id-"
		if len(id) < 3 || id[:3] != "id-" {
			t.Errorf("GenerateID() = %s, should start with 'id-'", id)
		}
	})

	t.Run("custom prefix", func(t *testing.T) {
		id := GenerateID("sandbox")
		if id == "" {
			t.Error("GenerateID returned empty string")
		}
		// Should start with "sandbox-"
		if len(id) < 9 || id[:8] != "sandbox-" {
			t.Errorf("GenerateID() = %s, should start with 'sandbox-'", id)
		}
	})

	t.Run("unique IDs", func(t *testing.T) {
		id1 := GenerateID()
		time.Sleep(1 * time.Nanosecond) // Ensure different timestamp
		id2 := GenerateID()
		if id1 == id2 {
			t.Error("GenerateID should produce unique IDs")
		}
	})
}

func TestParseVMStatus(t *testing.T) {
	tests := []struct {
		input    string
		expected VMStatus
	}{
		{"running", VMStatusRunning},
		{"Running", VMStatusRunning},
		{"RUNNING", VMStatusRunning},
		{"stopped", VMStatusStopped},
		{"Stopped", VMStatusStopped},
		{"STOPPED", VMStatusStopped},
		{"unknown-case", VMStatusCreated},
		{"", VMStatusCreated},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			result := ParseVMStatus(tt.input)
			if result != tt.expected {
				t.Errorf("ParseVMStatus(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestParseStatus(t *testing.T) {
	tests := []struct {
		input    string
		expected SandboxStatus
	}{
		{"running", SandboxStatusRunning},
		{"Running", SandboxStatusRunning},
		{"RUNNING", SandboxStatusRunning},
		{"stopped", SandboxStatusStopped},
		{"Stopped", SandboxStatusStopped},
		{"STOPPED", SandboxStatusStopped},
		{"unknown-case", SandboxStatusCreated},
		{"", SandboxStatusCreated},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			result := ParseStatus(tt.input)
			if result != tt.expected {
				t.Errorf("ParseStatus(%q) = %v, want %v", tt.input, result, tt.expected)
			}
		})
	}
}

func TestRuntimeTypeConstants(t *testing.T) {
	// Verify runtime type constants are defined
	constants := []RuntimeType{
		RuntimeDocker,
		RuntimeContainerd,
		RuntimeCrun,
		RuntimeGvisor,
		RuntimeWasmtime,
		RuntimeLima,
		RuntimeWSL,
		RuntimeNative,
	}

	for _, rt := range constants {
		if rt == "" {
			t.Error("RuntimeType constant is empty")
		}
	}
}

func TestSandboxTypeConstants(t *testing.T) {
	constants := []SandboxType{
		SandboxTypeGvisor,
		SandboxTypeLandlock,
		SandboxTypeSeccomp,
		SandboxTypeBwrap,
		SandboxTypeFirejail,
		SandboxTypeUnshare,
		SandboxTypeSandboxExec,
	}

	for _, st := range constants {
		if st == "" {
			t.Error("SandboxType constant is empty")
		}
	}
}

func TestSandboxStateConstants(t *testing.T) {
	states := []SandboxState{
		SandboxStateCreated,
		SandboxStateRunning,
		SandboxStateStopped,
	}

	for _, s := range states {
		if s == "" {
			t.Error("SandboxState constant is empty")
		}
	}
}

func TestSandboxStatusConstants(t *testing.T) {
	statuses := []SandboxStatus{
		SandboxStatusCreated,
		SandboxStatusRunning,
		SandboxStatusPaused,
		SandboxStatusStopped,
		SandboxStatusFailed,
	}

	for _, s := range statuses {
		if s == "" {
			t.Error("SandboxStatus constant is empty")
		}
	}
}

func TestVMTypeConstants(t *testing.T) {
	constants := []VMType{
		VMTypeNative,
		VMTypeWSL,
		VMTypeMicroVM,
		VMTypeQEMU,
		VMTypeKVM,
		VMTypeLima,
	}

	for _, vt := range constants {
		if vt == "" {
			t.Error("VMType constant is empty")
		}
	}
}

func TestVMStatusConstants(t *testing.T) {
	statuses := []VMStatus{
		VMStatusUnknown,
		VMStatusCreated,
		VMStatusRunning,
		VMStatusStopped,
		VMStatusPaused,
	}

	for _, s := range statuses {
		if s == "" {
			t.Error("VMStatus constant is empty")
		}
	}
}

func TestWASMTypeConstants(t *testing.T) {
	constants := []WASMType{
		WASMTypeWasmtime,
		WASMTypeWasmEdge,
		WASMTypeWasmer,
		WASMTypeWazero,
	}

	for _, wt := range constants {
		if wt == "" {
			t.Error("WASMType constant is empty")
		}
	}
}

func TestSandboxConfig(t *testing.T) {
	cfg := SandboxConfig{
		Name:            "test-sandbox",
		Type:            SandboxTypeBwrap,
		RootDir:         "/tmp/sandbox",
		Runtime:         RuntimeDocker,
		Image:           "alpine:latest",
		MemoryMB:        512,
		CPUCount:        2,
		NetworkEnabled:  false,
	}

	if cfg.Name != "test-sandbox" {
		t.Errorf("expected Name=test-sandbox, got %s", cfg.Name)
	}
	if cfg.Type != SandboxTypeBwrap {
		t.Errorf("expected Type=bwrap, got %s", cfg.Type)
	}
}

func TestSandbox(t *testing.T) {
	sb := Sandbox{
		ID:    "sandbox-123",
		Name:  "test-sandbox",
		Type:  SandboxTypeGvisor,
		State: SandboxStateRunning,
	}

	if sb.ID != "sandbox-123" {
		t.Errorf("expected ID=sandbox-123, got %s", sb.ID)
	}
	if sb.State != SandboxStateRunning {
		t.Errorf("expected State=running, got %s", sb.State)
	}
}

func TestVMConfig(t *testing.T) {
	cfg := VMConfig{
		Name:     "test-vm",
		VMType:   VMTypeLima,
		MemoryMB: 4096,
		CPUCount: 4,
		DiskMB:   51200,
	}

	if cfg.Name != "test-vm" {
		t.Errorf("expected Name=test-vm, got %s", cfg.Name)
	}
	if cfg.VMType != VMTypeLima {
		t.Errorf("expected VMType=lima, got %s", cfg.VMType)
	}
}

func TestVM(t *testing.T) {
	vm := VM{
		ID:     "vm-123",
		Name:   "test-vm",
		VMType: VMTypeKVM,
		Status: VMStatusRunning,
	}

	if vm.ID != "vm-123" {
		t.Errorf("expected ID=vm-123, got %s", vm.ID)
	}
	if vm.Status != VMStatusRunning {
		t.Errorf("expected Status=running, got %s", vm.Status)
	}
}

func TestProcess(t *testing.T) {
	proc := Process{
		ID:        "proc-123",
		SandboxID: "sandbox-456",
		Command:   "echo hello",
		ExitCode:  0,
	}

	if proc.ID != "proc-123" {
		t.Errorf("expected ID=proc-123, got %s", proc.ID)
	}
	if proc.ExitCode != 0 {
		t.Errorf("expected ExitCode=0, got %d", proc.ExitCode)
	}
}

func TestSandboxStats(t *testing.T) {
	stats := SandboxStats{
		SandboxID:   "sandbox-123",
		Type:        SandboxTypeBwrap,
		CPUUsage:    25.5,
		MemoryMB:    128.0,
		DiskUsage:   1024 * 1024,
	}

	if stats.SandboxID != "sandbox-123" {
		t.Errorf("expected SandboxID=sandbox-123, got %s", stats.SandboxID)
	}
	if stats.CPUUsage != 25.5 {
		t.Errorf("expected CPUUsage=25.5, got %f", stats.CPUUsage)
	}
}

func TestWASMStats(t *testing.T) {
	stats := WASMStats{
		InstanceID:            "wasm-123",
		Type:                 WASMTypeWasmtime,
		MemoryMB:             64.0,
		InstructionsExecuted: 1000000,
	}

	if stats.InstanceID != "wasm-123" {
		t.Errorf("expected InstanceID=w wasm-123, got %s", stats.InstanceID)
	}
	if stats.Type != WASMTypeWasmtime {
		t.Errorf("expected Type=wasmtime, got %s", stats.Type)
	}
}

func TestOCIImage(t *testing.T) {
	img := OCIImage{
		Registry: "docker.io",
		Name:     "library/alpine",
		Tag:      "3.18",
		Digest:   "sha256:abc123",
	}

	if img.Registry != "docker.io" {
		t.Errorf("expected Registry=docker.io, got %s", img.Registry)
	}
	if img.Tag != "3.18" {
		t.Errorf("expected Tag=3.18, got %s", img.Tag)
	}
}

func TestMount(t *testing.T) {
	mount := Mount{
		Source:   "/host/path",
		Target:   "/container/path",
		ReadOnly: true,
	}

	if mount.Source != "/host/path" {
		t.Errorf("expected Source=/host/path, got %s", mount.Source)
	}
	if !mount.ReadOnly {
		t.Error("expected ReadOnly=true")
	}
}
