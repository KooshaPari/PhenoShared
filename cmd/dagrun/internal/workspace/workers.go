package workspace

import (
	"fmt"
	"sort"
	"strings"
)

// WorkerBudget hands out worker slots across several repositories under two
// caps: one for the whole workspace and one per repo.
//
// Why this exists: a workspace-wide cap alone lets whichever repo has the most
// ready nodes absorb every slot. The work still finishes, but as a serial run of
// one hot repo followed by the others, which is not what a fan-out is for. This
// is the CONCURRENCY budget; the cost budget is a different thing entirely
// (run.SharedBudget) and the two are deliberately not merged: a run can be
// within its token spend and still be monopolised by one repo.
//
// This is deliberately NOT safe for concurrent use. It is a scheduling decision
// made in one place by the code that hands out work, and adding a mutex would
// imply it can be acquired from several goroutines, which is not the contract.
// Guarding it with a lock would hide the real bug: two places deciding.
type WorkerBudget struct {
	global  int
	perRepo map[string]int
	inUse   map[string]int
	total   int
}

// NewWorkerBudget validates the caps up front. A zero or negative global cap is
// rejected, because "0 workers" is never what an operator meant. A per-repo cap
// of 0 or absent means "no cap of its own", so the global cap governs that repo.
func NewWorkerBudget(global int, perRepo map[string]int) (*WorkerBudget, error) {
	if global < 1 {
		return nil, fmt.Errorf("workspace worker budget must be at least 1, got %d", global)
	}
	b := &WorkerBudget{global: global, perRepo: map[string]int{}, inUse: map[string]int{}}
	for repo, cap := range perRepo {
		if cap < 0 {
			return nil, fmt.Errorf("repo %q: worker cap must not be negative, got %d", repo, cap)
		}
		if cap > global {
			// Clamped rather than rejected: the global number is the promise the
			// operator made about total concurrency. A repo asking for more is a
			// smaller mistake than refusing to run at all.
			cap = global
		}
		b.perRepo[repo] = cap
	}
	return b, nil
}

// capFor is the effective cap for a repo. An absent or zero entry means the repo
// has no cap of its own and is bounded only by the workspace total.
func (b *WorkerBudget) capFor(repo string) int {
	if c, ok := b.perRepo[repo]; ok && c > 0 {
		return c
	}
	return b.global
}

// Acquire reserves a slot for repo, reporting whether one was available.
func (b *WorkerBudget) Acquire(repo string) bool {
	if b.total >= b.global {
		return false
	}
	if b.inUse[repo] >= b.capFor(repo) {
		return false
	}
	b.inUse[repo]++
	b.total++
	return true
}

// Release returns a slot. Releasing a repo that holds nothing is a no-op rather
// than an error: a deferred Release runs on paths where Acquire never happened,
// and a negative count there would corrupt every later decision.
func (b *WorkerBudget) Release(repo string) {
	if b.inUse[repo] == 0 {
		return
	}
	b.inUse[repo]--
	b.total--
}

// InUse is the number of slots currently held across every repo.
func (b *WorkerBudget) InUse() int { return b.total }

// InUseFor is the number of slots currently held by one repo.
func (b *WorkerBudget) InUseFor(repo string) int { return b.inUse[repo] }

// Runnable orders the repos that currently have headroom, least-utilised first,
// so a repo being crowded out is offered the next slot instead of being
// permanently outranked by a busier sibling.
//
// Ties break on the repo name, which keeps the order deterministic: a scheduler
// that returns a different order for the same input makes a flaky test and an
// unreproducible run.
func (b *WorkerBudget) Runnable(repos []string) []string {
	if b.total >= b.global {
		return nil
	}
	out := make([]string, 0, len(repos))
	for _, repo := range repos {
		if b.inUse[repo] < b.capFor(repo) {
			out = append(out, repo)
		}
	}
	sort.SliceStable(out, func(i, j int) bool {
		ui, uj := b.inUse[out[i]], b.inUse[out[j]]
		if ui != uj {
			return ui < uj
		}
		return out[i] < out[j]
	})
	return out
}

// Summary is a one-line description of current occupancy, for a run log.
func (b *WorkerBudget) Summary(repos []string) string {
	sorted := append([]string(nil), repos...)
	sort.Strings(sorted)
	parts := make([]string, 0, len(sorted))
	for _, repo := range sorted {
		parts = append(parts, fmt.Sprintf("%s %d/%d", repo, b.inUse[repo], b.capFor(repo)))
	}
	return fmt.Sprintf("%d/%d slots: %s", b.total, b.global, strings.Join(parts, ", "))
}

// BudgetFromWorkspace builds a worker budget from a loaded workspace,
// defaulting the global cap to the number of repos when the manifest does not
// state one. That default is the smallest fan-out that does something useful in
// every repo, and it is a default rather than a hidden policy: the manifest can
// always override it.
func BudgetFromWorkspace(w *Workspace) (*WorkerBudget, error) {
	global := w.MaxWorkers
	if global < 1 {
		global = len(w.Repos)
	}
	if global < 1 {
		global = 1
	}
	per := map[string]int{}
	for _, r := range w.Repos {
		if r.MaxWorkers > 0 {
			per[r.Path] = r.MaxWorkers
		}
	}
	return NewWorkerBudget(global, per)
}
