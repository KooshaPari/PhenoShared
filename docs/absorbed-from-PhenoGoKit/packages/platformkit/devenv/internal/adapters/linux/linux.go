// Package linux provides the Linux adapter with three tiers:
// - Native VM (KVM/QEMU)
// - Native containers (runc, containerd)
// - MicroVM (Firecracker)
package linux

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"strings"

	"github.com/kooshapari/devenv-abstraction/internal/domain"
)

// Adapter implements VMAdapter for Linux.
type Adapter struct {
	qemuBin        string
	firecrackerBin string
	containerdBin  string
	runcBin        string
	virshBin       string
}

// NewAdapter creates a new Linux adapter.
func NewAdapter() (*Adapter, error) {
	a := &Adapter{}

	// Check for QEMU/KVM
	qemuBin, _ := exec.LookPath("qemu-system-x86_64")
	if qemuBin == "" {
		qemuBin, _ = exec.LookPath("qemu-kvm")
	}
	a.qemuBin = qemuBin

	// Check for Firecracker
	a.firecrackerBin, _ = exec.LookPath("firecracker")
	if a.firecrackerBin == "" {
		a.firecrackerBin, _ = exec.LookPath("firecracker-jailer")
	}

	// Check for containerd
	a.containerdBin, _ = exec.LookPath("containerd")
	if a.containerdBin == "" {
		a.containerdBin, _ = exec.LookPath("containerd-shim")
	}

	// Check for runc
	a.runcBin, _ = exec.LookPath("runc")
	if a.runcBin == "" {
		a.runcBin, _ = exec.LookPath("docker")
	}

	// Check for virsh (libvirt)
	a.virshBin, _ = exec.LookPath("virsh")

	return a, nil
}

// Name returns the adapter name.
func (a *Adapter) Name() string {
	return "linux-adapter"
}

// VMType returns the VM type.
func (a *Adapter) VMType() domain.VMType {
	return domain.VMTypeNative
}

// CreateVM creates a new Linux VM using the appropriate backend.
func (a *Adapter) CreateVM(ctx context.Context, config domain.VMConfig) (*domain.VM, error) {
	name := config.Name
	if name == "" {
		name = fmt.Sprintf("devenv-%s", domain.GenerateID()[:8])
	}

	switch config.VMType {
	case domain.VMTypeNative:
		if a.virshBin != "" {
			return a.createKVMMVM(ctx, name, config)
		}
		return a.createQEMUVM(ctx, name, config)
	case domain.VMTypeMicroVM:
		return a.createFirecrackerVM(ctx, name, config)
	default:
		return a.createContainerVM(ctx, name, config)
	}
}

// StartVM starts a Linux VM.
func (a *Adapter) StartVM(ctx context.Context, id string) error {
	if a.virshBin != "" {
		cmd := exec.CommandContext(ctx, a.virshBin, "start", id)
		return cmd.Run()
	}
	if a.firecrackerBin != "" {
		cmd := exec.CommandContext(ctx, a.firecrackerBin, "--api-sock", fmt.Sprintf("/var/run/firecracker/%s.sock", id))
		return cmd.Run()
	}
	// Try docker
	cmd := exec.CommandContext(ctx, "docker", "start", id)
	return cmd.Run()
}

// StopVM stops a Linux VM.
func (a *Adapter) StopVM(ctx context.Context, id string) error {
	if a.virshBin != "" {
		cmd := exec.CommandContext(ctx, a.virshBin, "shutdown", id)
		if err := cmd.Run(); err != nil {
			// Force shutdown if graceful fails
			return exec.CommandContext(ctx, a.virshBin, "destroy", id).Run()
		}
		return nil
	}
	if a.firecrackerBin != "" {
		cmd := exec.CommandContext(ctx, "curl", "-X", "PUT", "--unix-socket", fmt.Sprintf("/var/run/firecracker/%s.sock", id), "http://localhost/actions", "-d", "{\"action_type\": \"SendCtrlAltDel\"}")
		return cmd.Run()
	}
	// Try docker
	cmd := exec.CommandContext(ctx, "docker", "stop", id)
	return cmd.Run()
}

