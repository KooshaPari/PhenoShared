package cheapllm

import (
	"context"
	"strings"
	"testing"
	"time"
)

// TestNew_Defaults verifies New() returns a valid client with default options.
func TestNew_Defaults(t *testing.T) {
	c, err := New(Options{})
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	if c == nil {
		t.Fatal("New() returned nil client")
	}
	if c.opts.PythonBin != "python3" {
		t.Errorf("default PythonBin = %q, want %q", c.opts.PythonBin, "python3")
	}
	if c.opts.WorkDir != "providers/cheap_llm" {
		t.Errorf("default WorkDir = %q, want %q", c.opts.WorkDir, "providers/cheap_llm")
	}
	if c.opts.Timeout != 30*time.Second {
		t.Errorf("default Timeout = %v, want %v", c.opts.Timeout, 30*time.Second)
	}
	if err := c.Close(); err != nil {
		t.Errorf("Close() error = %v", err)
	}
}

// TestNew_Custom verifies New() respects custom options.
func TestNew_Custom(t *testing.T) {
	c, err := New(Options{
		PythonBin:  "python3.12",
		WorkDir:    "/tmp",
		ConfigPath: "/tmp/config.toml",
		Timeout:    5 * time.Second,
	})
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	if c.opts.PythonBin != "python3.12" {
		t.Errorf("PythonBin = %q, want %q", c.opts.PythonBin, "python3.12")
	}
	if c.opts.WorkDir != "/tmp" {
		t.Errorf("WorkDir = %q, want %q", c.opts.WorkDir, "/tmp")
	}
	if c.opts.ConfigPath != "/tmp/config.toml" {
		t.Errorf("ConfigPath = %q, want %q", c.opts.ConfigPath, "/tmp/config.toml")
	}
	if c.opts.Timeout != 5*time.Second {
		t.Errorf("Timeout = %v, want %v", c.opts.Timeout, 5*time.Second)
	}
}

// TestComplete_ValidationMissingModel verifies the client rejects an empty model.
func TestComplete_ValidationMissingModel(t *testing.T) {
	c, err := New(Options{})
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	defer c.Close()

	_, err = c.Complete(context.Background(), CompletionRequest{
		Messages: []Message{{Role: "user", Content: "hi"}},
	})
	if err == nil {
		t.Fatal("Complete() with empty model should error")
	}
	if !strings.Contains(err.Error(), "model required") {
		t.Errorf("error = %v, want contains %q", err, "model required")
	}
}

// TestComplete_ValidationMissingMessages verifies the client rejects empty messages.
func TestComplete_ValidationMissingMessages(t *testing.T) {
	c, err := New(Options{})
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	defer c.Close()

	_, err = c.Complete(context.Background(), CompletionRequest{
		Model: "minimax/test",
	})
	if err == nil {
		t.Fatal("Complete() with empty messages should error")
	}
	if !strings.Contains(err.Error(), "messages required") {
		t.Errorf("error = %v, want contains %q", err, "messages required")
	}
}
