//go:build windows

package run

// posixShellSkip is non-empty on Windows, where the tests below would run shell
// snippets that assume POSIX tools. See the README shell note: Windows needs Git
// Bash/MSYS2/WSL with its usr\bin ahead of System32, and the exec-template path
// is not yet covered there.
const posixShellSkip = "exec templates here are POSIX shell snippets; Windows exec-template coverage is unverified (see the README shell note)"
