//go:build !windows

package hook

// posixShellSkip is empty off Windows, where the hook's working directory and the
// shell's pwd agree.
const posixShellSkip = ""
