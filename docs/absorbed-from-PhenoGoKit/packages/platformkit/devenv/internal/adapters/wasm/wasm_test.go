package wasm

import (
	"testing"

	"github.com/KooshaPari/devenv-abstraction/internal/domain"
)

func TestNewWasmtimeAdapter(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "wasmtime" {
		t.Errorf("expected name 'wasmtime', got '%s'", adapter.Name())
	}
}

func TestWasmtimeAdapter_Initialize(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWasmtimeAdapter_CompileModule(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	
	_, err := adapter.CompileModule([]byte{})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWasmtimeAdapter_InstantiateModule(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	
	module := &domain.WasmModule{
		Name:    "test",
		RawData: []byte{},
	}
	
	instance, err := adapter.InstantiateModule(module)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if instance == nil {
		t.Error("expected non-nil instance")
	}
}

func TestWasmtimeAdapter_ExecuteExport(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	
	instance := &domain.WasmInstance{
		Name:    "test",
		Module:  nil,
		Exports: map[string]interface{}{},
	}
	
	_, err := adapter.ExecuteExport(instance, "test_func", []interface{}{})
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestWasmtimeAdapter_Close(t *testing.T) {
	adapter := NewWasmtimeAdapter()
	
	err := adapter.Close()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewWasmerAdapter(t *testing.T) {
	adapter := NewWasmerAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "wasmer" {
		t.Errorf("expected name 'wasmer', got '%s'", adapter.Name())
	}
}

func TestWasmerAdapter_Initialize(t *testing.T) {
	adapter := NewWasmerAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestNewWazeroAdapter(t *testing.T) {
	adapter := NewWazeroAdapter()
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
	if adapter.Name() != "wazero" {
		t.Errorf("expected name 'wazero', got '%s'", adapter.Name())
	}
}

func TestWazeroAdapter_Initialize(t *testing.T) {
	adapter := NewWazeroAdapter()
	
	err := adapter.Initialize()
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}
