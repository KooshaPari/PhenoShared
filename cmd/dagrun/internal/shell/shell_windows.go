//go:build windows

package shell

import "os/exec"

// Command returns the interpreter and arguments for command.
//
// Windows ships no sh. Where Git for Windows (or any other POSIX shell) has put
// one on PATH, keep running under sh -c so existing POSIX-style commands behave
// exactly as they do on unix. Where there is no sh, fall back to cmd /c rather
// than failing every check and hook with "executable file not found".
func Command(command string) (string, []string) {
	if sh, err := exec.LookPath("sh"); err == nil {
		return sh, []string{"-c", command}
	}
	return "cmd", []string{"/c", command}
}
