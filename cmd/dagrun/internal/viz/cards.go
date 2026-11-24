package viz

import (
	"os"
	"time"

	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/session"
	"github.com/KooshaPari/dagrun/internal/store"
)

// attachCards folds the read-only agent cards for this run into the document,
// so the viewer can offer them without a second network call and without a
// second identity implementation.
//
// The cards are the same projection `dagrun agents` and GET /api/agents print,
// built by agents.BuildFrom from the plan and state this document already
// holds. No terminal is read and no screen is captured: every field is an
// environment variable, a process probe, or a stat of a harness artifact.
func attachCards(d *Doc, p *plan.Plan, snap *store.State) {
	if d == nil {
		return
	}
	self := session.Self(time.Now())
	home, _ := os.UserHomeDir()
	src := agents.BuildFrom(p, snap, &self, func(harness, id string) (string, bool) {
		return session.ValidateArtifact(home, harness, id)
	})
	d.Cards(src)
}

// Cards copies a card set onto the document. It is exported so tests and the
// server can attach a set they already built instead of re-deriving one.
func (d *Doc) Cards(src *agents.Doc) {
	if d == nil || src == nil {
		return
	}
	d.Self = src.Self
	d.Agents = append([]agents.Agent(nil), src.Agents...)
	if len(src.Unknown) > 0 {
		d.Unknown = append(d.Unknown, src.Unknown...)
	}
}
