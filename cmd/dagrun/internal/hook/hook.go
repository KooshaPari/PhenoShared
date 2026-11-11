package hook

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"
)

// defaultTimeout is applied when the caller's context has no deadline.
const defaultTimeout = 60 * time.Second

// maxOutputLen bounds the captured output embedded in an error.
const maxOutputLen = 4000

// waitDelay bounds how long the runner keeps waiting for a hook whose output
// pipe is still held by a process that escaped the killed process group.
const waitDelay = 2 * time.Second

// Hooks are the shell commands a plan node can run around its execution.
type Hooks struct {
	Pre    string `yaml:"pre,omitempty" json:"pre,omitempty"`
	Post   string `yaml:"post,omitempty" json:"post,omitempty"`
	OnFail string `yaml:"on_fail,omitempty" json:"on_fail,omitempty"`
}

// Run executes the hook for a phase ("pre", "post" or "on_fail").
//
// An empty hook for that phase is a no-op. The command runs with `sh -c` in
// dir, with env appended, a timeout (default 60s), and its output captured.
// A failing hook returns an error containing that output.
//
// The hook runs in its own process group so that the deadline kills the whole
// subtree. Killing only the shell leaves a forked child holding the output
// pipe, and the runner then waits for that child instead of returning at the
// deadline.
func Run(ctx context.Context, phase string, h Hooks, dir string, env []string) error {
	var cmd string
	switch phase {
	case "pre":
		cmd = h.Pre
	case "post":
		cmd = h.Post
	case "on_fail":
		cmd = h.OnFail
	default:
		return fmt.Errorf("hook: unknown phase %q", phase)
	}

	if strings.TrimSpace(cmd) == "" {
		return nil
	}

	if ctx == nil {
		ctx = context.Background()
	}
	if _, ok := ctx.Deadline(); !ok {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, defaultTimeout)
		defer cancel()
	}

	c := exec.CommandContext(ctx, "sh", "-c", cmd)
	c.Dir = dir
	c.Env = append(os.Environ(), env...)
	setProcessGroup(c)

	out, err := c.CombinedOutput()
	if err != nil {
		return fmt.Errorf("hook %s failed: %w: %s", phase, err, truncate(string(out), maxOutputLen))
	}
	return nil
}

// DefaultGitCommitHook returns a shell snippet that commits the worktree using
// the message in DAGRUN_COMMIT_MSG.
//
// Two deliberate choices:
//
//  1. The fallback message carries the ledger trailers. A host whose global
//     core.hooksPath installs a commit-message linter rejects a bare message,
//     and because this hook is best-effort that rejection would be invisible:
//     auto-commit would silently do nothing. A message that already satisfies
//     the trailer requirement removes the silent no-op.
//  2. `|| true` keeps the commit best-effort. A node that already verified must
//     not become unverified because a commit was refused, which is the same
//     rule as "a failing hook never masks a verification result" read in the
//     other direction.
//
// root is the worktree to commit, so the snippet works from any cwd.
func DefaultGitCommitHook(root string) string {
	target := "."
	if strings.TrimSpace(root) != "" {
		target = root
	}
	// A real newline inside shell double quotes is preserved, so the trailers
	// land in their own paragraph where git reads them as trailers. An escaped
	// "\n" would reach git as the two characters backslash and n.
	msg := "${DAGRUN_COMMIT_MSG:-dagrun: verified node}\n\n" +
		"tx-agent: ${DAGRUN_TX_AGENT:-jcode}\n" +
		"tx-validated: ${DAGRUN_TX_VALIDATED:-test}"
	return fmt.Sprintf("git -C %s add -A && git -C %s commit -m \"%s\" || true",
		shellQuote(target), shellQuote(target), msg)
}

// shellQuote wraps a path in single quotes so a `$`, backtick or space in a
// worktree path cannot be re-interpreted by the shell. An embedded single quote
// is closed, escaped, and reopened, which is the only portable construction.
func shellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "...(truncated)"
}
