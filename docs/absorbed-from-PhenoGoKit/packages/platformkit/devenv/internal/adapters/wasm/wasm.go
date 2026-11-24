// Package wasm provides adapters for WASM runtime technologies.
// It supports:
//   - wasmtime (WebAssembly runtime by Bytecode Alliance)
//   - wasmer (Universal WebAssembly runtime)
//   - wazero (Zero-dependency WebAssembly runtime for Go)
package wasm

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

// Adapter provides unified interface to all WASM runtime technologies
type Adapter struct {
	implementations map[domain.WASMType]WASMImplementation
	mu            sync.RWMutex
}

// WASMImplementation is the interface all WASM runtime backends must implement
type WASMImplementation interface {
	// Available checks if the WASM runtime is available on this system
	Available(ctx context.Context) (bool, error)

	// Compile compiles a WASM module
	Compile(ctx context.Context, wasmPath string) ([]byte, error)

	// Instantiate creates an instance of a compiled WASM module
	Instantiate(ctx context.Context, wasmBytes []byte, importObject *WASMImportObject) (*WASMInstance, error)

	// Execute runs a WASM function
	Execute(ctx context.Context, instance *WASMInstance, function string, args ...interface{}) ([]interface{}, error)

	// Stats returns resource usage statistics
	Stats(ctx context.Context, instance *WASMInstance) (*domain.WASMStats, error)
}

// WASMImportObject represents imports for a WASM module
type WASMImportObject struct {
	Env map[string]interface{}
}

// WASMInstance represents a running WASM instance
type WASMInstance struct {
	ID        string
	Module    string
	StartedAt time.Time
	MemoryMB  uint64
}

// NewAdapter creates a new WASM adapter with all available implementations
func NewAdapter() (*Adapter, error) {
	a := &Adapter{
		implementations: make(map[domain.WASMType]WASMImplementation),
	}

	// Register all implementations
	a.implementations[domain.WASMTypeWasmtime] = &wasmtimeAdapter{}
	a.implementations[domain.WASMTypeWasmer] = &wasmerAdapter{}
	a.implementations[domain.WASMTypeWazero] = &wazeroAdapter{}

	return a, nil
}

// AvailableRuntimes returns a list of available WASM runtimes
func (a *Adapter) AvailableRuntimes(ctx context.Context) ([]domain.WASMType, error) {
	a.mu.RLock()
	defer a.mu.RUnlock()

	var available []domain.WASMType
	for wt, impl := range a.implementations {
		ok, err := impl.Available(ctx)
		if err != nil {
			continue
		}
		if ok {
			available = append(available, wt)
		}
	}
	return available, nil
}

// Compile compiles a WASM module using the specified runtime
func (a *Adapter) Compile(ctx context.Context, runtimeType domain.WASMType, wasmPath string) ([]byte, error) {
	a.mu.RLock()
	impl, ok := a.implementations[runtimeType]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported WASM type: %s", runtimeType)
	}

	return impl.Compile(ctx, wasmPath)
}

// Instantiate creates a WASM instance
func (a *Adapter) Instantiate(ctx context.Context, runtimeType domain.WASMType, wasmBytes []byte, importObject *WASMImportObject) (*WASMInstance, error) {
	a.mu.RLock()
	impl, ok := a.implementations[runtimeType]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported WASM type: %s", runtimeType)
	}

	return impl.Instantiate(ctx, wasmBytes, importObject)
}

// Execute runs a WASM function
func (a *Adapter) Execute(ctx context.Context, runtimeType domain.WASMType, instance *WASMInstance, function string, args ...interface{}) ([]interface{}, error) {
	a.mu.RLock()
	impl, ok := a.implementations[runtimeType]
	a.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("unsupported WASM type: %s", runtimeType)
	}

	return impl.Execute(ctx, instance, function, args...)
}

// =============================================================================
// Wasmtime Adapter - Bytecode Alliance WASM runtime
// =============================================================================

type wasmtimeAdapter struct{}

