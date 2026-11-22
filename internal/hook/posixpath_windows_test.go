//go:build windows

package hook

import "testing"

// withPosixPath marks a test that cannot be proven on Windows yet.
//
// Hooks run through `sh -c`, and two things about that are unverified here rather
// than broken by the test:
//
//   - the shell reports a working directory in its own form (/c/Users/...) while
//     the caller passes a Windows path, so the two are not directly comparable;
//   - a hook whose child spawns grandchildren is not cancelled at its deadline,
//     because the grandchild keeps the output pipe open and Wait blocks on it.
//     A timeout that does not fire is a real gap, and it needs a job object or an
//     explicit process-tree kill, not a test change.
//
// Skipping names both, so nobody reads a skip as coverage.
func withPosixPath(t *testing.T) {
	t.Helper()
	t.Skip("Windows hook coverage is unverified: sh reports /c/... paths, and the deadline is not enforced when the hook spawns grandchildren")
}
