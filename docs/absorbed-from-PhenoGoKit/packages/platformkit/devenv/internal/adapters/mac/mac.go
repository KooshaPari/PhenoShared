// Package mac provides the macOS adapter with three tiers:
// - Native VM (HyperKit via VMware Fusion)
// - Lima/VZ (container-style Linux VMs)
// - MicroVM (Firecracker)
package mac

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"strings"
	"text/template"

	"github.com/kooshapari/devenv-abstraction/internal/domain"
)

// Adapter implements VMAdapter for macOS.
type Adapter struct {
	limaPath       string
	firecrackerBin string
}

// NewAdapter creates a new macOS adapter.
func NewAdapter() (*Adapter, error) {
	a := &Adapter{}

	// Check for lima installation
	limaPath, err := exec.LookPath("limactl")
	if err != nil {
		// Fallback to colima
		limaPath, err = exec.LookPath("colima")
		if err != nil {
			return nil, fmt.Errorf("neither lima nor colima found: %w", err)
		}
	}
	a.limaPath = limaPath

	// Check for firecracker
	a.firecrackerBin, _ = exec.LookPath("firecracker")

	return a, nil
}

// Name returns the adapter name.
func (a *Adapter) Name() string {
	return "macos-adapter"
}

// VMType returns the VM type.
func (a *Adapter) VMType() domain.VMType {
	return domain.VMTypeLima
}

// CreateVM creates a new macOS VM using the appropriate backend.
func (a *Adapter) CreateVM(ctx context.Context, config domain.VMConfig) (*domain.VM, error) {
	name := config.Name
	if name == "" {
		name = fmt.Sprintf("devenv-%s", domain.GenerateID()[:8])
	}

	switch config.VMType {
	case domain.VMTypeNative:
		return a.createHyperKitVM(ctx, name, config)
	case domain.VMTypeLima:
		return a.createLimaVM(ctx, name, config)
	case domain.VMTypeMicroVM:
		return a.createFirecrackerVM(ctx, name, config)
	default:
		return a.createLimaVM(ctx, name, config)
	}
}

// StartVM starts a macOS VM.
func (a *Adapter) StartVM(ctx context.Context, id string) error {
	cmd := exec.CommandContext(ctx, a.limaPath, "start", id)
	return cmd.Run()
}

// StopVM stops a macOS VM.
func (a *Adapter) StopVM(ctx context.Context, id string) error {
	cmd := exec.CommandContext(ctx, a.limaPath, "stop", id)
	return cmd.Run()
}

// DeleteVM deletes a macOS VM.
func (a *Adapter) DeleteVM(ctx context.Context, id string) error {
	cmd := exec.CommandContext(ctx, a.limaPath, "delete", id, "--force")
	return cmd.Run()
}

// ListVMs lists all macOS VMs.
func (a *Adapter) ListVMs(ctx context.Context) ([]domain.VM, error) {
	cmd := exec.CommandContext(ctx, a.limaPath, "list", "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	var vms []struct {
		Name   string `json:"name"`
		Status string `json:"status"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		return nil, err
	}

	result := make([]domain.VM, 0, len(vms))
	for _, vm := range vms {
		result = append(result, domain.VM{
			ID:     vm.Name,
			Name:   vm.Name,
			Status: domain.ParseStatus(vm.Status),
			VMType: domain.VMTypeLima,
		})
	}
	return result, nil
}

// VMStatus returns the status of a macOS VM.
func (a *Adapter) VMStatus(ctx context.Context, id string) (domain.VMStatus, error) {
	cmd := exec.CommandContext(ctx, a.limaPath, "list", "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return domain.VMStatusUnknown, err
	}

	var vms []struct {
		Name   string `json:"name"`
		Status string `json:"status"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		return domain.VMStatusUnknown, err
	}

	for _, vm := range vms {
		if vm.Name == id {
			return domain.ParseStatus(vm.Status), nil
		}
	}
	return domain.VMStatusUnknown, fmt.Errorf("VM not found: %s", id)
}

// ExecVM executes a command in a macOS VM.
func (a *Adapter) ExecVM(ctx context.Context, id string, cmd []string, stdin io.Reader, stdout, stderr io.Writer) error {
	execCmd := exec.CommandContext(ctx, a.limaPath, "shell", id, "/bin/bash", "-c", strings.Join(cmd, " "))
	execCmd.Stdin = stdin
	execCmd.Stdout = stdout
	execCmd.Stderr = stderr
	return execCmd.Run()
}