// DeleteVM deletes a Linux VM.
func (a *Adapter) DeleteVM(ctx context.Context, id string) error {
	if a.virshBin != "" {
		cmd := exec.CommandContext(ctx, a.virshBin, "undefine", "--domain", id)
		return cmd.Run()
	}
	if a.firecrackerBin != "" {
		// Remove firecracker jailer process
		exec.CommandContext(ctx, "pkill", "-f", fmt.Sprintf("firecracker-%s", id)).Run()
	}
	// Try docker
	cmd := exec.CommandContext(ctx, "docker", "rm", id)
	return cmd.Run()
}

// ListVMs lists all Linux VMs.
func (a *Adapter) ListVMs(ctx context.Context) ([]domain.VM, error) {
	if a.virshBin != "" {
		return a.listKVMVMs(ctx)
	}
	return a.listDockerContainers(ctx)
}

// listKVMVMs lists KVM/libvirt VMs.
func (a *Adapter) listKVMVMs(ctx context.Context) ([]domain.VM, error) {
	cmd := exec.CommandContext(ctx, a.virshBin, "list", "--all", "--name")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return nil, err
	}

	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	result := make([]domain.VM, 0, len(lines))
	for _, name := range lines {
		if name == "" {
			continue
		}
		vm := domain.VM{
			ID:     name,
			Name:   name,
			Status: domain.VMStatusUnknown,
			VMType: domain.VMTypeNative,
		}
		// Get state
		stateCmd := exec.CommandContext(ctx, a.virshBin, "domstate", name)
		var stateOut bytes.Buffer
		stateCmd.Stdout = &stateOut
		if err := stateCmd.Run(); err == nil {
			vm.Status = domain.ParseStatus(strings.TrimSpace(stateOut.String()))
		}
		result = append(result, vm)
	}
	return result, nil
}

// listDockerContainers lists Docker containers.
func (a *Adapter) listDockerContainers(ctx context.Context) ([]domain.VM, error) {
	cmd := exec.CommandContext(ctx, "docker", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		// Docker not available, try containerd
		if a.containerdBin != "" {
			cmd = exec.CommandContext(ctx, "ctr", "containers", "list")
			var ctrOut bytes.Buffer
			cmd.Stdout = &ctrOut
			if err := cmd.Run(); err != nil {
				return nil, err
			}
			lines := strings.Split(strings.TrimSpace(ctrOut.String()), "\n")
			result := make([]domain.VM, 0, len(lines))
			for _, line := range lines {
				if line == "" {
					continue
				}
				parts := strings.Fields(line)
				if len(parts) >= 2 {
					result = append(result, domain.VM{
						ID:     parts[0],
						Name:   parts[0],
						Status: domain.VMStatusUnknown,
						VMType: domain.VMTypeNative,
					})
				}
			}
			return result, nil
		}
		return nil, err
	}

	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	result := make([]domain.VM, 0, len(lines))
	for _, line := range lines {
		if line == "" {
			continue
		}
		parts := strings.Split(line, "|")
		if len(parts) >= 3 {
			result = append(result, domain.VM{
				ID:     parts[0],
				Name:   parts[1],
				Status: domain.ParseStatus(parts[2]),
				VMType: domain.VMTypeNative,
			})
		}
	}
	return result, nil
}

// VMStatus returns the status of a Linux VM.
func (a *Adapter) VMStatus(ctx context.Context, id string) (domain.VMStatus, error) {
	if a.virshBin != "" {
		cmd := exec.CommandContext(ctx, a.virshBin, "domstate", id)
		var out bytes.Buffer
		cmd.Stdout = &out
		if err := cmd.Run(); err != nil {
			return domain.VMStatusUnknown, err
		}
		return domain.ParseStatus(strings.TrimSpace(out.String())), nil
	}
	// Try docker
	cmd := exec.CommandContext(ctx, "docker", "inspect", id, "--format", "{{.State.Status}}")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return domain.VMStatusUnknown, err
	}
	return domain.ParseStatus(strings.TrimSpace(out.String())), nil
}

