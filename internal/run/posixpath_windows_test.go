//go:build windows

package run

import "testing"

// withPosixPath marks a test that cannot be proven on Windows yet.
//
// These templates embed an absolute path straight into a shell command, for
// example `sh -c C:\...\chain.sh {stdin}`. POSIX sh treats the word after -c as
// script text, so the backslashes are consumed as escapes and the script never
// runs: the harness "succeeds" without producing an artifact, which reads like an
// executor failure rather than a quoting defect.
//
// Prepending Git's usr\bin to PATH does not help, because the problem is the path
// form rather than which tools resolve. Making these templates portable (quote and
// convert, or run the script by relative name with the working directory set) is
// its own piece of work, so the tests say they are unverified instead of pretending
// to cover the executor there.
func withPosixPath(t *testing.T) {
	t.Helper()
	t.Skip("Windows exec-template coverage is unverified: the templates embed an absolute Windows path inside `sh -c`, where sh consumes the backslashes")
}
