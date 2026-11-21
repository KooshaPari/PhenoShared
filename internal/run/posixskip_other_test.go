//go:build !windows

package run

// posixShellSkip is empty off Windows: these snippets are written for the shell
// the platform ships, so they run as intended.
const posixShellSkip = ""
