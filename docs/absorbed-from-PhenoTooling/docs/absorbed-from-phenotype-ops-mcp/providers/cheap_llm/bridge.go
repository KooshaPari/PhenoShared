// Package cheapllm is a Go bridge around the cheap-llm-mcp Python provider.
//
// Status: scaffold (2026-06-10). The Python implementation lives in
// `cheap_llm_mcp/` (the embedded src-layout package) and exposes an MCP
// server over stdio. The Go host (`phenotype-ops-mcp`) wraps that server
// so that any other Go-side MCP tool can invoke the cheap Haiku-class
// reasoners (Minimax, Kimi, Fireworks) without depending on a separate
// Python process boundary from the user's perspective.
//
// See `phenotype-ops-mcp/CONVERGENCE_PLAN_2026_06_10.md` for the full
// merge plan and follow-up phases.
//
// Usage (Phase 0 — call Python as a subprocess):
//
//	import "github.com/nanovms/ops-mcp/providers/cheap_llm"
//
//	client, err := cheapllm.New(cheapllm.Options{
//	    PythonBin:  "python3.12",
//	    WorkDir:    "providers/cheap_llm",
//	    ConfigPath: "providers/cheap_llm/config.toml",
//	})
//	if err != nil { return err }
//	defer client.Close()
//
//	resp, err := client.Complete(ctx, cheapllm.CompletionRequest{
//	    Model:    "minimax/minimax",
//	    Messages: []cheapllm.Message{{Role: "user", Content: "ping"}},
//	})
package cheapllm

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"time"
)

// Message is a single chat message.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// CompletionRequest is the request payload.
type CompletionRequest struct {
	Model     string    `json:"model"`
	Messages  []Message `json:"messages"`
	MaxTokens int       `json:"max_tokens,omitempty"`
}

// CompletionResponse is the response payload.
type CompletionResponse struct {
	Text         string `json:"text"`
	Model        string `json:"model"`
	Provider     string `json:"provider"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
}

// Options configures the bridge.
type Options struct {
	PythonBin  string        // defaults to "python3"
	WorkDir    string        // dir containing cheap_llm_mcp/ (defaults to "providers/cheap_llm")
	ConfigPath string        // optional TOML config
	Timeout    time.Duration // defaults to 30s
}

// Client is a long-lived bridge to a cheap-llm-mcp Python process.
type Client struct {
	opts Options
	mu   sync.Mutex
	// Phase 0: we spawn the Python CLI in stdio-JSON-RPC mode.
	// Phase 1+: replace with an in-process pyO3 link or gRPC bridge.
}

// New spawns the underlying Python process (or returns an error).
func New(opts Options) (*Client, error) {
	if opts.PythonBin == "" {
		opts.PythonBin = "python3"
	}
	if opts.WorkDir == "" {
		opts.WorkDir = "providers/cheap_llm"
	}
	if opts.Timeout == 0 {
		opts.Timeout = 30 * time.Second
	}
	return &Client{opts: opts}, nil
}

// Close releases resources.
func (c *Client) Close() error {
	return nil
}

// Complete sends a completion request and waits for the response.
//
// Phase 0: shells out to the Python CLI. Replace with in-process pyO3
// or gRPC bridge in Phase 1.
func (c *Client) Complete(ctx context.Context, req CompletionRequest) (CompletionResponse, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if req.Model == "" {
		return CompletionResponse{}, fmt.Errorf("model required")
	}
	if len(req.Messages) == 0 {
		return CompletionResponse{}, fmt.Errorf("messages required")
	}

	// Marshal request as JSON for the Python CLI to read on stdin.
	payload, err := json.Marshal(req)
	if err != nil {
		return CompletionResponse{}, fmt.Errorf("marshal request: %w", err)
	}

	args := []string{"-m", "cheap_llm_mcp.cli", "complete", "--json"}
	cmd := exec.CommandContext(ctx, c.opts.PythonBin, args...)
	cmd.Dir = c.opts.WorkDir
	cmd.Stdin = readerFromBytes(payload)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return CompletionResponse{}, fmt.Errorf("stdout pipe: %w", err)
	}
	if err := cmd.Start(); err != nil {
		return CompletionResponse{}, fmt.Errorf("start python: %w", err)
	}

	// Read the first non-empty JSON object from stdout.
	resp, err := readFirstJSON(stdout)
	if err != nil {
		_ = cmd.Wait()
		return CompletionResponse{}, fmt.Errorf("read response: %w", err)
	}
	if err := cmd.Wait(); err != nil {
		return CompletionResponse{}, fmt.Errorf("python exit: %w", err)
	}
	return resp, nil
}

func readerFromBytes(b []byte) io.Reader {
	return &byteReader{b: b}
}

type byteReader struct {
	b []byte
	i int
}

func (r *byteReader) Read(p []byte) (int, error) {
	if r.i >= len(r.b) {
		return 0, io.EOF
	}
	n := copy(p, r.b[r.i:])
	r.i += n
	return n, nil
}

func readFirstJSON(r io.Reader) (CompletionResponse, error) {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var resp CompletionResponse
		if err := json.Unmarshal(line, &resp); err == nil && resp.Text != "" {
			return resp, nil
		}
	}
	if err := scanner.Err(); err != nil {
		return CompletionResponse{}, fmt.Errorf("scan: %w", err)
	}
	return CompletionResponse{}, fmt.Errorf("no JSON response")
}
