package ports

import (
	"context"
	"io"
	"testing"

	"github.com/kooshapari/devenv-abstraction/internal/domain"
)

// MockRuntimePort is a mock implementation of RuntimePort for testing.
type MockRuntimePort struct {
	nameFunc   func() string
	createFunc func(ctx context.Context, config domain.SandboxConfig) (*domain.Sandbox, error)
	startFunc  func(ctx context.Context, id string) error
	stopFunc   func(ctx context.Context, id string) error
	deleteFunc func(ctx context.Context, id string) error
	listFunc   func(ctx context.Context) ([]domain.Sandbox, error)
	statusFunc func(ctx context.Context, id string) (domain.SandboxStatus, error)
	execFunc   func(ctx context.Context, id string, cmd []string, stdin io.Reader, stdout, stderr io.Writer) error
	pullFunc   func(ctx context.Context, image string) error
}

func (m *MockRuntimePort) Name() string {
	if m.nameFunc != nil {
		return m.nameFunc()
	}
	return "mock"
}

func (m *MockRuntimePort) Create(ctx context.Context, config domain.SandboxConfig) (*domain.Sandbox, error) {
	if m.createFunc != nil {
		return m.createFunc(ctx, config)
	}
	return nil, nil
}

func (m *MockRuntimePort) Start(ctx context.Context, id string) error {
	if m.startFunc != nil {
		return m.startFunc(ctx, id)
	}
	return nil
}

func (m *MockRuntimePort) Stop(ctx context.Context, id string) error {
	if m.stopFunc != nil {
		return m.stopFunc(ctx, id)
	}
	return nil
}

func (m *MockRuntimePort) Delete(ctx context.Context, id string) error {
	if m.deleteFunc != nil {
		return m.deleteFunc(ctx, id)
	}
	return nil
}

func (m *MockRuntimePort) List(ctx context.Context) ([]domain.Sandbox, error) {
	if m.listFunc != nil {
		return m.listFunc(ctx)
	}
	return nil, nil
}

func (m *MockRuntimePort) Status(ctx context.Context, id string) (domain.SandboxStatus, error) {
	if m.statusFunc != nil {
		return m.statusFunc(ctx, id)
	}
	return domain.SandboxStatusCreated, nil
}

func (m *MockRuntimePort) Exec(ctx context.Context, id string, cmd []string, stdin io.Reader, stdout, stderr io.Writer) error {
	if m.execFunc != nil {
		return m.execFunc(ctx, id, cmd, stdin, stdout, stderr)
	}
	return nil
}

func (m *MockRuntimePort) Pull(ctx context.Context, image string) error {
	if m.pullFunc != nil {
		return m.pullFunc(ctx, image)
	}
	return nil
}

// Compile-time interface check
var _ RuntimePort = (*MockRuntimePort)(nil)

func TestRuntimePortInterface(t *testing.T) {
	port := &MockRuntimePort{
		nameFunc: func() string { return "test-runtime" },
		statusFunc: func(ctx context.Context, id string) (domain.SandboxStatus, error) {
			return domain.SandboxStatusRunning, nil
		},
	}

	if port.Name() != "test-runtime" {
		t.Errorf("expected Name=test-runtime, got %s", port.Name())
	}

	status, err := port.Status(context.Background(), "test-id")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if status != domain.SandboxStatusRunning {
		t.Errorf("expected Status=running, got %s", status)
	}
}

// MockImagePort is a mock implementation of ImagePort for testing.
type MockImagePort struct {
	pullFunc       func(ctx context.Context, image string) error
	listImagesFunc func(ctx context.Context) ([]domain.OCIImage, error)
	deleteFunc     func(ctx context.Context, image string) error
}

func (m *MockImagePort) Pull(ctx context.Context, image string) error {
	if m.pullFunc != nil {
		return m.pullFunc(ctx, image)
	}
	return nil
}

func (m *MockImagePort) ListImages(ctx context.Context) ([]domain.OCIImage, error) {
	if m.listImagesFunc != nil {
		return m.listImagesFunc(ctx)
	}
	return nil, nil
}

func (m *MockImagePort) Delete(ctx context.Context, image string) error {
	if m.deleteFunc != nil {
		return m.deleteFunc(ctx, image)
	}
	return nil
}

// Compile-time interface check
var _ ImagePort = (*MockImagePort)(nil)