// ExecVM executes a command in a Linux VM.
func (a *Adapter) ExecVM(ctx context.Context, id string, cmd []string, stdin io.Reader, stdout, stderr io.Writer) error {
	execCmd := exec.CommandContext(ctx, "docker", append([]string{"exec", "-i", id}, cmd...)...)
	execCmd.Stdin = stdin
	execCmd.Stdout = stdout
	execCmd.Stderr = stderr
	return execCmd.Run()
}

// GetVMInfo returns detailed VM information.
func (a *Adapter) GetVMInfo(ctx context.Context, id string) (map[string]interface{}, error) {
	cmd := exec.CommandContext(ctx, "docker", "inspect", id)
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		if a.virshBin != "" {
			cmd = exec.CommandContext(ctx, a.virshBin, "dumpxml", id)
			var xmlOut bytes.Buffer
			cmd.Stdout = &xmlOut
			if err := cmd.Run(); err != nil {
				return nil, err
			}
			return map[string]interface{}{
				"xml": xmlOut.String(),
			}, nil
		}
		return nil, err
	}

	var info []map[string]interface{}
	if err := json.Unmarshal(out.Bytes(), &info); err != nil || len(info) == 0 {
		return nil, fmt.Errorf("failed to parse docker inspect output")
	}
	return info[0], nil
}

// createQEMUVM creates a VM using QEMU/KVM.
func (a *Adapter) createQEMUVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	if a.qemuBin == "" {
		return nil, fmt.Errorf("QEMU/KVM not available")
	}

	diskPath := fmt.Sprintf("/var/lib/devenv/qemu/%s.qcow2", name)
	kernelPath := "/var/lib/devenv/kernels/vmlinuz"
	initrdPath := "/var/lib/devenv/kernels/initrd"

	// Create disk image
	createDisk := exec.CommandContext(ctx, "qemu-img", "create", "-f", "qcow2", "-b", "/var/lib/devenv/base.img", diskPath, fmt.Sprintf("%dG", config.DiskGB))
	if err := createDisk.Run(); err != nil {
		// Try creating a new disk
		createDisk = exec.CommandContext(ctx, "qemu-img", "create", "-f", "qcow2", diskPath, fmt.Sprintf("%dG", config.DiskGB))
		if err := createDisk.Run(); err != nil {
			return nil, fmt.Errorf("failed to create disk image: %w", err)
		}
	}

	// Create the VM
	args := []string{
		"-name", name,
		"-m", fmt.Sprintf("%dG", config.MemoryGB),
		"-smp", fmt.Sprintf("%d", config.CPU),
		"-hda", diskPath,
		"-kernel", kernelPath,
		"-initrd", initrdPath,
		"-append", "console=ttyS0 root=/dev/sda1",
		"-nographic",
	}

	cmd := exec.CommandContext(ctx, a.qemuBin, args...)
	cmd.Stdout = &bytes.Buffer{}
	cmd.Stderr = &bytes.Buffer{}
	// Start in background - in real impl would use libvirt or proper daemon

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeNative,
		Config: config,
	}, nil
}

// createKVMMVM creates a VM using KVM/libvirt.
func (a *Adapter) createKVMMVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	xml := fmt.Sprintf(`<domain type='kvm'>
  <name>%s</name>
  <memory unit='G'>%d</memory>
  <vcpu>%d</vcpu>
  <os>
    <type>hvm</type>
  </os>
  <disk type='file'>
    <source file='/var/lib/devenv/kvm/%s.qcow2'/>
    <target dev='hda'/>
  </disk>
</domain>`, name, config.MemoryGB, config.CPU, name)

	// Write XML to temp file
	tmpFile := fmt.Sprintf("/tmp/%s.xml", name)
	if err := exec.CommandContext(ctx, "sh", "-c", fmt.Sprintf("cat > %s << 'EOF'\n%s\nEOF", tmpFile, xml)).Run(); err != nil {
		return nil, fmt.Errorf("failed to create domain XML: %w", err)
	}

	// Define the domain
	cmd := exec.CommandContext(ctx, a.virshBin, "define", tmpFile)
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("failed to define domain: %w", err)
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeNative,
		Config: config,
	}, nil
}

