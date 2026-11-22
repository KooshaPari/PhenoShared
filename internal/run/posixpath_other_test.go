//go:build !windows

package run

import "testing"

// withPosixPath is a no-op off Windows: the shell and the tools already agree, so
// there is nothing to reorder.
func withPosixPath(*testing.T) {}