func TestImagePortInterface(t *testing.T) {
	port := &MockImagePort{
		listImagesFunc: func(ctx context.Context) ([]domain.OCIImage, error) {
			return []domain.OCIImage{
				{Name: "alpine", Tag: "latest"},
				{Name: "ubuntu", Tag: "22.04"},
			}, nil
		},
	}

	images, err := port.ListImages(context.Background())
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if len(images) != 2 {
		t.Errorf("expected 2 images, got %d", len(images))
	}
}

// MockFilesystemPort is a mock implementation of FilesystemPort for testing.
type MockFilesystemPort struct {
	mountFunc      func(ctx context.Context, sandboxID, source, target string, readOnly bool) error
	unmountFunc    func(ctx context.Context, sandboxID, target string) error
	listMountsFunc func(ctx context.Context, sandboxID string) ([]domain.Mount, error)
}

func (m *MockFilesystemPort) Mount(ctx context.Context, sandboxID, source, target string, readOnly bool) error {
	if m.mountFunc != nil {
		return m.mountFunc(ctx, sandboxID, source, target, readOnly)
	}
	return nil
}

func (m *MockFilesystemPort) Unmount(ctx context.Context, sandboxID, target string) error {
	if m.unmountFunc != nil {
		return m.unmountFunc(ctx, sandboxID, target)
	}
	return nil
}

func (m *MockFilesystemPort) ListMounts(ctx context.Context, sandboxID string) ([]domain.Mount, error) {
	if m.listMountsFunc != nil {
		return m.listMountsFunc(ctx, sandboxID)
	}
	return nil, nil
}

// Compile-time interface check
var _ FilesystemPort = (*MockFilesystemPort)(nil)

func TestFilesystemPortInterface(t *testing.T) {
	port := &MockFilesystemPort{
		listMountsFunc: func(ctx context.Context, sandboxID string) ([]domain.Mount, error) {
			return []domain.Mount{
				{Source: "/data", Target: "/app/data"},
			}, nil
		},
	}

	mounts, err := port.ListMounts(context.Background(), "sandbox-123")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if len(mounts) != 1 {
		t.Errorf("expected 1 mount, got %d", len(mounts))
	}
}

// MockNetworkPort is a mock implementation of NetworkPort for testing.
type MockNetworkPort struct {
	createNetworkFunc  func(ctx context.Context, name string, subnet string) error
	deleteNetworkFunc func(ctx context.Context, name string) error
	connectFunc        func(ctx context.Context, sandboxID, network string) error
	disconnectFunc     func(ctx context.Context, sandboxID, network string) error
}

func (m *MockNetworkPort) CreateNetwork(ctx context.Context, name string, subnet string) error {
	if m.createNetworkFunc != nil {
		return m.createNetworkFunc(ctx, name, subnet)
	}
	return nil
}

func (m *MockNetworkPort) DeleteNetwork(ctx context.Context, name string) error {
	if m.deleteNetworkFunc != nil {
		return m.deleteNetworkFunc(ctx, name)
	}
	return nil
}

func (m *MockNetworkPort) Connect(ctx context.Context, sandboxID, network string) error {
	if m.connectFunc != nil {
		return m.connectFunc(ctx, sandboxID, network)
	}
	return nil
}

func (m *MockNetworkPort) Disconnect(ctx context.Context, sandboxID, network string) error {
	if m.disconnectFunc != nil {
		return m.disconnectFunc(ctx, sandboxID, network)
	}
	return nil
}

// Compile-time interface check
var _ NetworkPort = (*MockNetworkPort)(nil)

func TestNetworkPortInterface(t *testing.T) {
	port := &MockNetworkPort{
		createNetworkFunc: func(ctx context.Context, name string, subnet string) error {
			if name == "" {
				return nil // success
			}
			return nil
		},
	}

	err := port.CreateNetwork(context.Background(), "test-net", "10.0.0.0/24")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestPortInterfaceDefinitions(t *testing.T) {
	// These tests verify that all port interfaces are properly defined
	// by creating compile-time checks

	t.Run("RuntimePort has all required methods", func(t *testing.T) {
		var port RuntimePort = &MockRuntimePort{}
		_ = port.Name()
	})

	t.Run("ImagePort has all required methods", func(t *testing.T) {
		var port ImagePort = &MockImagePort{}
		_ = port
	})

	t.Run("FilesystemPort has all required methods", func(t *testing.T) {
		var port FilesystemPort = &MockFilesystemPort{}
		_ = port
	})

	t.Run("NetworkPort has all required methods", func(t *testing.T) {
		var port NetworkPort = &MockNetworkPort{}
		_ = port
	})
}
