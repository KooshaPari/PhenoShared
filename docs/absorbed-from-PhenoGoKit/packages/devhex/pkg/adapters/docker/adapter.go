// Package docker implements the domain.Environment port for Docker/Podman backends.
// wraps: github.com/moby/moby/client v0.4.1
package docker

import (
	"context"
	"fmt"
	"io"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
	dockerclient "github.com/moby/moby/client"
)

// Adapter implements domain.Environment backed by the Docker daemon.
type Adapter struct {
	client      *dockerclient.Client
	containerID string
}

// New returns a new Docker Adapter. The Docker client is initialised from
// environment variables (DOCKER_HOST, DOCKER_TLS_VERIFY, etc.) following
// the standard Docker SDK convention.
func New() (domain.Environment, error) {
	cli, err := dockerclient.New(
		dockerclient.FromEnv,
	)
	if err != nil {
		return nil, fmt.Errorf("docker adapter: failed to initialise client: %w", err)
	}
	return &Adapter{client: cli}, nil
}

// MustNew is like New but panics on error. Suitable for use in init() or tests.
func MustNew() domain.Environment {
	a, err := New()
	if err != nil {
		panic(err)
	}
	return a
}

// Start pulls the image (if needed) and creates + starts a container.
func (a *Adapter) Start(ctx context.Context, cfg domain.Config) error {
	// TODO(WP02): implement full pull + create + start flow
	return fmt.Errorf("docker adapter: Start not yet implemented")
}

// Stop stops and removes the managed container.
func (a *Adapter) Stop(ctx context.Context) error {
	if a.containerID == "" {
		return fmt.Errorf("docker adapter: no container running")
	}
	// TODO(WP02): implement stop + remove
	return fmt.Errorf("docker adapter: Stop not yet implemented")
}

// Status inspects the container and maps Docker state to domain.Status.
func (a *Adapter) Status(ctx context.Context) (domain.Status, error) {
	if a.containerID == "" {
		return domain.Status{Code: domain.StatusStopped}, nil
	}
	// TODO(WP02): implement inspect + map
	return domain.Status{Code: domain.StatusUnknown}, fmt.Errorf("docker adapter: Status not yet implemented")
}

// Exec runs cmd inside the container via docker exec.
func (a *Adapter) Exec(ctx context.Context, cmd []string) (domain.ExecResult, error) {
	// TODO(WP03): implement exec
	return domain.ExecResult{}, fmt.Errorf("docker adapter: Exec not yet implemented")
}

// Logs streams container stdout+stderr.
func (a *Adapter) Logs(ctx context.Context) (io.ReadCloser, error) {
	// TODO(WP03): implement log streaming
	return nil, fmt.Errorf("docker adapter: Logs not yet implemented")
}
