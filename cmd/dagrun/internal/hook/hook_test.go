package hook

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// A hook registered for one phase must not run for another. Before this test,
// nothing in the package was covered, so a typo in the phase switch would have
// silently run the on-failure hook before every node.
func TestRunDispatchesOnlyTheRequestedPhase(t *testing.T) {
	dir := t.TempDir()
	h := Hooks{Pre: "echo pre > pre.txt", Post: "echo post > post.txt", OnFail: "echo fail > fail.txt"}

	if err := Run(context.Background(), "pre", h, dir, nil); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"pre.txt"} {
		if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
			t.Errorf("%s was not created: %v", name, err)
		}
	}
	for _, name := range []string{"post.txt", "fail.txt"} {
		if _, err := os.Stat(filepath.Join(dir, name)); err == nil {
			t.Errorf("%s was created by the wrong phase", name)
		}
	}
}

func TestRunRejectsAnUnknownPhase(t *testing.T) {
	err := Run(context.Background(), "during", Hooks{Pre: "true"}, t.TempDir(), nil)
	if err == nil {
		t.Fatal("expected an error for an unknown phase")
	}
	if !strings.Contains(err.Error(), "during") {
		t.Errorf("error should name the phase it did not recognise, got %q", err)
	}
}

// An empty hook is a no-op, not a failure. A plan with no hooks must run.
func TestRunWithNoHookIsANoop(t *testing.T) {
	for _, phase := range []string{"pre", "post", "on_fail"} {
		if err := Run(context.Background(), phase, Hooks{}, t.TempDir(), nil); err != nil {
			t.Errorf("phase %q with an empty hook returned %v", phase, err)
		}
	}
}

// A hook runs in the supplied directory, not the caller's.
func TestRunHonoursTheWorkingDirectory(t *testing.T) {
	dir := t.TempDir()
	if err := Run(context.Background(), "pre", Hooks{Pre: "pwd > where.txt"}, dir, nil); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(filepath.Join(dir, "where.txt"))
	if err != nil {
		t.Fatal(err)
	}
	// On macOS /var is a symlink to /private/var, so compare the resolved forms.
	wantResolved, _ := filepath.EvalSymlinks(dir)
	gotResolved, _ := filepath.EvalSymlinks(strings.TrimSpace(string(got)))
	if gotResolved != wantResolved {
		t.Errorf("hook ran in %q, want %q", gotResolved, wantResolved)
	}
}

// Caller-supplied env must win over the inherited environment, because a hook
// exists to receive context from the executor that the shell could not know.
func TestRunAppendsCallerEnv(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("DAGRUN_HOOK_PROBE", "inherited")
	err := Run(context.Background(), "pre",
		Hooks{Pre: "echo \"$DAGRUN_HOOK_PROBE\" > env.txt"},
		dir, []string{"DAGRUN_HOOK_PROBE=from-caller"})
	if err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(filepath.Join(dir, "env.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if strings.TrimSpace(string(got)) != "from-caller" {
		t.Errorf("env = %q, want the caller's value", strings.TrimSpace(string(got)))
	}
}

// A failing hook must surface the command's own output. An operator reading
// "exit status 1" with no stderr has to re-run the hook by hand to learn
// anything, which defeats the point of capturing it.
func TestRunSurfacesFailureOutput(t *testing.T) {
	err := Run(context.Background(), "post",
		Hooks{Post: "echo the-real-reason >&2; exit 3"}, t.TempDir(), nil)
	if err == nil {
		t.Fatal("expected the hook to fail")
	}
	if !strings.Contains(err.Error(), "the-real-reason") {
		t.Errorf("error hides the hook output: %v", err)
	}
	if !strings.Contains(err.Error(), "post") {
		t.Errorf("error should name the phase: %v", err)
	}
}

// A hook that outlives its deadline must be killed, not waited on. Otherwise a
// stuck hook wedges the executor with no node to blame.
func TestRunRespectsTheContextDeadline(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()

	start := time.Now()
	err := Run(ctx, "pre", Hooks{Pre: "sleep 30"}, t.TempDir(), nil)
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("expected the hook to be killed")
	}
	if elapsed > 5*time.Second {
		t.Errorf("hook ran %s; the deadline was not enforced", elapsed)
	}
}