func (w *wasmtimeAdapter) Available(ctx context.Context) (bool, error) {
	// Check for wasmtime CLI
	path, err := exec.LookPath("wasmtime")
	if err != nil {
		paths := []string{
			"/usr/local/bin/wasmtime",
			"/usr/bin/wasmtime",
			filepath.Join(os.Getenv("HOME"), ".cargo/bin/wasmtime"),
		}
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

func (w *wasmtimeAdapter) Compile(ctx context.Context, wasmPath string) ([]byte, error) {
	// Compile WASM to native code using wasmtime
	// This is a simplified version - real implementation would use the wasmtime Go API
	wasmtime := "wasmtime"
	if path, err := exec.LookPath("wasmtime"); err == nil {
		wasmtime = path
	}

	// Check if the file exists
	if _, err := os.Stat(wasmPath); err != nil {
		return nil, fmt.Errorf("WASM file not found: %w", err)
	}

	// Run wasmtime to validate and get module info
	cmd := exec.CommandContext(ctx, wasmtime, "compile", "--print-cranelift", wasmPath)
	output, err := cmd.Output()
	if err != nil {
		// Fall back to just reading the file
		return os.ReadFile(wasmPath)
	}

	return output, nil
}

func (w *wasmtimeAdapter) Instantiate(ctx context.Context, wasmBytes []byte, importObject *WASMImportObject) (*WASMInstance, error) {
	instance := &WASMInstance{
		ID:        fmt.Sprintf("wasmtime-%d", time.Now().UnixNano()),
		Module:    "unknown",
		StartedAt: time.Now(),
		MemoryMB:  0,
	}
	return instance, nil
}

func (w *wasmtimeAdapter) Execute(ctx context.Context, instance *WASMInstance, function string, args ...interface{}) ([]interface{}, error) {
	// Execute a WASM function using wasmtime CLI
	// Real implementation would use the wasmtime Go API
	return nil, fmt.Errorf("Execute requires WASM API integration")
}

func (w *wasmtimeAdapter) Stats(ctx context.Context, instance *WASMInstance) (*domain.WASMStats, error) {
	return &domain.WASMStats{
		InstanceID: instance.ID,
		Type:       domain.WASMTypeWasmtime,
		Timestamp:  time.Now(),
		MemoryMB:    instance.MemoryMB,
	}, nil
}

// =============================================================================
// Wasmer Adapter - Universal WASM runtime
// =============================================================================

type wasmerAdapter struct{}

func (w *wasmerAdapter) Available(ctx context.Context) (bool, error) {
	path, err := exec.LookPath("wasmer")
	if err != nil {
		paths := []string{
			"/usr/local/bin/wasmer",
			"/usr/bin/wasmer",
		}
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

func (w *wasmerAdapter) Compile(ctx context.Context, wasmPath string) ([]byte, error) {
	wasmer := "wasmer"
	if path, err := exec.LookPath("wasmer"); err == nil {
		wasmer = path
	}

	// Validate the WASM file
	cmd := exec.CommandContext(ctx, wasmer, "validate", wasmPath)
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("invalid WASM file: %w", err)
	}

	return os.ReadFile(wasmPath)
}

func (w *wasmerAdapter) Instantiate(ctx context.Context, wasmBytes []byte, importObject *WASMImportObject) (*WASMInstance, error) {
	instance := &WASMInstance{
		ID:        fmt.Sprintf("wasmer-%d", time.Now().UnixNano()),
		Module:    "unknown",
		StartedAt: time.Now(),
		MemoryMB:  0,
	}
	return instance, nil
}

func (w *wasmerAdapter) Execute(ctx context.Context, instance *WASMInstance, function string, args ...interface{}) ([]interface{}, error) {
	return nil, fmt.Errorf("Execute requires WASM API integration")
}

func (w *wasmerAdapter) Stats(ctx context.Context, instance *WASMInstance) (*domain.WASMStats, error) {
	return &domain.WASMStats{
		InstanceID: instance.ID,
		Type:       domain.WASMTypeWasmer,
		Timestamp:  time.Now(),
		MemoryMB:   instance.MemoryMB,
	}, nil
}

// =============================================================================
// Wazero Adapter - Zero-dependency WASM runtime for Go
// =============================================================================

type wazeroAdapter struct{}

func (w *wazeroAdapter) Available(ctx context.Context) (bool, error) {
	// wazero is a Go library, so it's "available" if the imports work
	// For CLI check, look for wazero command
	path, err := exec.LookPath("wazero")
	if err != nil {
		// wazero might be used as a library rather than CLI
		// Check if we can import it
		cmd := exec.CommandContext(ctx, "go", "list", "-m", "github.com/tetratelabs/wazero")
		if err := cmd.Run(); err != nil {
			return false, nil
		}
		return true, nil
	}
	_ = path
	return true, nil
}

func (w *wazeroAdapter) Compile(ctx context.Context, wasmPath string) ([]byte, error) {
	// Read and validate WASM file
	wasmBytes, err := os.ReadFile(wasmPath)
	if err != nil {
		return nil, fmt.Errorf("read WASM file: %w", err)
	}

	// Basic WASM magic number validation
	if len(wasmBytes) < 8 {
		return nil, fmt.Errorf("WASM file too small")
	}
	if string(wasmBytes[:4]) != "\x00asm" {
		return nil, fmt.Errorf("invalid WASM magic number")
	}

	return wasmBytes, nil
}

func (w *wazeroAdapter) Instantiate(ctx context.Context, wasmBytes []byte, importObject *WASMImportObject) (*WASMInstance, error) {
	// Real implementation would use wazero API:
	// ctx := context.Background()
	// r := wazero.NewRuntime(ctx)
	// defer r.Close(ctx)
	// compiled, err := r.CompileModule(ctx, wasmBytes)
	// if err != nil { ... }
	// config := wazero.NewConfig()
	// builder, _ := r.InstantiateModule(ctx, compiled, config)
	// return builder, nil

	instance := &WASMInstance{
		ID:        fmt.Sprintf("wazero-%d", time.Now().UnixNano()),
		Module:    "unknown",
		StartedAt: time.Now(),
		MemoryMB:  0,
	}
	return instance, nil
}

func (w *wazeroAdapter) Execute(ctx context.Context, instance *WASMInstance, function string, args ...interface{}) ([]interface{}, error) {
	// Real implementation would use wazero API:
	// results, err := builder.ExportedFunction(ctx, function).Call(ctx, args...)
	return nil, fmt.Errorf("Execute requires WASM API integration")
}

func (w *wazeroAdapter) Stats(ctx context.Context, instance *WASMInstance) (*domain.WASMStats, error) {
	return &domain.WASMStats{
		InstanceID: instance.ID,
		Type:       domain.WASMTypeWazero,
		Timestamp:  time.Now(),
		MemoryMB:   instance.MemoryMB,
	}, nil
}

// Helper to check if WASM file is valid
func isValidWASM(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	if len(data) < 8 {
		return false
	}
	return string(data[:4]) == "\x00asm"
}

// =============================================================================
// WASM CLI helpers
// =============================================================================

// RunWASM runs a WASM file using the default runtime
func RunWASM(ctx context.Context, wasmPath string, args []string, env []string) (*domain.Process, error) {
	proc := &domain.Process{
		ID:        fmt.Sprintf("wasm-%d", time.Now().UnixNano()),
		Command:   fmt.Sprintf("wasmtime %s", strings.Join(args, " ")),
		StartedAt: time.Now(),
	}

	// Try wasmtime first
	wasmtime := "wasmtime"
	if path, err := exec.LookPath("wasmtime"); err == nil {
		wasmtime = path
	} else if path, err := exec.LookPath("wasmer"); err == nil {
		wasmtime = path
	} else if path, err := exec.LookPath("runw"); err == nil {
		wasmtime = path
	}

	cmdArgs := append([]string{wasmPath}, args...)
	execCmd := exec.CommandContext(ctx, wasmtime, cmdArgs...)
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

// ListExports lists the exported functions from a WASM module
func ListExports(ctx context.Context, wasmPath string) ([]string, error) {
	// Try wasm-objdump or similar tool
	// This is a placeholder - real implementation would use proper tooling
	return []string{}, nil
}
