package session

import (
	"os"
	"strings"
	"time"
)

// Self resolves the identity of the CURRENT process from the real host: the
// environment it inherited, the executable it is running, and the harness
// artifact store under $HOME.
//
// It is the shared implementation behind `dagrun session`, the self card in
// `dagrun agents`, and the observer banner in the viewer, so all three surfaces
// answer "who is this" the same way instead of three slightly different ones.
//
// Resolve is still the testable half: this function only gathers the probes.
func Self(now time.Time) Card {
	host, _ := os.Hostname()
	exe, _ := os.Executable()
	cwd, _ := os.Getwd()
	home, _ := os.UserHomeDir()
	return Resolve(Environ(), Prober{
		Host: host,
		PID:  os.Getpid(),
		PPID: os.Getppid(),
		CWD:  cwd,
		Exe:  exe,
		Now:  now,
		Validate: func(harness, id string) (string, bool) {
			return ValidateArtifact(home, harness, id)
		},
	})
}

// Environ snapshots the process environment into a map. Duplicate keys keep the
// first occurrence, which is what the C library would return.
func Environ() map[string]string {
	env := make(map[string]string, 64)
	for _, kv := range os.Environ() {
		i := strings.IndexByte(kv, '=')
		if i <= 0 {
			continue
		}
		k := kv[:i]
		if _, ok := env[k]; !ok {
			env[k] = kv[i+1:]
		}
	}
	return env
}
