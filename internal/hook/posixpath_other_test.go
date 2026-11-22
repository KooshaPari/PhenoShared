//go:build !windows

package hook

import "testing"

// withPosixPath is a no-op off Windows: the hook's working directory and the
// shell's pwd already agree.
func withPosixPath(*testing.T) {}
