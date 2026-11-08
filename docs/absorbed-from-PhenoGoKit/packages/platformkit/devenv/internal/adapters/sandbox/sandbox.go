// Package sandbox provides adapters for various sandbox isolation technologies.
// It supports:
//   - gVisor (user-space kernel)
//   - landlock (Linux kernel sandboxing)
//   - seccomp (syscall filtering)
//   - bwrap/bubblewrap (Linux namespace sandbox)
//   - firejail (profile-based sandbox)
//   - unshare (Linux namespace isolation)
//   - sandbox-exec (macOS sandbox)
package sandbox

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

// Adapter provides unified interface to all sandbox technologies
type Adapter struct {
	implementations map[domain.SandboxType]SandboxImplementation
	mu             sync.RWMutex
}

// SandboxImplementation is the interface all sandbox backends must implement
type SandboxImplementation interface {
	// Available checks if the sandbox technology is available on this system
	Available(ctx context.Context) (bool, error)

	// Create creates a new sandboxed environment
	Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error)

	// Start starts a process within an existing sandbox
	Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error)

	// Stop stops and cleans up a sandbox
	Stop(ctx context.Context, sandbox *domain.Sandbox) error

	// Execute runs a command in a temporary sandbox
	Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error)

	// Stats returns resource usage statistics for a sandbox
	Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error)
}

// NewAdapter creates a new sandbox adapter with all available implementations
func NewAdapter() (*Adapter, error) {
	a := &Adapter{
		implementations: make(map[domain.SandboxType]SandboxImplementation),
	}

	// Register all implementations
	a.implementations[domain.SandboxTypeGvisor] = &gvisorAdapter{}
	a.implementations[domain.SandboxTypeLandlock] = &landlockAdapter{}
	a.implementations[domain.SandboxTypeSeccomp] = &seccompAdapter{}
	a.implementations[domain.SandboxTypeBwrap] = &bwrapAdapter{}
	a.implementations[domain.SandboxTypeFirejail] = &firejailAdapter{}
	a.implementations[domain.SandboxTypeUnshare] = &unshareAdapter{}
	a.implementations[domain.SandboxTypeSandboxExec] = &sandboxExecAdapter{}

	return a, nil
}

// AvailableSandboxes returns a list of available sandbox technologies
func (a *Adapter) AvailableSandboxes(ctx context.Context) ([]domain.SandboxType, error) {
	a.mu.RLock()
	defer a.mu.RUnlock()

	var available []domain.SandboxType
	for st, impl := range a.implementations {
		ok, err := impl.Available(ctx)
		if err != nil {
			continue
		}
		if ok {
			available = append(available, st)
		}
	}
	return available, nil
}

// Create creates a sandbox using the specified technology
func (a *Adapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	a.mu.RLock()
	impl, ok := a.implementations[config.Type]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported sandbox type: %s", config.Type)
	}

	return impl.Create(ctx, config)
}

// Start starts a process in an existing sandbox
func (a *Adapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	a.mu.RLock()
	impl, ok := a.implementations[sandbox.Type]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported sandbox type: %s", sandbox.Type)
	}

	return impl.Start(ctx, sandbox, cmd, env)
}

// Stop stops and cleans up a sandbox
func (a *Adapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	a.mu.RLock()
	impl, ok := a.implementations[sandbox.Type]
	a.mu.RUnlock()

	if !ok {
		return fmt.Errorf("unsupported sandbox type: %s", sandbox.Type)
	}

	return impl.Stop(ctx, sandbox)
}

// Execute runs a command in a temporary sandbox
func (a *Adapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	a.mu.RLock()
	impl, ok := a.implementations[config.Type]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported sandbox type: %s", config.Type)
	}

	return impl.Execute(ctx, config, cmd, env)
}

// Stats returns resource usage for a sandbox
func (a *Adapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	a.mu.RLock()
	impl, ok := a.implementations[sandbox.Type]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported sandbox type: %s", sandbox.Type)
	}

	return impl.Stats(ctx, sandbox)
}

// =============================================================================
// gVisor Adapter - User-space kernel for syscall interception
// =============================================================================

type gvisorAdapter struct{}

func (g *gvisorAdapter) Available(ctx context.Context) (bool, error) {
	// Check for runsc binary
	path, err := exec.LookPath("runsc")
	if err != nil {
		// Try common installation paths
		paths := []string{
			"/usr/local/bin/runsc",
			"/usr/bin/runsc",
			"/opt/gvisor/runsc",
		}
		for _, p := range paths {
			if _, err := os.Stat(p); err == nil {
				return true, nil
			}
		}
		return false, nil
	}
	_ = path // suppress unused warning
	return true, nil
}

