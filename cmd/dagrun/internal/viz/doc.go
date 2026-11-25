package viz

import (
	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/session"
)

// Doc is the whole picture the viewer needs. It is the wire format: keep the
// JSON tags stable, they are read by viewer.html.
type Doc struct {
	Run         string     `json:"run"`
	GeneratedAt string     `json:"generated_at"`
	Intent      string     `json:"intent,omitempty"`
	Stats       Stats      `json:"stats"`
	Nodes       []Node     `json:"nodes"`
	Edges       []Edge     `json:"edges"`
	Waves       [][]string `json:"waves"`

	// Agents is one card per run node, the same set GET /api/agents serves.
	// The viewer renders them beside the graph so a node's session identity is
	// readable without going back to the CLI. Every card is read-only: this
	// document observes agents, it never drives one.
	Agents []agents.Agent `json:"agents,omitempty"`

	// Self is the process that RENDERED this page, not necessarily the one
	// reading it. It exists so the page can say which observer produced it.
	Self *session.Card `json:"self,omitempty"`

	// Unknown records what the card projection could not establish.
	Unknown []string `json:"unknown,omitempty"`
}

// Stats is the header summary. Progress is done/(done+failed+pending+running):
// skipped nodes are structure, not work, so they never move the bar.
type Stats struct {
	Done     int     `json:"done"`
	Failed   int     `json:"failed"`
	Pending  int     `json:"pending"`
	Running  int     `json:"running"`
	Skipped  int     `json:"skipped"`
	Dynamic  int     `json:"dynamic"`
	Progress float64 `json:"progress"`
}

// Node is one rendered unit of work.
type Node struct {
	ID        string `json:"id"`
	Kind      string `json:"kind,omitempty"`
	Title     string `json:"title,omitempty"`
	Status    string `json:"status"`
	Role      string `json:"role,omitempty"`
	Harness   string `json:"harness,omitempty"`
	Provider  string `json:"provider,omitempty"`
	Model     string `json:"model,omitempty"`
	Estimate  string `json:"estimate,omitempty"`
	Branch    string `json:"branch,omitempty"`
	Worktree  string `json:"worktree,omitempty"`
	LastError string `json:"last_error,omitempty"`
	// Session is the child harness session that ran this node, as recorded by
	// the executor. It is an observation, not a guess: when the harness printed
	// no id this stays empty and the panel says so.
	Session       string     `json:"session,omitempty"`
	SessionSource string     `json:"session_source,omitempty"`
	Check         string     `json:"check,omitempty"`
	Wave          int        `json:"wave"`
	Attempts      int        `json:"attempts,omitempty"`
	DurationMS    int64      `json:"duration_ms,omitempty"`
	Dynamic       bool       `json:"dynamic,omitempty"`
	Parent        string     `json:"parent,omitempty"`
	Artifacts     []Artifact `json:"artifacts,omitempty"`
}

// Artifact is one declared output and the verifier's opinion of it.
type Artifact struct {
	Path   string `json:"path"`
	OK     bool   `json:"ok"`
	Code   string `json:"code,omitempty"`
	Detail string `json:"detail,omitempty"`
	SHA256 string `json:"sha256,omitempty"`
	Bytes  int64  `json:"bytes,omitempty"`
}

// Edge is one dependency arrow. Type is "dep" for a declared dependency and
// "fanout" for the parent -> child link of a runtime expansion.
type Edge struct {
	From string `json:"from"`
	To   string `json:"to"`
	Type string `json:"type"`
}
