// Package session answers one question: WHO is this process?
//
// It resolves the launching harness, the harness session id, the terminal
// session the process is attached to, and the dagrun node it is executing. All
// of it is read from the environment and the filesystem, never from a terminal
// screen.
//
// The rule this package exists to enforce: an identity is an observation with
// evidence, never a claim. Every field carries how it was learned, and an id
// that cannot be corroborated on disk is reported as unvalidated rather than
// dressed up as fact.
//
// Why environment variables count as reliable identity: a terminal emulator or
// multiplexer issues its session token to the processes it starts (the same
// class of signal as OSC 7/133 shell integration), so TERM_SESSION_ID and
// TMUX_PANE are host-issued identifiers, not pixels or inference. Nothing here
// captures, reads, or records a screen.
package session

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// Terminal is the terminal session a process is attached to.
type Terminal struct {
	// Kind is the issuing program: iterm2, apple-terminal, tmux, herdr,
	// kitty, windows-terminal, screen, or "" when none was found.
	Kind string `json:"kind,omitempty"`
	// Session is the terminal-level session token (TERM_SESSION_ID and
	// friends). It is stable across the lifetime of the tab/window.
	Session string `json:"session,omitempty"`
	// Pane is the multiplexer pane id, when a multiplexer issued one.
	Pane string `json:"pane,omitempty"`
	// Source names the variable the identity came from, so the card can be
	// audited instead of trusted.
	Source string `json:"source,omitempty"`
}

// Binding ties a process to the dagrun node that spawned it.
type Binding struct {
	Run  string `json:"run,omitempty"`
	Node string `json:"node,omitempty"`
	Dir  string `json:"dir,omitempty"`
	// Source is always "env:DAGRUN_*"; a bare DAGRUN=1 is NOT a binding.
	Source string `json:"source"`
}

// Card is one agent's identity, with the evidence behind every claim.
type Card struct {
	// ReadOnly is always true. This surface observes; it never controls.
	ReadOnly bool `json:"read_only"`

	Host string `json:"host,omitempty"`
	PID  int    `json:"pid,omitempty"`
	PPID int    `json:"ppid,omitempty"`
	CWD  string `json:"cwd,omitempty"`
	Exe  string `json:"exe,omitempty"`

	Harness       string `json:"harness,omitempty"`
	HarnessSource string `json:"harness_source,omitempty"`

	SessionID        string `json:"session_id,omitempty"`
	SessionSource    string `json:"session_source,omitempty"`
	SessionValidated bool   `json:"session_validated"`
	SessionEvidence  string `json:"session_evidence,omitempty"`

	Terminal Terminal `json:"terminal,omitempty"`
	Dagrun   *Binding `json:"dagrun,omitempty"`

	// Unknown lists what could not be established and why. A card with a
	// non-empty Unknown is still useful; a card that hides one is not.
	Unknown    []string `json:"unknown,omitempty"`
	ObservedAt string   `json:"observed_at,omitempty"`
}

// Prober carries the process facts and the on-disk check the resolver is
// allowed to use. Tests inject both, so no resolution path needs a live host.
type Prober struct {
	Host string
	PID  int
	PPID int
	CWD  string
	Exe  string
	Now  time.Time
	// Validate corroborates a claimed harness session id against the
	// harness's own artifact store. It must only stat/glob; reading session
	// content would leak prompts into a monitoring surface.
	Validate func(harness, id string) (evidence string, ok bool)
}

// harnessMarkers are the environment markers that identify a harness family,
// strongest first. It mirrors harness.Launching's ordering, but is expressed
// over an injectable env map so it can be tested.
//
// Kcode is a fork of jcode and reads jcode's store through a shim, so a kcode
// session can carry JCODE_* variables; JCODE_BIN naming kcode is the
// discriminator.
var harnessMarkers = []struct {
	harness string
	keys    []string
	// contains, when set, must appear in the variable's value.
	contains    string
	containsKey string
}{
	{harness: "kcode", containsKey: "JCODE_BIN", contains: "kcode"},
	{harness: "kcode", keys: []string{"KCODE_SESSION_ID"}},
	{harness: "jcode", keys: []string{"JCODE_SESSION_ID", "JCODE_SOCKET"}},
	{harness: "codex", keys: []string{"CODEX_SESSION_ID", "CODEX_HOME"}},
	{harness: "helioslite", keys: []string{"HELIOSLITE_SESSION_ID"}},
	{harness: "forge", keys: []string{"FORGE_SESSION_ID"}},
}

