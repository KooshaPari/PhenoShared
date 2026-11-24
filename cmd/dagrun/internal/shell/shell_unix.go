//go:build !windows

// Package shell selects the interpreter that runs an operator-supplied command
// string: a node's check, or a plan hook.
package shell

// Command returns the interpreter and arguments for command.
//
// On every unix it is sh -c, unchanged from the original implementation.
func Command(command string) (string, []string) {
	return "sh", []string{"-c", command}
}