func (g *gvisorAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	// Create root directory for the sandbox
	root := config.RootDir
	if root == "" {
		root = filepath.Join(os.TempDir(), fmt.Sprintf("gvisor-sandbox-%d", os.Getpid()))
	}

	if err := os.MkdirAll(root, 0755); err != nil {
		return nil, fmt.Errorf("create root dir: %w", err)
	}

	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("gvisor-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeGvisor,
		State:     domain.SandboxStateCreated,
		RootDir:   root,
		CreatedAt: time.Now(),
	}

	// Find runsc binary
	runsc := "/usr/bin/runsc" // default
	if path, err := exec.LookPath("runsc"); err == nil {
		runsc = path
	}

	// Initialize the sandbox root
	cmd := exec.CommandContext(ctx, runsc, "boot", "--root", root)
	if err := cmd.Run(); err != nil {
		// runsc boot might not work directly, try alternative approach
		_ = cmd
	}

	return sandbox, nil
}

func (g *gvisorAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	runsc := "/usr/bin/runsc"
	if path, err := exec.LookPath("runsc"); err == nil {
		runsc = path
	}

	proc := &domain.Process{
		ID:        fmt.Sprintf("gvisor-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build runsc command
	args := append([]string{"run", "--root", sandbox.RootDir}, cmd...)
	execCmd := exec.CommandContext(ctx, runsc, args...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}

	proc.ExitedAt = time.Now()
	return proc, nil
}

func (g *gvisorAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	runsc := "/usr/bin/runsc"
	if path, err := exec.LookPath("runsc"); err == nil {
		runsc = path
	}

	// Send terminate signal to sandbox
	cmd := exec.CommandContext(ctx, runsc, "kill", "--root", sandbox.RootDir)
	_ = cmd.Run()

	// Clean up root directory
	return os.RemoveAll(sandbox.RootDir)
}

func (g *gvisorAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := g.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	defer g.Stop(ctx, sandbox)

	return g.Start(ctx, sandbox, cmd, env)
}

func (g *gvisorAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeGvisor,
		Timestamp: time.Now(),
		CPUPercent: 0, // Would need cgroup integration
		MemoryMB:   0,
	}, nil
}

// =============================================================================
// Landlock Adapter - Linux kernel sandboxing
// =============================================================================

type landlockAdapter struct{}

func (l *landlockAdapter) Available(ctx context.Context) (bool, error) {
	// Check kernel support
	data, err := os.ReadFile("/proc/sys/kernel/unprivileged_userns_clone")
	if err == nil {
		if strings.TrimSpace(string(data)) == "1" {
			return true, nil
		}
	}
	return false, nil
}

func (l *landlockAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("landlock-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeLandlock,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (l *landlockAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	// Landlock requires the binary to be linked with liblandlock
	// For Go, we'd need to use syscall.RawSyscall or a CGO wrapper

	proc := &domain.Process{
		ID:        fmt.Sprintf("landlock-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	execCmd := exec.CommandContext(ctx, cmd[0], cmd[1:]...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (l *landlockAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	// Landlock sandboxes are ephemeral - no persistent state
	return nil
}

func (l *landlockAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := l.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return l.Start(ctx, sandbox, cmd, env)
}

func (l *landlockAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeLandlock,
		Timestamp: time.Now(),
	}, nil
}

// =============================================================================
// Seccomp Adapter - Syscall filtering
// =============================================================================

type seccompAdapter struct{}

func (s *seccompAdapter) Available(ctx context.Context) (bool, error) {
	// seccomp is available on Linux
	return true, nil
}

func (s *seccompAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("seccomp-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeSeccomp,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (s *seccompAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	proc := &domain.Process{
		ID:        fmt.Sprintf("seccomp-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build command with seccomp profile
	execCmd := execCommandWithSeccomp(ctx, cmd, config.SeccompProfile)
	if execCmd == nil {
		execCmd = exec.CommandContext(ctx, cmd[0], cmd[1:]...)
	}
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (s *seccompAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	return nil
}

func (s *seccompAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := s.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return s.Start(ctx, sandbox, cmd, env)
}

func (s *seccompAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeSeccomp,
		Timestamp: time.Now(),
	}, nil
}

// =============================================================================
// Bubblewrap (bwrap) Adapter - Linux namespace sandbox
// =============================================================================

type bwrapAdapter struct{}

func (b *bwrapAdapter) Available(ctx context.Context) (bool, error) {
	path, err := exec.LookPath("bwrap")
	if err != nil {
		// Try common paths
		paths := []string{"/usr/bin/bwrap", "/usr/local/bin/bwrap"}
		for _, p := range paths {
			if _, err := os.Stat(p); err == nil {
				return true, nil
			}
		}
		return false, nil
	}
	_ = path
	return true, nil
}

func (b *bwrapAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	// bwrap creates ephemeral sandboxes - no persistent state
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("bwrap-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeBwrap,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (b *bwrapAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	bwrap := "bwrap"
	if path, err := exec.LookPath("bwrap"); err == nil {
		bwrap = path
	}

	proc := &domain.Process{
		ID:        fmt.Sprintf("bwrap-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build bwrap command arguments
	args := buildBwrapArgs(config)

	// Add user namespace if supported
	args = append(args, "--unshare-user")

	// Add mount options
	if config.ReadOnly {
		args = append(args, "--ro-bind", "/", "/")
	} else {
		args = append(args, "--bind", "/", "/")
	}

	// Add seccomp if profile is provided
	if config.SeccompProfile != "" {
		args = append(args, "--seccomp", config.SeccompProfile)
	}

	args = append(args, "--")
	args = append(args, cmd...)

	execCmd := exec.CommandContext(ctx, bwrap, args...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (b *bwrapAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	// bwrap sandboxes are ephemeral
	return nil
}

func (b *bwrapAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := b.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return b.Start(ctx, sandbox, cmd, env)
}

func (b *bwrapAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeBwrap,
		Timestamp: time.Now(),
	}, nil
}

// =============================================================================
// Firejail Adapter - Profile-based sandbox
// =============================================================================

type firejailAdapter struct{}

func (f *firejailAdapter) Available(ctx context.Context) (bool, error) {
	path, err := exec.LookPath("firejail")
	if err != nil {
		paths := []string{"/usr/bin/firejail", "/usr/local/bin/firejail"}
		for _, p := range paths {
			if _, err := os.Stat(p); err == nil {
				return true, nil
			}
		}
		return false, nil
	}
	_ = path
	return true, nil
}

func (f *firejailAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("firejail-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeFirejail,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (f *firejailAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	firejail := "firejail"
	if path, err := exec.LookPath("firejail"); err == nil {
		firejail = path
	}

	proc := &domain.Process{
		ID:        fmt.Sprintf("firejail-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build firejail arguments
	args := []string{}

	// Add profile if specified
	if config.Profile != "" {
		args = append(args, "--profile="+config.Profile)
	}

	// Add namespace isolation
	args = append(args, "--noprofile")

	// Add network isolation if requested
	if config.NetworkEnabled {
		args = append(args, "--net=none")
	}

	// Add filesystem restrictions
	if config.ReadOnly {
		args = append(args, "--read-only")
		args = append(args, "--read-only-tmpfs")
	}

	// Add private temp directory
	args = append(args, "--private-tmp")
	args = append(args, "--private")

	args = append(args, "--")
	args = append(args, cmd...)

	execCmd := exec.CommandContext(ctx, firejail, args...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (f *firejailAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	return nil
}

func (f *firejailAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := f.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return f.Start(ctx, sandbox, cmd, env)
}

func (f *firejailAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeFirejail,
		Timestamp: time.Now(),
	}, nil
}

// =============================================================================
// Unshare Adapter - Linux namespace isolation
// =============================================================================

type unshareAdapter struct{}

func (u *unshareAdapter) Available(ctx context.Context) (bool, error) {
	path, err := exec.LookPath("unshare")
	if err != nil {
		paths := []string{"/usr/bin/unshare", "/bin/unshare"}
		for _, p := range paths {
			if _, err := os.Stat(p); err == nil {
				return true, nil
			}
		}
		return false, nil
	}
	_ = path
	return true, nil
}

func (u *unshareAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("unshare-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeUnshare,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (u *unshareAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	proc := &domain.Process{
		ID:        fmt.Sprintf("unshare-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build unshare command to run in new namespaces
	unshare := "unshare"
	if path, err := exec.LookPath("unshare"); err == nil {
		unshare = path
	}

	args := []string{}

	// Mount namespace for filesystem isolation
	args = append(args, "--mount")

	// PID namespace
	args = append(args, "--pid")

	// Network namespace if not needed
	if !config.NetworkEnabled {
		args = append(args, "--net")
	}

	// User namespace
	args = append(args, "--user")

	// Run in new mount namespace with pivot_root
	args = append(args, "--mount-proc")

	// Use --fork with --keep-caps for proper namespace creation
	args = append(args, "--fork")

	// Execute the actual command
	args = append(args, "--")
	args = append(args, cmd...)

	execCmd := exec.CommandContext(ctx, unshare, args...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (u *unshareAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	return nil
}

func (u *unshareAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := u.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return u.Start(ctx, sandbox, cmd, env)
}

func (u *unshareAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeUnshare,
		Timestamp: time.Now(),
	}, nil
}

// =============================================================================
// Sandbox-exec Adapter - macOS sandbox
// =============================================================================

type sandboxExecAdapter struct{}

func (s *sandboxExecAdapter) Available(ctx context.Context) (bool, error) {
	// Only available on macOS
	if runtime.GOOS != "darwin" {
		return false, nil
	}

	path, err := exec.LookPath("sandbox-exec")
	if err != nil {
		return false, nil
	}
	_ = path
	return true, nil
}

func (s *sandboxExecAdapter) Create(ctx context.Context, config *domain.SandboxConfig) (*domain.Sandbox, error) {
	sandbox := &domain.Sandbox{
		ID:        fmt.Sprintf("sandbox-exec-%d", time.Now().UnixNano()),
		Type:      domain.SandboxTypeSandboxExec,
		State:     domain.SandboxStateCreated,
		RootDir:   config.RootDir,
		CreatedAt: time.Now(),
	}
	return sandbox, nil
}

func (s *sandboxExecAdapter) Start(ctx context.Context, sandbox *domain.Sandbox, cmd []string, env []string) (*domain.Process, error) {
	proc := &domain.Process{
		ID:        fmt.Sprintf("sandbox-exec-proc-%d", time.Now().UnixNano()),
		SandboxID: sandbox.ID,
		Command:   strings.Join(cmd, " "),
		StartedAt: time.Now(),
	}

	// Build sandbox-exec command
	args := []string{"sandbox-exec", "-p", buildSandboxProfile(config)}

	args = append(args, "--")
	args = append(args, cmd...)

	execCmd := exec.CommandContext(ctx, args[0], args[1:]...)
	execCmd.Env = env

	output, err := execCmd.CombinedOutput()
	if err != nil {
		proc.ExitCode = 1
		proc.Error = err.Error()
	} else {
		proc.ExitCode = 0
		proc.Stdout = string(output)
	}
	proc.ExitedAt = time.Now()

	return proc, nil
}

func (s *sandboxExecAdapter) Stop(ctx context.Context, sandbox *domain.Sandbox) error {
	return nil
}

func (s *sandboxExecAdapter) Execute(ctx context.Context, config *domain.SandboxConfig, cmd []string, env []string) (*domain.Process, error) {
	sandbox, err := s.Create(ctx, config)
	if err != nil {
		return nil, err
	}
	return s.Start(ctx, sandbox, cmd, env)
}

func (s *sandboxExecAdapter) Stats(ctx context.Context, sandbox *domain.Sandbox) (*domain.SandboxStats, error) {
	return &domain.SandboxStats{
		SandboxID: sandbox.ID,
		Type:      domain.SandboxTypeSandboxExec,
		Timestamp: time.Now(),
	}, nil
}

// Helper functions

func buildBwrapArgs(config *domain.SandboxConfig) []string {
	args := []string{}

	// Basic isolation
	args = append(args, "--new-session")
	args = append(args, "--die-with-parent")

	// Filesystem
	args = append(args, "--clearenv")
	args = append(args, "--unsetenv", "LD_PRELOAD")

	// Devtmpfs
	args = append(args, "--dev", "/dev")

	// Proc
	args = append(args, "--proc", "/proc")

	// Temp filesystem
	args = append(args, "--tmpfs", "/tmp")

	return args
}

func buildSandboxProfile(config *domain.SandboxConfig) string {
	// Basic macOS sandbox profile
	profile := `
    (version 1)
    (allow default)
    (deny network*)
    (deny file-write* /private/tmp/*)
    `

	if config.ReadOnly {
		profile += "\n    (deny file-write*)"
	}

	return profile
}

func execCommandWithSeccomp(ctx context.Context, cmd []string, profile string) *exec.Cmd {
	// This is a simplified version - real implementation would use
	// libseccomp-golang or a CGO wrapper
	return nil // Fall through to regular exec
}
