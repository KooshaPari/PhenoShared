// Package windows provides the Windows adapter with three tiers:
// - Native VM (Hyper-V)
// - WSL2 (container-style Linux VMs)
// - MicroVM (Cloud Hypervisor)
package windows

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

// Adapter implements VMAdapter for Windows.
type Adapter struct {
	wslBin          string
	hypervBin       string
	cloudHypervisor string
}

// NewAdapter creates a new Windows adapter.
func NewAdapter() (*Adapter, error) {
	a := &Adapter{}

	// Check for WSL2
	wslBin, err := exec.LookPath("wsl")
	if err != nil {
		// Try PowerShell wsl
		out, err := exec.Command("powershell", "-Command", "Get-Command wsl -ErrorAction SilentlyContinue").Output()
		if err == nil && len(out) > 0 {
			a.wslBin = "wsl"
		}
	} else {
		a.wslBin = wslBin
	}

	// Check for Hyper-V
	hypervBin, _ := exec.LookPath("hyperv")
	if hypervBin == "" {
		// Try PowerShell
		out, err := exec.Command("powershell", "-Command", "Get-Command Enable-WindowsOptionalFeature -ErrorAction SilentlyContinue").Output()
		if err == nil && len(out) > 0 {
			a.hypervBin = "powershell"
		}
	}

	// Check for cloud-hypervisor
	a.cloudHypervisor, _ = exec.LookPath("cloud-hypervisor")

	return a, nil
}

// Name returns the adapter name.
func (a *Adapter) Name() string {
	return "windows-adapter"
}

// VMType returns the VM type.
func (a *Adapter) VMType() domain.VMType {
	return domain.VMTypeWSL
}

// CreateVM creates a new Windows VM using the appropriate backend.
func (a *Adapter) CreateVM(ctx context.Context, config domain.VMConfig) (*domain.VM, error) {
	name := config.Name
	if name == "" {
		name = fmt.Sprintf("devenv-%s", domain.GenerateID()[:8])
	}

	switch config.VMType {
	case domain.VMTypeNative:
		return a.createHyperVVM(ctx, name, config)
	case domain.VMTypeWSL:
		return a.createWSL2VM(ctx, name, config)
	case domain.VMTypeMicroVM:
		return a.createCloudHypervisorVM(ctx, name, config)
	default:
		return a.createWSL2VM(ctx, name, config)
	}
}

// StartVM starts a Windows VM.
func (a *Adapter) StartVM(ctx context.Context, id string) error {
	if a.hypervBin != "" {
		cmd := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("Start-VM -Name %s", id))
		return cmd.Run()
	}
	// Fallback to WSL
	cmd := exec.CommandContext(ctx, a.wslBin, "--distribution", id, "--", "bash", "-c", "echo started")
	return cmd.Run()
}

// StopVM stops a Windows VM.
func (a *Adapter) StopVM(ctx context.Context, id string) error {
	if a.hypervBin != "" {
		cmd := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("Stop-VM -Name %s -Force", id))
		return cmd.Run()
	}
	// Fallback to WSL
	cmd := exec.CommandContext(ctx, a.wslBin, "--shutdown")
	return cmd.Run()
}

// DeleteVM deletes a Windows VM.
func (a *Adapter) DeleteVM(ctx context.Context, id string) error {
	if a.hypervBin != "" {
		cmd := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("Remove-VM -Name %s -Force", id))
		return cmd.Run()
	}
	// Fallback to WSL
	cmd := exec.CommandContext(ctx, a.wslBin, "--unregister", id)
	return cmd.Run()
}

// ListVMs lists all Windows VMs.
func (a *Adapter) ListVMs(ctx context.Context) ([]domain.VM, error) {
	if a.hypervBin != "" {
		return a.listHyperVVMs(ctx)
	}
	return a.listWSL2VMs(ctx)
}

