// Package benchmarks provides performance benchmarks for sandbox technologies
package benchmarks

import (
	"testing"

	"github.com/kooshapari/devenv-abstraction/internal/adapters/linux"
	"github.com/kooshapari/devenv-abstraction/internal/adapters/mac"
	"github.com/kooshapari/devenv-abstraction/internal/adapters/sandbox"
	"github.com/kooshapari/devenv-abstraction/internal/adapters/windows"
	"github.com/kooshapari/devenv-abstraction/internal/adapters/wasm"
)

// BenchmarkSandboxSpinUp benchmarks sandbox spin-up times
func BenchmarkSandboxSpinUp(b *testing.B) {
	adapter := sandbox.NewSandboxAdapter()

	tests := []struct {
		name   string
		sandbox sandbox.SandboxType
	}{
		{"bwrap", sandbox.Bwrap},
		{"firejail", sandbox.Firejail},
		{"gvisor", sandbox.Gvisor},
		{"landlock", sandbox.Landlock},
		{"seccomp", sandbox.Seccomp},
		{"wasmtime", sandbox.Wasmtime},
	}

	for _, tt := range tests {
		b.Run(tt.name, func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				adapter.CreateSandbox(tt.sandbox, sandbox.SandboxConfig{
					Root:    "/tmp/benchmark",
					Timeout: 30,
				})
			}
		})
	}
}

// BenchmarkLinuxAdapter benchmarks Linux VM adapter operations
func BenchmarkLinuxAdapter(b *testing.B) {
	adapter := linux.NewLinuxAdapter()

	b.Run("ListContainers", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.ListVMs(linux.VMTypeNative)
		}
	})

	b.Run("GetRuntimeInfo", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.GetRuntimeInfo()
		}
	})
}

// BenchmarkMacAdapter benchmarks Mac VM adapter operations
func BenchmarkMacAdapter(b *testing.B) {
	adapter := mac.NewMacAdapter()

	b.Run("ListVMs", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.ListVMs(mac.VMTypeLima)
		}
	})

	b.Run("GetRuntimeInfo", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.GetRuntimeInfo()
		}
	})
}

// BenchmarkWindowsAdapter benchmarks Windows VM adapter operations
func BenchmarkWindowsAdapter(b *testing.B) {
	adapter := windows.NewWindowsAdapter()

	b.Run("ListVMs", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.ListVMs(windows.VMTypeWSL2)
		}
	})

	b.Run("GetRuntimeInfo", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.GetRuntimeInfo()
		}
	})
}

// BenchmarkWasmAdapter benchmarks WASM adapter operations
func BenchmarkWasmAdapter(b *testing.B) {
	adapter := wasm.NewWasmAdapter()

	b.Run("ListRuntimes", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.ListRuntimes()
		}
	})

	b.Run("GetRuntimeInfo", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			adapter.GetRuntimeInfo()
		}
	})
}

// Memory benchmarks
func BenchmarkSandboxMemory(b *testing.B) {
	adapter := sandbox.NewSandboxAdapter()

	tests := []struct {
		name   string
		sandbox sandbox.SandboxType
	}{
		{"bwrap", sandbox.Bwrap},
		{"firejail", sandbox.Firejail},
		{"gvisor", sandbox.Gvisor},
		{"wasmtime", sandbox.Wasmtime},
	}

	for _, tt := range tests {
		b.Run(tt.name, func(b *testing.B) {
			b.ResetTimer()
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				adapter.CreateSandbox(tt.sandbox, sandbox.SandboxConfig{
					Root:    "/tmp/benchmark",
					Timeout: 30,
				})
			}
		})
	}
}