// sessionKeys names the variable that holds the harness's own session id, per
// harness. FORGE_EDITOR is deliberately absent: it is a plugin variable that is
// set in unrelated shells, so it identifies a family but never a session.
var sessionKeys = map[string][]string{
	"kcode":      {"KCODE_SESSION_ID", "JCODE_SESSION_ID"},
	"jcode":      {"JCODE_SESSION_ID"},
	"codex":      {"CODEX_SESSION_ID"},
	"helioslite": {"HELIOSLITE_SESSION_ID"},
	"forge":      {"FORGE_SESSION_ID"},
}

// Resolve builds a card from an environment snapshot. It never panics on a
// missing key and never fabricates a value: what it cannot establish lands in
// Unknown with the reason.
func Resolve(env map[string]string, p Prober) Card {
	c := Card{
		ReadOnly:   true,
		Host:       p.Host,
		PID:        p.PID,
		PPID:       p.PPID,
		CWD:        p.CWD,
		Exe:        p.Exe,
		ObservedAt: observedAt(p.Now),
	}

	c.Harness, c.HarnessSource = detectHarness(env)
	if c.Harness == "" {
		c.Unknown = append(c.Unknown, "harness: no session marker in the environment")
	}

	c.SessionID, c.SessionSource = claimSession(env, c.Harness)
	switch {
	case c.SessionID == "" && c.Harness != "":
		c.Unknown = append(c.Unknown,
			"session: "+c.Harness+" is running but no session-id variable is set")
	case c.SessionID != "":
		if p.Validate != nil {
			evidence, ok := p.Validate(c.Harness, c.SessionID)
			c.SessionValidated = ok
			c.SessionEvidence = evidence
		}
		if !c.SessionValidated {
			if c.SessionEvidence == "" {
				c.SessionEvidence = "no on-disk artifact names this id"
			}
			c.Unknown = append(c.Unknown,
				"session: id is claimed by the environment but unvalidated ("+c.SessionEvidence+")")
		}
	}

	c.Terminal = detectTerminal(env)
	if c.Terminal.Kind == "" {
		c.Unknown = append(c.Unknown, "terminal: no terminal session variable is set")
	}

	c.Dagrun = detectBinding(env)
	if c.Dagrun == nil {
		c.Unknown = append(c.Unknown, "dagrun: process was not spawned by a dagrun node")
	}

	sort.Strings(c.Unknown)
	return c
}

// detectHarness returns the harness family and the variable that proved it.
func detectHarness(env map[string]string) (harness, source string) {
	for _, m := range harnessMarkers {
		if m.containsKey != "" {
			if v, ok := env[m.containsKey]; ok && v != "" && strings.Contains(v, m.contains) {
				return m.harness, "env:" + m.containsKey
			}
			continue
		}
		for _, k := range m.keys {
			if v, ok := env[k]; ok && v != "" {
				return m.harness, "env:" + k
			}
		}
	}
	return "", ""
}

// claimSession returns the session id the environment claims, and the variable
// it came from. "Claimed" is the operative word: validation happens later.
func claimSession(env map[string]string, harness string) (id, source string) {
	for _, k := range sessionKeys[harness] {
		if v, ok := env[k]; ok && plausibleID(v) {
			return v, "env:" + k
		}
	}
	return "", ""
}

