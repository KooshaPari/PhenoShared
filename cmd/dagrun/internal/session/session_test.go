package session

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func fixedProber() Prober {
	return Prober{
		Host: "testhost",
		PID:  4242,
		PPID: 1,
		CWD:  "/work",
		Exe:  "/usr/local/bin/dagrun",
		Now:  time.Date(2026, 11, 24, 0, 0, 0, 0, time.UTC),
	}
}

// A card must never invent identity. With nothing in the environment every
// field is empty and every gap is named in Unknown.
func TestResolveBareEnvironmentClaimsNothing(t *testing.T) {
	c := Resolve(map[string]string{"PATH": "/usr/bin"}, fixedProber())

	if !c.ReadOnly {
		t.Error("card must be read-only: this surface observes, it does not control")
	}
	if c.Harness != "" || c.SessionID != "" || c.Terminal.Kind != "" || c.Dagrun != nil {
		t.Fatalf("bare environment produced identity: %+v", c)
	}
	if c.ObservedAt != "2026-11-24T00:00:00Z" {
		t.Errorf("observed_at = %q, want the injected clock", c.ObservedAt)
	}
	for _, want := range []string{"harness:", "terminal:", "dagrun:"} {
		if !hasPrefix(c.Unknown, want) {
			t.Errorf("unknown lacks %q, so the gap is hidden instead of reported: %v", want, c.Unknown)
		}
	}
}

// kcode reads jcode's store through a shim, so a kcode process can carry
// JCODE_*. JCODE_BIN naming kcode is the discriminator and must win.
func TestResolveKcodeWinsOverJcode(t *testing.T) {
	env := map[string]string{
		"JCODE_BIN":        "/opt/kcode/bin/kcode",
		"JCODE_SESSION_ID": "sess-1",
	}
	c := Resolve(env, fixedProber())
	if c.Harness != "kcode" {
		t.Fatalf("harness = %q, want kcode", c.Harness)
	}
	if c.HarnessSource != "env:JCODE_BIN" {
		t.Errorf("harness_source = %q", c.HarnessSource)
	}
	if c.SessionID != "sess-1" || c.SessionSource != "env:JCODE_SESSION_ID" {
		t.Errorf("session = (%q, %q)", c.SessionID, c.SessionSource)
	}
}

// A claimed id with no on-disk corroboration is unvalidated, and the card says
// why rather than promoting the claim.
func TestResolveUnvalidatedSessionIsReported(t *testing.T) {
	env := map[string]string{"CODEX_SESSION_ID": "abc"}
	p := fixedProber()
	p.Validate = func(harness, id string) (string, bool) { return "", false }

	c := Resolve(env, p)
	if c.SessionValidated {
		t.Error("session_validated must stay false without evidence")
	}
	if !strings.Contains(c.SessionEvidence, "no on-disk artifact") {
		t.Errorf("evidence = %q", c.SessionEvidence)
	}
	if !hasPrefix(c.Unknown, "session:") {
		t.Errorf("unvalidated id must land in unknown: %v", c.Unknown)
	}
}

func TestResolveValidatedSessionCarriesEvidence(t *testing.T) {
	env := map[string]string{"CODEX_SESSION_ID": "abc"}
	p := fixedProber()
	p.Validate = func(harness, id string) (string, bool) {
		return "artifact:/home/u/.codex/sessions/2026/11/24/rollout-abc.jsonl", true
	}

	c := Resolve(env, p)
	if !c.SessionValidated || !strings.HasPrefix(c.SessionEvidence, "artifact:") {
		t.Fatalf("validated = %v evidence = %q", c.SessionValidated, c.SessionEvidence)
	}
	if hasPrefix(c.Unknown, "session:") {
		t.Errorf("a validated session must not be listed as unknown: %v", c.Unknown)
	}
}

