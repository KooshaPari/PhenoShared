// Package nix implements domain.Environment for Nix flake / nix-shell backends.
package nix

import (
	"context"
	"fmt"
	"io"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

// Adapter implements domain.Environment by spawning nix develop / nix-shell processes.
type Adapter struct {
	shellPID int
}

// New returns a new Nix Adapter.
func New() domain.Environment {
	return &Adapter{}
}

// Start enters the Nix shell described by cfg.Image (a flake URI or shell.nix path).
func (a *Adapter) Start(ctx context.Context, cfg domain.Config) error {
	// TODO(WP05): implement nix develop / nix-shell invocation
	return fmt.Errorf("nix adapter: Start not yet implemented")
}

// Stop exits the Nix shell.
func (a *Adapter) Stop(ctx context.Context) error {
	if a.shellPID == 0 {
		return fmt.Errorf("nix adapter: no shell running")
	}
	// TODO(WP05): implement graceful exit
	return fmt.Errorf("nix adapter: Stop not yet implemented")
}

// Status checks whether the Nix shell process is alive.
func (a *Adapter) Status(ctx context.Context) (domain.Status, error) {
	if a.shellPID == 0 {
		return domain.Status{Code: domain.StatusStopped}, nil
	}
	return domain.Status{Code: domain.StatusUnknown}, fmt.Errorf("nix adapter: Status not yet implemented")
}

// Exec runs cmd inside the Nix environment via nix run or a sub-shell exec.
func (a *Adapter) Exec(ctx context.Context, cmd []string) (domain.ExecResult, error) {
	// TODO(WP05): implement nix run integration
	return domain.ExecResult{}, fmt.Errorf("nix adapter: Exec not yet implemented")
}

// Logs returns a reader over nix shell output.
func (a *Adapter) Logs(ctx context.Context) (io.ReadCloser, error) {
	return nil, fmt.Errorf("nix adapter: Logs not yet implemented")
}