// detectTerminal finds the terminal session token, preferring a multiplexer
// over the emulator because the pane is the more specific identity.
func detectTerminal(env map[string]string) Terminal {
	if env["HERDR_ENV"] != "" || env["HERDR_PANE_ID"] != "" {
		return Terminal{Kind: "herdr", Pane: env["HERDR_PANE_ID"], Source: "env:HERDR_PANE_ID"}
	}
	if env["TMUX"] != "" || env["TMUX_PANE"] != "" {
		return Terminal{Kind: "tmux", Pane: env["TMUX_PANE"], Source: "env:TMUX_PANE"}
	}
	if env["STY"] != "" {
		return Terminal{Kind: "screen", Session: env["STY"], Source: "env:STY"}
	}
	// TERM_PROGRAM disambiguates the Apple terminals, which both set
	// TERM_SESSION_ID.
	termProgram := env["TERM_PROGRAM"]
	switch {
	case strings.Contains(termProgram, "iTerm"):
		if v := env["ITERM_SESSION_ID"]; v != "" {
			return Terminal{Kind: "iterm2", Session: v, Source: "env:ITERM_SESSION_ID"}
		}
	case termProgram == "Apple_Terminal":
		if v := env["TERM_SESSION_ID"]; v != "" {
			return Terminal{Kind: "apple-terminal", Session: v, Source: "env:TERM_SESSION_ID"}
		}
	}
	if v := env["ITERM_SESSION_ID"]; v != "" {
		return Terminal{Kind: "iterm2", Session: v, Source: "env:ITERM_SESSION_ID"}
	}
	if env["KITTY_WINDOW_ID"] != "" {
		return Terminal{Kind: "kitty", Session: env["KITTY_WINDOW_ID"], Source: "env:KITTY_WINDOW_ID"}
	}
	if v := env["WT_SESSION"]; v != "" {
		return Terminal{Kind: "windows-terminal", Session: v, Source: "env:WT_SESSION"}
	}
	if v := env["TERM_SESSION_ID"]; v != "" {
		return Terminal{Kind: "apple-terminal", Session: v, Source: "env:TERM_SESSION_ID"}
	}
	return Terminal{}
}

// detectBinding reads the node binding dagrun injects into every child.
func detectBinding(env map[string]string) *Binding {
	run := env["DAGRUN_RUN_ID"]
	node := env["DAGRUN_NODE_ID"]
	if run == "" && node == "" {
		return nil
	}
	return &Binding{Run: run, Node: node, Dir: env["DAGRUN_DIR"], Source: "env:DAGRUN_*"}
}

// plausibleID rejects values that cannot be a session id.
func plausibleID(s string) bool {
	if s == "" || len(s) > 200 {
		return false
	}
	return !strings.ContainsAny(s, " \t\r\n/\\")
}

func observedAt(t time.Time) string {
	if t.IsZero() {
		t = time.Now()
	}
	return t.UTC().Format(time.RFC3339)
}

// ValidateArtifact is the real, filesystem-backed validator. It only stats and
// globs; it never opens a session file, so no prompt content can leak into a
// monitoring surface.
//
// The artifact layouts are the ones observed on this host:
//
//	jcode / kcode  $HOME/.jcode/sessions/<id>.json
//	               $HOME/.kcode/sessions/<id>.json
//	codex          $HOME/.codex/sessions/YYYY/MM/DD/rollout-*<id>*.jsonl
//
// A harness with no documented artifact store (forge, helioslite) returns
// unvalidated with that reason, which is the truth rather than a guess.
func ValidateArtifact(home, harness, id string) (evidence string, ok bool) {
	if home == "" || id == "" {
		return "", false
	}
	switch harness {
	case "jcode", "kcode":
		for _, dir := range []string{
			filepath.Join(home, ".kcode", "sessions"),
			filepath.Join(home, ".jcode", "sessions"),
		} {
			p := filepath.Join(dir, id+".json")
			if _, err := os.Stat(p); err == nil {
				return "artifact:" + p, true
			}
		}
		return "", false
	case "codex":
		// Bounded glob: the full layout is at most YYYY/MM/DD/<file>.
		pattern := filepath.Join(home, ".codex", "sessions", "*", "*", "*", "*"+id+"*")
		if matches, err := filepath.Glob(pattern); err == nil && len(matches) > 0 {
			return "artifact:" + matches[len(matches)-1], true
		}
		return "", false
	default:
		return "no artifact store is known for harness " + harness, false
	}
}
