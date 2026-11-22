//go:build !windows

package plan

// preflightDiscovery is a no-op off Windows: the POSIX tools a `cmd:` work set is
// written against are the ones the shell is built for, so there is nothing to
// disambiguate.
func preflightDiscovery(string) error { return nil }
