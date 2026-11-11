package workspace

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWorkerBudgetAdmitsUpToBothCaps(t *testing.T) {
	b, err := NewWorkerBudget(4, map[string]int{"a": 2})
	if err != nil {
		t.Fatal(err)
	}
	if !b.Acquire("a") || !b.Acquire("a") {
		t.Fatal("the first two slots in a capped repo must be granted")
	}
	if b.Acquire("a") {
		t.Error("a per-repo cap of 2 admitted a third")
	}
	// An uncapped repo may still use the remaining global capacity.
	if !b.Acquire("b") || !b.Acquire("b") {
		t.Fatal("an uncapped repo must be able to use the remaining global slots")
	}
	if b.Acquire("b") {
		t.Error("the global cap of 4 admitted a fifth slot")
	}
	if b.InUse() != 4 {
		t.Errorf("InUse = %d, want 4", b.InUse())
	}
	if b.InUseFor("a") != 2 {
		t.Errorf("InUseFor(a) = %d, want 2", b.InUseFor("a"))
	}
}

// A repo with no cap of its own is bounded ONLY by the workspace total. This is
// the backward-compatible case: a manifest written before per-repo caps existed
// must behave exactly as it did.
func TestWorkerBudgetFallsBackToTheGlobalCap(t *testing.T) {
	b, err := NewWorkerBudget(3, nil)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 3; i++ {
		if !b.Acquire("only") {
			t.Fatalf("slot %d refused with no per-repo cap", i+1)
		}
	}
	if b.Acquire("only") {
		t.Error("the global cap of 3 admitted a fourth")
	}
}

// A per-repo cap larger than the global one is clamped, not rejected. The global
// number is the operator's promise about total concurrency.
func TestWorkerBudgetClampsAPerRepoCapAboveTheGlobalCap(t *testing.T) {
	b, err := NewWorkerBudget(2, map[string]int{"a": 99})
	if err != nil {
		t.Fatal(err)
	}
	if got := b.capFor("a"); got != 2 {
		t.Fatalf("capFor(a) = %d, want the clamped 2", got)
	}
	for i := 0; i < 2; i++ {
		if !b.Acquire("a") {
			t.Fatalf("slot %d refused below the global cap", i+1)
		}
	}
	if b.Acquire("a") {
		t.Error("a clamped cap of 2 admitted a third")
	}
}

func TestWorkerBudgetRejectsNonsenseCaps(t *testing.T) {
	if _, err := NewWorkerBudget(0, nil); err == nil {
		t.Error("a global cap of 0 must be rejected; it is never what an operator meant")
	}
	if _, err := NewWorkerBudget(-1, nil); err == nil {
		t.Error("a negative global cap must be rejected")
	}
	if _, err := NewWorkerBudget(4, map[string]int{"a": -1}); err == nil {
		t.Error("a negative per-repo cap must be rejected")
	}
}

// Releasing a repo that holds nothing must not go negative, because a deferred
// Release runs on paths where Acquire never happened.
func TestWorkerBudgetReleaseOfUnheldRepoIsANoop(t *testing.T) {
	b, err := NewWorkerBudget(2, nil)
	if err != nil {
		t.Fatal(err)
	}
	b.Release("never-acquired")
	if b.InUse() != 0 || b.InUseFor("never-acquired") != 0 {
		t.Fatalf("release invented capacity: total=%d repo=%d", b.InUse(), b.InUseFor("never-acquired"))
	}
	if !b.Acquire("never-acquired") {
		t.Error("a bogus release used up a slot")
	}
}

// The fairness rule: the least-utilised repo is offered the next slot, so a repo
// being crowded out is not permanently outranked by a busier sibling.
func TestWorkerBudgetRunnablePrefersTheLeastUtilisedRepo(t *testing.T) {
	b, err := NewWorkerBudget(4, nil)
	if err != nil {
		t.Fatal(err)
	}
	repos := []string{"a", "b", "c"}

	// Fill "a" first, as a naive loop over the manifest order would.
	if !b.Acquire("a") {
		t.Fatal("expected to take a slot in a")
	}

	got := b.Runnable(repos)
	if len(got) != 3 {
		t.Fatalf("Runnable returned %v, want all three repos", got)
	}
	if got[0] == "a" {
		t.Errorf("Runnable ranked the busy repo first: %v", got)
	}
	// Untouched repos tie on utilisation, so the tiebreak is the name.
	if got[0] != "b" || got[1] != "c" {
		t.Errorf("Runnable = %v, want [b c a] for a deterministic tiebreak", got)
	}
}

func TestWorkerBudgetRunnableIsEmptyWhenTheGlobalCapIsFull(t *testing.T) {
	b, err := NewWorkerBudget(1, nil)
	if err != nil {
		t.Fatal(err)
	}
	b.Acquire("a")
	if got := b.Runnable([]string{"a", "b"}); len(got) != 0 {
		t.Errorf("Runnable = %v, want nothing when every global slot is held", got)
	}
}

// A repo at its own cap is excluded even when global capacity remains.
func TestWorkerBudgetRunnableExcludesARepoAtItsOwnCap(t *testing.T) {
	b, err := NewWorkerBudget(4, map[string]int{"a": 1})
	if err != nil {
		t.Fatal(err)
	}
	b.Acquire("a")
	got := b.Runnable([]string{"a", "b"})
	if len(got) != 1 || got[0] != "b" {
		t.Errorf("Runnable = %v, want [b]: a is at its own cap", got)
	}
}

// The manifest field must be optional: a workspace written before per-repo caps
// existed still loads, with no cap of its own anywhere.
func TestWorkspaceLoadAcceptsNoPerRepoCaps(t *testing.T) {
	dir := t.TempDir()
	body := `version: 1
name: legacy
repos:
  - path: .
    plan: plan.yaml
`
	path := filepath.Join(dir, "dagrun.workspace.yaml")
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	w, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(w.Repos) != 1 || w.Repos[0].MaxWorkers != 0 {
		t.Fatalf("legacy manifest did not load cleanly: %+v", w.Repos)
	}
	b, err := BudgetFromWorkspace(w)
	if err != nil {
		t.Fatal(err)
	}
	if b.InUse() != 0 {
		t.Fatalf("a fresh budget already holds %d slots", b.InUse())
	}
	if !b.Acquire(".") {
		t.Error("the default global cap must admit at least one worker")
	}
}

func TestWorkspaceLoadReadsPerRepoCaps(t *testing.T) {
	dir := t.TempDir()
	body := `version: 1
name: capped
max_workers: 6
repos:
  - path: a
    plan: plan.yaml
    max_workers: 2
  - path: b
    plan: plan.yaml
`
	path := filepath.Join(dir, "dagrun.workspace.yaml")
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	w, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	b, err := BudgetFromWorkspace(w)
	if err != nil {
		t.Fatal(err)
	}
	if got := b.capFor("a"); got != 2 {
		t.Errorf("repo a cap = %d, want 2", got)
	}
	if got := b.capFor("b"); got != 6 {
		t.Errorf("repo b cap = %d, want the global 6", got)
	}
	if b.Summary([]string{"a", "b"}) == "" {
		t.Error("Summary returned nothing")
	}
}