// listWSL2VMs lists WSL2 distributions.
func (a *Adapter) listWSL2VMs(ctx context.Context) ([]domain.VM, error) {
	cmd := exec.CommandContext(ctx, a.wslBin, "--list", "--verbose", "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	var vms []struct {
		Name   string `json:"name"`
		State  int    `json:"state"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		return nil, err
	}

	result := make([]domain.VM, 0, len(vms))
	for _, vm := range vms {
		result = append(result, domain.VM{
			ID:     vm.Name,
			Name:   vm.Name,
			Status: a.wslStateToStatus(vm.State),
			VMType: domain.VMTypeWSL,
		})
	}
	return result, nil
}

// listHyperVVMs lists Hyper-V VMs.
func (a *Adapter) listHyperVVMs(ctx context.Context) ([]domain.VM, error) {
	cmd := exec.CommandContext(ctx, "powershell", "-Command", "Get-VM | Select-Object Name, State | ConvertTo-Json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	var vms []struct {
		Name  string `json:"Name"`
		State string `json:"State"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		// Try single VM case
		var vm struct {
			Name  string `json:"Name"`
			State string `json:"State"`
		}
		if err := json.Unmarshal(out.Bytes(), &vm); err == nil {
			return []domain.VM{{
				ID:     vm.Name,
				Name:   vm.Name,
				Status: domain.ParseStatus(vm.State),
				VMType: domain.VMTypeNative,
			}}, nil
		}
		return nil, err
	}

	result := make([]domain.VM, 0, len(vms))
	for _, vm := range vms {
		result = append(result, domain.VM{
			ID:     vm.Name,
			Name:   vm.Name,
			Status: domain.ParseStatus(vm.State),
			VMType: domain.VMTypeNative,
		})
	}
	return result, nil
}

