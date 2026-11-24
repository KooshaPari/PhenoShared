// Package native implements domain.Environment for process-compose / bare-process backends.
package native

import (
	"context"
	"fmt"
	"io"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

// Adapter implements domain.Environment by running processes directly on the host.
// It is primarily used to wrap process-compose or other process orchestrators.
type Adapter struct {
	pid int
}

// New returns a new native process Adapter.
func New() domain.Environment {
	return &Adapter{}
}

// Start launches the process described by cfg on the host.
func (a *Adapter) Start(ctx context.Context, cfg domain.Config) error {
	// TODO(WP04): implement process-compose integration
	return fmt.Errorf("native adapter: Start not yet implemented")
}

// Stop sends SIGTERM to the managed process group.
func (a *Adapter) Stop(ctx context.Context) error {
	if a.pid == 0 {
		return fmt.Errorf("native adapter: no process running")
	}
	// TODO(WP04): implement graceful shutdown
	return fmt.Errorf("native adapter: Stop not yet implemented")
}

// Status checks whether the managed process is alive.
func (a *Adapter) Status(ctx context.Context) (domain.Status, error) {
	if a.pid == 0 {
		return domain.Status{Code: domain.StatusStopped}, nil
	}
	// TODO(WP04): implement /proc check or kill -0
	return domain.Status{Code: domain.StatusUnknown}, fmt.Errorf("native adapter: Status not yet implemented")
}

// Exec runs cmd as a child of the managed environment's working directory.
func (a *Adapter) Exec(ctx context.Context, cmd []string) (domain.ExecResult, error) {
	// TODO(WP04): implement os/exec integration
	return domain.ExecResult{}, fmt.Errorf("native adapter: Exec not yet implemented")
}

// Logs returns a reader over the process stdout/stderr log buffer.
func (a *Adapter) Logs(ctx context.Context) (io.ReadCloser, error) {
	// TODO(WP04): implement log tailing
	return nil, fmt.Errorf("native adapter: Logs not yet implemented")
}
