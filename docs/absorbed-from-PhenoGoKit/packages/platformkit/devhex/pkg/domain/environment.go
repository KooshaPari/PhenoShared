// Package domain contains the core hexagonal architecture ports and domain types
// for the devenv-abstraction library.
package domain

import (
	"context"
	"io"
	"time"
)

// Environment is the primary port for dev environment lifecycle operations.
// Adapters implement this interface for each backend (Docker, Podman, Nix, native).
type Environment interface {
	// Start provisions and starts the environment with the provided config.
	Start(ctx context.Context, cfg Config) error
	// Stop shuts down the environment, releasing resources.
	Stop(ctx context.Context) error
	// Status returns the current runtime status of the environment.
	Status(ctx context.Context) (Status, error)
	// Exec runs a command inside the environment and returns the result.
	Exec(ctx context.Context, cmd []string) (ExecResult, error)
	// Logs returns a streaming reader of environment logs.
	Logs(ctx context.Context) (io.ReadCloser, error)
}

// BackendType identifies which environment backend to use.
type BackendType string

const (
	BackendDocker  BackendType = "docker"
	BackendPodman  BackendType = "podman"
	BackendNix     BackendType = "nix"
	BackendNative  BackendType = "native"
)

// Config holds environment provisioning parameters.
type Config struct {
	// Name is a human-readable identifier for this environment instance.
	Name string
	// Backend selects the adapter to use.
	Backend BackendType
	// Image is the container image or Nix flake reference, as applicable.
	Image string
	// Ports lists port mappings to expose from the environment.
	Ports []PortMapping
	// Volumes lists filesystem mounts to attach.
	Volumes []VolumeMount
	// Env contains environment variable overrides.
	Env map[string]string
	// WorkDir is the working directory inside the environment.
	WorkDir string
}

// PortMapping describes a host <-> container port binding.
type PortMapping struct {
	HostPort      int
	ContainerPort int
	Protocol      string // "tcp" or "udp"
}

// VolumeMount describes a host path or named volume attached to the environment.
type VolumeMount struct {
	Source   string // host path or named volume
	Target   string // path inside the environment
	ReadOnly bool
}

// StatusCode enumerates the lifecycle states of an environment.
type StatusCode string

const (
	StatusRunning  StatusCode = "running"
	StatusStopped  StatusCode = "stopped"
	StatusStarting StatusCode = "starting"
	StatusStopping StatusCode = "stopping"
	StatusError    StatusCode = "error"
	StatusUnknown  StatusCode = "unknown"
)

// Status represents the current state of an environment.
type Status struct {
	Code      StatusCode
	Message   string
	StartedAt *time.Time
	StoppedAt *time.Time
	// Metadata holds backend-specific metadata (e.g. container ID, Nix store path).
	Metadata map[string]string
}

// ExecResult holds the output of a command executed inside the environment.
type ExecResult struct {
	ExitCode int
	Stdout   []byte
	Stderr   []byte
	Duration time.Duration
}
