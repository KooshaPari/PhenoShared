package domain_test

import (
	"context"
	"io"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

// stubEnv is a no-op Environment used for registry tests.
type stubEnv struct{}

func (s *stubEnv) Start(_ context.Context, _ domain.Config) error           { return nil }
func (s *stubEnv) Stop(_ context.Context) error                              { return nil }
func (s *stubEnv) Status(_ context.Context) (domain.Status, error)          { return domain.Status{}, nil }
func (s *stubEnv) Exec(_ context.Context, _ []string) (domain.ExecResult, error) {
	return domain.ExecResult{}, nil
}
func (s *stubEnv) Logs(_ context.Context) (io.ReadCloser, error) { return nil, nil }

// compile-time assertion: stubEnv satisfies domain.Environment
var _ domain.Environment = (*stubEnv)(nil)

func TestRegistry_RegisterAndNew(t *testing.T) {
	tests := []struct {
		name      string
		backend   domain.BackendType
		wantErr   bool
		wantNil   bool
	}{
		{name: "known backend returns env", backend: domain.BackendDocker, wantErr: false, wantNil: false},
		{name: "unknown backend returns error", backend: "unknown", wantErr: true, wantNil: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r := domain.NewRegistry()
			r.Register(domain.BackendDocker, func() domain.Environment { return &stubEnv{} })

			env, err := r.New(tc.backend)
			if tc.wantErr && err == nil {
				t.Fatal("expected error, got nil")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tc.wantNil && env != nil {
				t.Fatal("expected nil env on error")
			}
			if !tc.wantNil && env == nil {
				t.Fatal("expected non-nil env")
			}
		})
	}
}

func TestRegistry_DuplicateRegistrationPanics(t *testing.T) {
	r := domain.NewRegistry()
	r.Register(domain.BackendDocker, func() domain.Environment { return &stubEnv{} })

	defer func() {
		if rec := recover(); rec == nil {
			t.Fatal("expected panic on duplicate registration, got none")
		}
	}()
	r.Register(domain.BackendDocker, func() domain.Environment { return &stubEnv{} })
}

func TestRegistry_Available(t *testing.T) {
	r := domain.NewRegistry()
	if len(r.Available()) != 0 {
		t.Fatal("empty registry should have no available backends")
	}
	r.Register(domain.BackendNix, func() domain.Environment { return &stubEnv{} })
	avail := r.Available()
	if len(avail) != 1 || avail[0] != domain.BackendNix {
		t.Fatalf("expected [nix], got %v", avail)
	}
}
