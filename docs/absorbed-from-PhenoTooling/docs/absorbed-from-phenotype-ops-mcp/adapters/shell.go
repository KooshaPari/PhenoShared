package adapters

import (
	"context"
	"fmt"
	"os/exec"
	"path/filepath"

	"github.com/nanovms/ops-mcp/core"
)

var builtInShellTools = []core.Tool{
	{Name: "health", Description: "Report shell adapter health"},
	{Name: "exec_allowlisted", Description: "Execute an allowlisted shell command"},
}

// ShellDispatcher executes allowlisted shell commands.
type ShellDispatcher struct {
	allowlist map[string]struct{}
	logger    core.Logger
}

// NewShellDispatcher constructs a ShellDispatcher with a normalized allowlist.
func NewShellDispatcher(allowlist []string, logger core.Logger) *ShellDispatcher {
	normalized := make(map[string]struct{}, len(allowlist))
	for _, command := range allowlist {
		cleaned := filepath.Clean(command)
		normalized[cleaned] = struct{}{}
	}

	return &ShellDispatcher{
		allowlist: normalized,
		logger:    logger,
	}
}

// Dispatch executes an allowlisted command with the supplied arguments.
func (d *ShellDispatcher) Dispatch(ctx context.Context, name string, args []string) ([]byte, error) {
	const op = "shell.Dispatch"

	cleaned := filepath.Clean(name)
	if filepath.Base(cleaned) != cleaned {
		return nil, core.WrappedError{Op: op, Err: fmt.Errorf("disallowed command path: %s", name)}
	}
	if _, ok := d.allowlist[cleaned]; !ok {
		return nil, core.WrappedError{Op: op, Err: fmt.Errorf("command not allowlisted: %s", cleaned)}
	}

	if d.logger != nil {
		d.logger.Printf("shell dispatch: %s %v", cleaned, args)
	}

	cmd := exec.CommandContext(ctx, cleaned, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, core.WrappedError{Op: op, Err: err}
	}
	return output, nil
}

// Health reports the adapter status.
func (d *ShellDispatcher) Health(context.Context) core.Status {
	return core.Status{
		Healthy: true,
		Message: "shell ok",
	}
}

// ListTools returns the built-in tools exposed by the shell adapter.
func (d *ShellDispatcher) ListTools() []core.Tool {
	tools := make([]core.Tool, len(builtInShellTools))
	copy(tools, builtInShellTools)
	return tools
}
