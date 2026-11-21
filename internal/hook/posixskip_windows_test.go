//go:build windows

package hook

// posixShellSkip is non-empty on Windows, where hooks run through `sh -c` and the
// test below compares a Windows path against the shell's /c/... form. The hook
// itself works when a POSIX sh is on PATH; what is unverified here is the path
// comparison, so the test says so instead of failing for the wrong reason.
const posixShellSkip = "hooks run through `sh -c`; the Windows path form differs from the shell's /c/... (see the README shell note)"
