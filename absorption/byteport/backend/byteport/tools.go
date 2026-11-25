//go:build tools

package main

// Tracking govulncheck as a module dependency means
// `go install golang.org/x/vuln/cmd/govulncheck` (no version suffix) resolves
// the exact version recorded in go.mod/go.sum — the lockfile-enforced,
// reproducible form the CI rules require instead of fetching at install time.
import _ "golang.org/x/vuln/cmd/govulncheck"
