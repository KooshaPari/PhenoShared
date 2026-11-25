package run

import (
	"strings"

	"github.com/KooshaPari/dagrun/internal/harness"
	"github.com/KooshaPari/dagrun/internal/plan"
)

// nodeEnv is the identity dagrun gives every child process.
//
// It is additive and cannot change how a child behaves: three variables naming
// the run, the node, and the run directory. Without them a child agent session
// knows it is inside *some* dagrun run (DAGRUN=1) but cannot say which node,
// so a console could only show a card and never bind it to the graph.
//
// The values are sanitized because an environment entry cannot carry a NUL and
// a plan is untrusted input: a newline in a run name must not be able to forge
// a second variable.
func nodeEnv(run, nodeID, dir string) []string {
	return []string{
		"DAGRUN_RUN_ID=" + envSafe(run),
		"DAGRUN_NODE_ID=" + envSafe(nodeID),
		"DAGRUN_DIR=" + envSafe(dir),
	}
}

// envSafe strips characters that are not valid in an environment value.
func envSafe(s string) string {
	return strings.Map(func(r rune) rune {
		switch r {
		case 0, '\n', '\r':
			return -1
		}
		return r
	}, s)
}

// recordSession stores the child's own session id when its output named one.
//
// This runs on the same captured tail as usage, so it costs no extra IO. It is
// best-effort by design: a node whose harness prints no id keeps an empty
// Session field, and callers must treat that as UNKNOWN rather than invent one.
func (e *Executor) recordSession(n *plan.Node, epoch int64, captured []byte) {
	id, source := harness.ParseSessionID(captured)
	if id == "" {
		return
	}
	if _, err := e.st.RecordSession(n.ID, e.opt.Owner, epoch, id, source); err != nil {
		e.setErr(err)
	}
}