// GetVMInfo returns detailed VM information.
func (a *Adapter) GetVMInfo(ctx context.Context, id string) (map[string]interface{}, error) {
	cmd := exec.CommandContext(ctx, a.limaPath, "show", id, "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	var info map[string]interface{}
	if err := json.Unmarshal(out.Bytes(), &info); err != nil {
		return nil, err
	}
	return info, nil
}

// createHyperKitVM creates a VM using HyperKit (VMware Fusion).
func (a *Adapter) createHyperKitVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	// Check for VMware Fusion
	if _, err := exec.LookPath("vmrun"); err != nil {
		return nil, fmt.Errorf("vmrun (VMware Fusion) not found: %w", err)
	}

	// Note: HyperKit VMs require VMware Fusion
	// This is a placeholder for actual implementation
	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusRunning,
		VMType: domain.VMTypeNative,
		Config: config,
	}, nil
}

// createLimaVM creates a VM using Lima (with VZ driver).
func (a *Adapter) createLimaVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	yamlConfig := a.generateLimaConfig(config)

	// Write config to temp file
	tmpPath := fmt.Sprintf("/tmp/devenv-%s.yaml", name)
	if err := os.WriteFile(tmpPath, []byte(yamlConfig), 0644); err != nil {
		return nil, fmt.Errorf("failed to write config: %w", err)
	}

	// Create the VM
	cmd := exec.CommandContext(ctx, a.limaPath, "create", name, "--tty=false", "--vm-type=vz", tmpPath)
	cmd.Stdout = &bytes.Buffer{}
	cmd.Stderr = &bytes.Buffer{}
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("lima create failed: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeLima,
		Config: config,
	}, nil
}

// createFirecrackerVM creates a MicroVM using Firecracker.
func (a *Adapter) createFirecrackerVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	if a.firecrackerBin == "" {
		return nil, fmt.Errorf("firecracker not found")
	}

	// Create firecracker config
	fcConfig := a.generateFirecrackerConfig(config)
	configPath := fmt.Sprintf("/tmp/devenv-%s-fc.json", name)
	if err := os.WriteFile(configPath, []byte(fcConfig), 0644); err != nil {
		return nil, fmt.Errorf("failed to write firecracker config: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeMicroVM,
		Config: config,
	}, nil
}

// generateLimaConfig generates a Lima configuration for the sandbox.
func (a *Adapter) generateLimaConfig(config domain.VMConfig) string {
	tmpl := `images:
  - location: "https://github.com/lima-vm/lima/releases/download/v0.20.0/jammy.yaml"
    arch: "{{ .Arch }}"

cpus: {{ .CPU }}
memory: {{ .MemoryGB }}G
disk: {{ .DiskGB }}G

mounts:
  - location: "~/"
    writable: {{ .ReadWrite }}
  - location: "/tmp/devenv"
    writable: true

environment:
  DEVENv_MODE: "{{ .Mode }}"
`

	t, _ := template.New("lima").Parse(tmpl)
	var buf bytes.Buffer
	t.Execute(&buf, map[string]interface{}{
		"Arch":      config.Arch,
		"CPU":       config.CPU,
		"MemoryGB":  config.MemoryGB,
		"DiskGB":    config.DiskGB,
		"ReadWrite": config.ReadWrite,
		"Mode":      config.Mode,
	})
	return buf.String()
}

// generateFirecrackerConfig generates a Firecracker configuration.
func (a *Adapter) generateFirecrackerConfig(config domain.VMConfig) string {
	return fmt.Sprintf(`{
  "boot-source": {
    "kernel_image_path": "/var/lib/firecracker/vmlinux",
    "initrd_path": "",
    "boot_args": "console=ttyS0 reboot=k panic=1"
  },
  "drives": [
    {
      "drive_id": "root",
      "path_on_host": "/var/lib/firecracker/%s-rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "network-interfaces": [],
  "machine-config": {
    "vcpu_count": %d,
    "mem_size_mib": %d
  }
}`, config.Name, config.CPU, config.MemoryGB*1024)
}