// A hook that leaves a background child behind must not keep the runner
// waiting. The child inherits the output pipe, so waiting for the pipe to
// close waits for the child, not for the hook. This is the case that made the
// deadline unenforced on hosts whose shell forks instead of exec'ing.
func TestRunDeadlineEnforcedWhenHookLeavesABackgroundChild(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()

	start := time.Now()
	err := Run(ctx, "pre", Hooks{Pre: "sleep 30 &"}, t.TempDir(), nil)
	elapsed := time.Since(start)

	if elapsed > 5*time.Second {
		t.Errorf("hook ran %s; the deadline was not enforced", elapsed)
	}
	_ = err
}

// The default commit hook must produce a message a ledger-enforcing pre-commit
// hook accepts. On a host whose global core.hooksPath requires tx-agent and
// tx-validated trailers, the old message ("dagrun: verified node") was rejected
// and the rejection was swallowed by `|| true`, so auto-commit silently did
// nothing.
func TestDefaultGitCommitHookCarriesLedgerTrailers(t *testing.T) {
	cmd := DefaultGitCommitHook("/repo")
	for _, want := range []string{"add -A", "commit -m", "tx-agent:", "tx-validated:"} {
		if !strings.Contains(cmd, want) {
			t.Errorf("default commit hook is missing %q:\n%s", want, cmd)
		}
	}
	if !strings.Contains(cmd, "/repo") {
		t.Errorf("the root argument was ignored:\n%s", cmd)
	}
}

// The strongest statement available: run the snippet for real in a repository
// whose pre-commit hook rejects any message without ledger trailers, the way an
// operator's global core.hooksPath does. Before this fix the commit was refused
// and `|| true` swallowed it, so auto-commit failed silently.
func TestDefaultGitCommitHookSatisfiesALedgerCommitMsgHook(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git is not installed")
	}
	repo := t.TempDir()
	git := func(args ...string) {
		t.Helper()
		c := exec.Command("git",
			append([]string{"-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"}, args...)...)
		c.Dir = repo
		if out, err := c.CombinedOutput(); err != nil {
			t.Fatalf("git %v: %v\n%s", args, err, out)
		}
	}
	git("init")
	git("config", "user.email", "t@example.com")
	git("config", "user.name", "t")

	// A commit-msg hook with the same rule the operator's ledger hook enforces.
	// It must be commit-msg, not pre-commit: git passes the message FILE to
	// commit-msg and nothing to pre-commit, which is the whole reason the
	// operator's ledger hook lives at ~/.githooks/commit-msg.
	hooksDir := filepath.Join(repo, ".githooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}
	body := "#!/bin/sh\n" +
		"if ! grep -q 'tx-agent:' \"$1\"; then echo 'missing tx-agent trailer' >&2; exit 1; fi\n" +
		"if ! grep -q 'tx-validated:' \"$1\"; then echo 'missing tx-validated trailer' >&2; exit 1; fi\n"
	if err := os.WriteFile(filepath.Join(hooksDir, "commit-msg"), []byte(body), 0o755); err != nil {
		t.Fatal(err)
	}
	git("config", "core.hooksPath", hooksDir)

	if err := os.WriteFile(filepath.Join(repo, "artifact.md"), []byte("done\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := Run(context.Background(), "post",
		Hooks{Post: DefaultGitCommitHook(repo)}, repo, nil); err != nil {
		t.Fatalf("the default commit hook errored: %v", err)
	}

	c := exec.Command("git", "log", "-1", "--format=%B")
	c.Dir = repo
	out, err := c.CombinedOutput()
	if err != nil {
		t.Fatalf("no commit was created: %v\n%s", err, out)
	}
	message := string(out)
	for _, want := range []string{"tx-agent:", "tx-validated:"} {
		if !strings.Contains(message, want) {
			t.Errorf("commit message is missing %q:\n%s", want, message)
		}
	}
}

// The default hook is best-effort by design: a verified node must not become
// unverified because a commit failed. That is the opposite of the
// failing-hook-masks-verification bug, and it is deliberate, so it is asserted
// rather than left to a reader's guess.
func TestDefaultGitCommitHookCannotFailANode(t *testing.T) {
	if !strings.Contains(DefaultGitCommitHook("/repo"), "|| true") {
		t.Error("the default commit hook must not be able to fail a node that already verified")
	}
}
