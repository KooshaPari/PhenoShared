package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/session"
)

// cmdSession prints the validated identity of the CURRENT process: which
// harness launched it, which session that harness claims, which terminal
// session it sits in, and which dagrun node it is executing.
//
// Every claim carries its source, and a harness session id that cannot be
// corroborated in the harness's own artifact store is reported unvalidated.
// That is the whole point: a console can render this card, but it cannot make
// it more certain than the evidence allows.
//
// The command is read-only and does not need a run directory. It is the
// "who am I" primitive that `dagrun agents` composes into a card set.
func cmdSession(args []string) error {
	if hasHelp(args) {
		fmt.Fprint(os.Stdout, `usage: dagrun session [--json]

Print this process's validated session identity.

  --json   machine-readable card on stdout

Fields:
  harness / harness_source        which harness family, and the variable proving it
  session_id / session_source     the id the environment claims, and its variable
  session_validated               true only when an on-disk artifact names that id
  terminal                        terminal session or multiplexer pane, from the env
  dagrun                          run/node binding when spawned by a dagrun node
  unknown                         everything that could not be established, and why
`)
		return nil
	}

	var dir string
	var jsonOut bool
	fs := flagSet("session", &dir, &jsonOut)
	if err := fs.Parse(args); err != nil {
		return err
	}

	card := resolveSelf(time.Now())
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(card)
	}

	fmt.Printf("pid %d  host %s\n", card.PID, orDash(card.Host))
	fmt.Printf("  harness   %s   (%s)\n", orDash(card.Harness), orDash(card.HarnessSource))
	if card.SessionID == "" {
		fmt.Printf("  session   unknown\n")
	} else {
		fmt.Printf("  session   %s   (%s)\n", card.SessionID, orDash(card.SessionSource))
		fmt.Printf("  validated %v\n", card.SessionValidated)
		if card.SessionEvidence != "" {
			fmt.Printf("  evidence  %s\n", card.SessionEvidence)
		}
	}
	if card.Terminal.Kind != "" {
		term := card.Terminal.Kind
		if card.Terminal.Pane != "" {
			term += " pane " + card.Terminal.Pane
		}
		if card.Terminal.Session != "" {
			term += " session " + card.Terminal.Session
		}
		fmt.Printf("  terminal  %s   (%s)\n", term, orDash(card.Terminal.Source))
	}
	if card.Dagrun != nil {
		fmt.Printf("  dagrun    run %s node %s\n", orDash(card.Dagrun.Run), orDash(card.Dagrun.Node))
	}
	if len(card.Unknown) > 0 {
		fmt.Println("  unknown")
		for _, u := range card.Unknown {
			fmt.Printf("    - %s\n", u)
		}
	}
	return nil
}

// resolveSelf builds the current process's card. It is the only place that
// touches the OS for identity, so every other projection stays pure.
func resolveSelf(now time.Time) session.Card {
	host, _ := os.Hostname()
	exe, _ := os.Executable()
	cwd, _ := os.Getwd()
	home, _ := os.UserHomeDir()
	return session.Resolve(environMap(), session.Prober{
		Host: host,
		PID:  os.Getpid(),
		PPID: os.Getppid(),
		CWD:  cwd,
		Exe:  exe,
		Now:  now,
		Validate: func(harness, id string) (string, bool) {
			return session.ValidateArtifact(home, harness, id)
		},
	})
}

// environMap snapshots the environment into a map. Duplicate keys keep the
// first occurrence, which is what the C library would return.
func environMap() map[string]string {
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
