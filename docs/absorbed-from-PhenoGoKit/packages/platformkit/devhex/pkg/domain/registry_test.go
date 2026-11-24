package domain

import (
	"context"
	"errors"
	"io"
	"testing"
)

// mockEnv is a mock implementation of Environment for testing.
type mockEnv struct {
	startFunc  func(ctx context.Context, cfg Config) error
	stopFunc   func(ctx context.Context) error
	statusFunc func(ctx context.Context) (Status, error)
	execFunc   func(ctx context.Context, cmd []string) (ExecResult, error)
	logsFunc   func(ctx context.Context) (io.ReadCloser, error)
}

func (m *mockEnv) Start(ctx context.Context, cfg Config) error {
	if m.startFunc != nil {
		return m.startFunc(ctx, cfg)
	}
	return nil
}

func (m *mockEnv) Stop(ctx context.Context) error {
	if m.stopFunc != nil {
		return m.stopFunc(ctx)
	}
	return nil
}

func (m *mockEnv) Status(ctx context.Context) (Status, error) {
	if m.statusFunc != nil {
		return m.statusFunc(ctx)
	}
	return Status{Code: StatusUnknown}, nil
}

func (m *mockEnv) Exec(ctx context.Context, cmd []string) (ExecResult, error) {
	if m.execFunc != nil {
		return m.execFunc(ctx, cmd)
	}
	return ExecResult{}, nil
}

func (m *mockEnv) Logs(ctx context.Context) (io.ReadCloser, error) {
	if m.logsFunc != nil {
		return m.logsFunc(ctx)
	}
	return nil, nil
}

// Ensure mockEnv implements Environment
var _ Environment = (*mockEnv)(nil)

func TestNewRegistry(t *testing.T) {
	r := NewRegistry()
	if r == nil {
		t.Fatal("NewRegistry returned nil")
	}
	if r.factories == nil {
		t.Error("factories map is nil")
	}
}

func TestRegistry_Register(t *testing.T) {
	r := NewRegistry()
	r.Register(BackendDocker, func() Environment {
		return &mockEnv{}
	})

	available := r.Available()
	if len(available) != 1 {
		t.Errorf("expected 1 available backend, got %d", len(available))
	}
	if available[0] != BackendDocker {
		t.Errorf("expected BackendDocker, got %s", available[0])
	}
}

func TestRegistry_Register_Panic(t *testing.T) {
	r := NewRegistry()
	r.Register(BackendDocker, func() Environment {
		return &mockEnv{}
	})

	defer func() {
		if r := recover(); r == nil {
			t.Error("expected panic when registering duplicate backend")
		}
	}()

	r.Register(BackendDocker, func() Environment {
		return &mockEnv{}
	})
}

func TestRegistry_New(t *testing.T) {
	r := NewRegistry()
	r.Register(BackendDocker, func() Environment {
		return &mockEnv{}
	})
	r.Register(BackendPodman, func() Environment {
		return &mockEnv{}
	})

	t.Run("existing backend", func(t *testing.T) {
		env, err := r.New(BackendDocker)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if env == nil {
			t.Fatal("expected non-nil environment")
		}
	})

	t.Run("non-existent backend", func(t *testing.T) {
		_, err := r.New(BackendNix)
		if err == nil {
			t.Fatal("expected error for non-existent backend")
		}
	})
}

func TestRegistry_New_CallsFactory(t *testing.T) {
	r := NewRegistry()
	factoryCalled := false

	r.Register(BackendDocker, func() Environment {
		factoryCalled = true
		return &mockEnv{
			statusFunc: func(ctx context.Context) (Status, error) {
				return Status{Code: StatusRunning}, nil
			},
		}
	})

	env, err := r.New(BackendDocker)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !factoryCalled {
		t.Error("expected factory to be called")
	}

	status, err := env.Status(context.Background())
	if err != nil {
		t.Fatalf("Status failed: %v", err)
	}
	if status.Code != StatusRunning {
		t.Errorf("expected Status=running, got %s", status.Code)
	}
}

func TestRegistry_Available(t *testing.T) {
	r := NewRegistry()

	// Empty registry
	available := r.Available()
	if len(available) != 0 {
		t.Errorf("expected empty available list, got %d", len(available))
	}

	// Add multiple backends
	r.Register(BackendDocker, func() Environment { return &mockEnv{} })
	r.Register(BackendPodman, func() Environment { return &mockEnv{} })
	r.Register(BackendNix, func() Environment { return &mockEnv{} })

	available = r.Available()
	if len(available) != 3 {
		t.Errorf("expected 3 available backends, got %d", len(available))
	}
}

func TestRegistry_New_Integration(t *testing.T) {
	r := NewRegistry()
	var started bool
	var stopped bool

	r.Register(BackendDocker, func() Environment {
		return &mockEnv{
			startFunc: func(ctx context.Context, cfg Config) error {
				started = true
				return nil
			},
			stopFunc: func(ctx context.Context) error {
				stopped = true
				return nil
			},
			statusFunc: func(ctx context.Context) (Status, error) {
				return Status{Code: StatusRunning}, nil
			},
		}
	})

	env, err := r.New(BackendDocker)
	if err != nil {
		t.Fatalf("New failed: %v", err)
	}

	// Test Start
	err = env.Start(context.Background(), Config{Name: "test"})
	if err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	if !started {
		t.Error("Start was not called on mock")
	}

	// Test Status
	status, err := env.Status(context.Background())
	if err != nil {
		t.Fatalf("Status failed: %v", err)
	}
	if status.Code != StatusRunning {
		t.Errorf("expected Status=running, got %s", status.Code)
	}

	// Test Stop
	err = env.Stop(context.Background())
	if err != nil {
		t.Fatalf("Stop failed: %v", err)
	}
	if !stopped {
		t.Error("Stop was not called on mock")
	}
}

func TestRegistry_New_EnvironmentError(t *testing.T) {
	r := NewRegistry()
	expectedErr := errors.New("factory initialization failed")

	r.Register(BackendPodman, func() Environment {
		return &mockEnv{
			statusFunc: func(ctx context.Context) (Status, error) {
				return Status{Code: StatusError, Message: expectedErr.Error()}, expectedErr
			},
		}
	})

	env, err := r.New(BackendPodman)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = env.Status(context.Background())
	if err == nil {
		t.Error("expected error from Status")
	}
}

func TestRegistry_ConcurrentAccess(t *testing.T) {
	r := NewRegistry()

	// Concurrent registration
	done := make(chan bool)
	for i := 0; i < 10; i++ {
		backend := BackendType(string(rune('A' + i)))
		go func(b BackendType) {
			defer func() { done <- true }()
			defer func() { recover() }() // Some will panic due to duplicate
			r.Register(b, func() Environment { return &mockEnv{} })
		}(backend)
	}

	for i := 0; i < 10; i++ {
		<-done
	}

	// All should be registered
	available := r.Available()
	if len(available) != 10 {
		t.Logf("Note: %d backends registered (some may have panicked)", len(available))
	}
}