// VMStatus returns the status of a Windows VM.
func (a *Adapter) VMStatus(ctx context.Context, id string) (domain.VMStatus, error) {
	if a.hypervBin != "" {
		cmd := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("(Get-VM -Name %s).State", id))
		out, err := exec.CommandContext(ctx, cmd.Path, cmd.Args[1:]...).Output()
		if err != nil {
			return domain.VMStatusUnknown, err
		}
		return domain.ParseStatus(strings.TrimSpace(string(out))), nil
	}
	// WSL
	cmd := exec.CommandContext(ctx, a.wslBin, "--list", "--verbose", "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return domain.VMStatusUnknown, err
	}

	var vms []struct {
		Name   string `json:"name"`
		State  int    `json:"state"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		return domain.VMStatusUnknown, err
	}

	for _, vm := range vms {
		if vm.Name == id {
			return a.wslStateToStatus(vm.State), nil
		}
	}
	return domain.VMStatusUnknown, fmt.Errorf("VM not found: %s", id)
}

// ExecVM executes a command in a Windows VM.
func (a *Adapter) ExecVM(ctx context.Context, id string, cmd []string, stdin io.Reader, stdout, stderr io.Writer) error {
	execCmd := exec.CommandContext(ctx, a.wslBin, "--distribution", id, "--", "bash", "-c", strings.Join(cmd, " "))
	execCmd.Stdin = stdin
	execCmd.Stdout = stdout
	execCmd.Stderr = stderr
	return execCmd.Run()
}

// GetVMInfo returns detailed VM information.
func (a *Adapter) GetVMInfo(ctx context.Context, id string) (map[string]interface{}, error) {
	cmd := exec.CommandContext(ctx, a.wslBin, "--list", "--verbose", "--json")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	var vms []struct {
		Name          string `json:"name"`
		State         int    `json:"state"`
		Version       string `json:"version"`
		Default       bool   `json:"default"`
		WSLVersion    int    `json:"wslVersion,omitempty"`
	}
	if err := json.Unmarshal(out.Bytes(), &vms); err != nil {
		return nil, err
	}

	for _, vm := range vms {
		if vm.Name == id {
			return map[string]interface{}{
				"name":     vm.Name,
				"state":   vm.State,
				"version":  vm.Version,
				"default": vm.Default,
			}, nil
		}
	}
	return nil, fmt.Errorf("VM not found: %s", id)
}

// wslStateToStatus converts WSL state to VMStatus.
func (a *Adapter) wslStateToStatus(state int) domain.VMStatus {
	switch state {
	case 0:
		return domain.VMStatusRunning
	case 1:
		return domain.VMStatusRunning // Installing
	case 2:
		return domain.VMStatusStopped
	case 3:
		return domain.VMStatusRunning // Halting
	case 4:
		return domain.VMStatusStopped // Deleted
	default:
		return domain.VMStatusUnknown
	}
}

// createHyperVVM creates a VM using Hyper-V.
func (a *Adapter) createHyperVVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	if a.hypervBin == "" {
		return nil, fmt.Errorf("Hyper-V not available")
	}

	// Create Hyper-V VM using PowerShell
	createScript := fmt.Sprintf(`
		New-VM -Name %s -MemoryStartupBytes %dGB -BootDevice VHD -VHDPath "C:\\Users\\Public\\Documents\\%s.vhdx" -Generation 2
		Set-VMMemory -VMName %s -DynamicMemoryEnabled $true -MaximumBytes %dGB
		Add-VMNetworkAdapter -VMName %s -SwitchName "Default Switch"
	`, name, config.MemoryGB, name, name, config.MemoryGB, name)

	cmd := exec.CommandContext(ctx, "powershell", "-Command", createScript)
	cmd.Stdout = &bytes.Buffer{}
	cmd.Stderr = &bytes.Buffer{}
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("Hyper-V VM creation failed: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeNative,
		Config: config,
	}, nil
}

// createWSL2VM creates a VM using WSL2.
func (a *Adapter) createWSL2VM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	// Create WSL2 distribution from config
	wslConfig := a.generateWSL2Config(config)

	// Write config to temp file
	tmpPath := fmt.Sprintf("C:\\Users\\Public\\Documents\\devenv-%s-wsl.json", name)
	wslConfigJSON, _ := json.Marshal(wslConfig)
	if err := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("Set-Content -Path '%s' -Value '%s'", tmpPath, string(wslConfigJSON))).Run(); err != nil {
		return nil, fmt.Errorf("failed to write WSL config: %w", err)
	}

	// Import the WSL distribution
	cmd := exec.CommandContext(ctx, a.wslBin, "--import", name, fmt.Sprintf("C:\\Users\\Public\\Documents\\%s", name), tmpPath, "--version", "2")
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("WSL2 VM creation failed: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeWSL,
		Config: config,
	}, nil
}

// createCloudHypervisorVM creates a MicroVM using Cloud Hypervisor.
func (a *Adapter) createCloudHypervisorVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	if a.cloudHypervisor == "" {
		return nil, fmt.Errorf("cloud-hypervisor not found")
	}

	clConfig := a.generateCloudHypervisorConfig(config)
	configPath := fmt.Sprintf("C:\\Users\\Public\\Documents\\devenv-%s-cl.json", name)
	clConfigJSON, _ := json.Marshal(clConfig)
	if err := exec.CommandContext(ctx, "powershell", "-Command", fmt.Sprintf("Set-Content -Path '%s' -Value '%s'", configPath, string(clConfigJSON))).Run(); err != nil {
		return nil, fmt.Errorf("failed to write cloud-hypervisor config: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeMicroVM,
		Config: config,
	}, nil
}

// generateWSL2Config generates WSL2 configuration.
func (a *Adapter) generateWSL2Config(config domain.VMConfig) map[string]interface{} {
	return map[string]interface{}{
		"version":          2,
		"processor":        config.CPU,
		"memory":           fmt.Sprintf("%dGB", config.MemoryGB),
		"disk":             fmt.Sprintf("%dGB", config.DiskGB),
		"network":          map[string]bool{"generateResolvConf": false},
		"filesystem":       map[string]interface{}{},
		"environmentVars":  map[string]string{"DEVENv_MODE": config.Mode},
	}
}

// generateCloudHypervisorConfig generates Cloud Hypervisor configuration.
func (a *Adapter) generateCloudHypervisorConfig(config domain.VMConfig) map[string]interface{} {
	return map[string]interface{}{
		"boot-source": map[string]string{
			"kernel_image_path": "/var/lib/cloud-hypervisor/vmlinux",
			"initrd_path":       "",
		},
		"drives": []map[string]interface{}{
			{
				"drive_id":        "root",
				"path_on_host":     fmt.Sprintf("/var/lib/cloud-hypervisor/%s-rootfs.ext4", config.Name),
				"is_root_device":   true,
				"is_read_only":     false,
			},
		},
		"machine-config": map[string]interface{}{
			"vcpu_count": config.CPU,
			"mem_size":   config.MemoryGB * 1024,
		},
	}
}