// createFirecrackerVM creates a MicroVM using Firecracker.
func (a *Adapter) createFirecrackerVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	if a.firecrackerBin == "" {
		return nil, fmt.Errorf("Firecracker not available")
	}

	socketPath := fmt.Sprintf("/var/run/firecracker/%s.sock", name)
	kernelPath := "/var/lib/firecracker/vmlinux"
	rootfsPath := fmt.Sprintf("/var/lib/firecracker/%s.rootfs.ext4", name)

	// Create rootfs if it doesn't exist
	if _, err := os.Stat(rootfsPath); os.IsNotExist(err) {
		createRootfs := exec.CommandContext(ctx, "dd", "if=/dev/zero", "of="+rootfsPath, "bs=1M", fmt.Sprintf("count=%d", config.DiskGB))
		if err := createRootfs.Run(); err != nil {
			return nil, fmt.Errorf("failed to create rootfs: %w", err)
		}
		// Format
		if err := exec.CommandContext(ctx, "mkfs.ext4", "-F", rootfsPath).Run(); err != nil {
			return nil, fmt.Errorf("failed to format rootfs: %w", err)
		}
	}

	return &domain.VM{
		ID:     name,
		Name:   name,
		Status: domain.VMStatusCreated,
		VMType: domain.VMTypeMicroVM,
		Config: config,
	}, nil
}

// createContainerVM creates a native container using Docker/containerd.
func (a *Adapter) createContainerVM(ctx context.Context, name string, config domain.VMConfig) (*domain.VM, error) {
	// Try docker first
	dockerBin, _ := exec.LookPath("docker")
	if dockerBin != "" {
		// Pull image if specified
		if config.Image != "" {
			pullCmd := exec.CommandContext(ctx, "docker", "pull", config.Image)
			if err := pullCmd.Run(); err != nil {
				return nil, fmt.Errorf("failed to pull image: %w", err)
			}
		}

		// Create container
		args := []string{"create", "--name", name}
		if config.CPU > 0 {
			args = append(args, "--cpus", fmt.Sprintf("%d", config.CPU))
		}
		if config.MemoryGB > 0 {
			args = append(args, "--memory", fmt.Sprintf("%dg", config.MemoryGB))
		}
		args = append(args, config.Image)

		cmd := exec.CommandContext(ctx, dockerBin, args...)
		cmd.Stdout = &bytes.Buffer{}
		cmd.Stderr = &bytes.Buffer{}
		if err := cmd.Run(); err != nil {
			return nil, fmt.Errorf("failed to create container: %w", err)
		}

		return &domain.VM{
			ID:     name,
			Name:   name,
			Status: domain.VMStatusCreated,
			VMType: domain.VMTypeNative,
			Config: config,
		}, nil
	}

	// Try containerd
	if a.containerdBin != "" {
		// Use ctr to create container
		cmd := exec.CommandContext(ctx, "ctr", "run", "-d", "--name", name, config.Image, "/bin/sh")
		cmd.Stdout = &bytes.Buffer{}
		cmd.Stderr = &bytes.Buffer{}
		if err := cmd.Run(); err != nil {
			return nil, fmt.Errorf("failed to create container: %w", err)
		}

		return &domain.VM{
			ID:     name,
			Name:   name,
			Status: domain.VMStatusRunning,
			VMType: domain.VMTypeNative,
			Config: config,
		}, nil
	}

	return nil, fmt.Errorf("no container runtime available (docker or containerd)")
}
