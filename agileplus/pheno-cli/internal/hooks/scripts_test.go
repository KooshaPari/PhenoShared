package hooks

import (
	"bytes"
	"io/fs"
	"os"
	"path/filepath"
	"testing"
)

// canonicalHooksDir is the spec-canonical authoring location for the hook
// scripts (WP12: hooks/commit-msg, hooks/pre-commit, hooks/pre-push).
//
// go:embed cannot reference files outside its own package directory, so the
// scripts are mirrored into internal/hooks/scripts/ for embedding. This test
// fails if the mirror ever drifts from the canonical copies.
const canonicalHooksDir = "../../hooks"

func TestEmbeddedScriptsExist(t *testing.T) {
	for _, name := range hookNames {
		if _, err := fs.Stat(hookScripts, filepath.Join("scripts", name)); err != nil {
			t.Errorf("embedded hook %q missing from scripts/: %v", name, err)
		}
	}
}

func TestEmbeddedScriptsMatchCanonical(t *testing.T) {
	for _, name := range hookNames {
		embedded, err := fs.ReadFile(hookScripts, filepath.Join("scripts", name))
		if err != nil {
			t.Errorf("read embedded hook %q: %v", name, err)
			continue
		}

		canonicalPath := filepath.Join(canonicalHooksDir, name)
		canonical, err := os.ReadFile(canonicalPath)
		if err != nil {
			t.Errorf("read canonical hook %q: %v", canonicalPath, err)
			continue
		}

		if !bytes.Equal(embedded, canonical) {
			t.Errorf("embedded hook %q drifted from %s; re-copy the canonical script into internal/hooks/scripts/", name, canonicalPath)
		}
	}
}
