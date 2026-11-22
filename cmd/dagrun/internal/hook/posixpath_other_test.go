//go:build !windows

package hook

// shellPathsComparable is true off Windows: the shell reports the same path form the
// caller supplied, so the reported working directory can be compared directly.
const shellPathsComparable = true
