package domain_test

import (
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

// BenchmarkRegistry_New measures the hot-path cost of looking up a registered backend.
func BenchmarkRegistry_New(b *testing.B) {
	r := domain.NewRegistry()
	r.Register(domain.BackendDocker, func() domain.Environment { return &stubEnv{} })

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		env, err := r.New(domain.BackendDocker)
		if err != nil || env == nil {
			b.Fatalf("unexpected: err=%v env=%v", err, env)
		}
	}
}

// BenchmarkRegistry_Available measures the cost of listing registered backends.
func BenchmarkRegistry_Available(b *testing.B) {
	r := domain.NewRegistry()
	r.Register(domain.BackendDocker, func() domain.Environment { return &stubEnv{} })
	r.Register(domain.BackendNix, func() domain.Environment { return &stubEnv{} })

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = r.Available()
	}
}
