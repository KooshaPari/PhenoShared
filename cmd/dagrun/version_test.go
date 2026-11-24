package main

import "testing"

// The version line is the one thing a bug report is built on, so both of its
// shapes are pinned here: a plain `go build` reports the source version alone,
// and a stamped build adds the identity it was given.
//
// "Reports the source version alone" is the important half. A binary built
// without a stamp has no commit, and inventing one would be worse than saying
// nothing: every 1.2.0 binary is not the same binary.
func TestVersionLineReportsTheStampedIdentity(t *testing.T) {
	original := Commit
	t.Cleanup(func() { Commit = original })

	Commit = ""
	if got, want := versionLine(), Version; got != want {
		t.Errorf("unstamped versionLine() = %q, want the source version %q", got, want)
	}

	Commit = "abc123def456"
	if got, want := versionLine(), Version+"+abc123def456"; got != want {
		t.Errorf("stamped versionLine() = %q, want %q", got, want)
	}

	Commit = "abc123def456.dirty"
	if got, want := versionLine(), Version+"+abc123def456.dirty"; got != want {
		t.Errorf("dirty versionLine() = %q, want %q", got, want)
	}
}