// The pane is the more specific identity, so a multiplexer outranks the
// emulator that hosts it.
func TestResolveTerminalPrecedence(t *testing.T) {
	cases := []struct {
		name string
		env  map[string]string
		kind string
		pane string
		sess string
	}{
		{
			name: "herdr over tmux and iterm",
			env: map[string]string{
				"HERDR_PANE_ID":    "wA:pK",
				"TMUX_PANE":        "%3",
				"TERM_PROGRAM":     "iTerm.app",
				"ITERM_SESSION_ID": "iterm-1",
			},
			kind: "herdr",
			pane: "wA:pK",
		},
		{
			name: "tmux over iterm",
			env: map[string]string{
				"TMUX_PANE":        "%3",
				"TERM_PROGRAM":     "iTerm.app",
				"ITERM_SESSION_ID": "iterm-1",
			},
			kind: "tmux",
			pane: "%3",
		},
		{
			// Both Apple terminals set TERM_SESSION_ID; TERM_PROGRAM decides.
			name: "apple terminal",
			env: map[string]string{
				"TERM_PROGRAM":     "Apple_Terminal",
				"TERM_SESSION_ID":  "term-1",
				"ITERM_SESSION_ID": "",
			},
			kind: "apple-terminal",
			sess: "term-1",
		},
		{
			name: "windows terminal",
			env:  map[string]string{"WT_SESSION": "wt-1"},
			kind: "windows-terminal",
			sess: "wt-1",
		},
		{
			name: "kitty",
			env:  map[string]string{"KITTY_WINDOW_ID": "7"},
			kind: "kitty",
			sess: "7",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := detectTerminal(c.env)
			if got.Kind != c.kind || got.Pane != c.pane || got.Session != c.sess {
				t.Fatalf("got %+v, want kind=%q pane=%q session=%q", got, c.kind, c.pane, c.sess)
			}
			if got.Source == "" {
				t.Error("terminal identity must name the variable it came from")
			}
		})
	}
}

// A bare DAGRUN=1 means "inside some dagrun run", which is not a binding: it
// cannot name the node, so no card may claim one.
func TestResolveBindingRequiresRunOrNode(t *testing.T) {
	if b := detectBinding(map[string]string{"DAGRUN": "1"}); b != nil {
		t.Fatalf("bare DAGRUN=1 produced a binding: %+v", b)
	}
	b := detectBinding(map[string]string{
		"DAGRUN":         "1",
		"DAGRUN_RUN_ID":  "run-1",
		"DAGRUN_NODE_ID": "1.2",
		"DAGRUN_DIR":     "/runs/x",
	})
	if b == nil || b.Run != "run-1" || b.Node != "1.2" || b.Dir != "/runs/x" {
		t.Fatalf("binding = %+v", b)
	}
}

func TestClaimSessionRejectsImplausibleIDs(t *testing.T) {
	for _, bad := range []string{"", "two words", "/a/path", "a\\b", strings.Repeat("x", 201)} {
		env := map[string]string{"CODEX_SESSION_ID": bad}
		if id, _ := claimSession(env, "codex"); id != "" {
			t.Errorf("accepted %q as a session id", bad)
		}
	}
}

// FORGE_EDITOR is a plugin variable set in unrelated shells: it can identify
// the family but must never be read as a session id.
func TestSessionKeysDoNotIncludeForgeEditor(t *testing.T) {
	for harness, keys := range sessionKeys {
		for _, k := range keys {
			if k == "FORGE_EDITOR" {
				t.Fatalf("%s claims a session from FORGE_EDITOR", harness)
			}
		}
	}
}

// ValidateArtifact only stats and globs, so a missing store is a miss rather
// than an error, and a harness with no known store says exactly that.
func TestValidateArtifactAnswers(t *testing.T) {
	home := t.TempDir()
	store := filepath.Join(home, ".jcode", "sessions")
	if err := os.MkdirAll(store, 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(store, "sess-9.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}

	if ev, ok := ValidateArtifact(home, "jcode", "sess-9"); !ok || !strings.Contains(ev, "sess-9.json") {
		t.Errorf("jcode artifact miss: (%q, %v)", ev, ok)
	}
	if _, ok := ValidateArtifact(home, "jcode", "absent"); ok {
		t.Error("absent id validated")
	}
	if ev, ok := ValidateArtifact(home, "forge", "any"); ok {
		t.Errorf("forge has no artifact store, got (%q, %v)", ev, ok)
	}
	if _, ok := ValidateArtifact("", "jcode", "sess-9"); ok {
		t.Error("empty home must not validate")
	}
}

func hasPrefix(list []string, prefix string) bool {
	for _, s := range list {
		if strings.HasPrefix(s, prefix) {
			return true
		}
	}
	return false
}
