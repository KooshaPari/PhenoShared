package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStemOfOkfJson(t *testing.T) {
	got := stemOf(`docs/reference/conformance/fixtures/forge-go-module-026.okf.json`)
	if got != "forge-go-module-026" {
		t.Fatalf("stemOf = %q, want forge-go-module-026", got)
	}
}

func TestValidateMinimalDoc(t *testing.T) {
	doc := map[string]any{
		"okf":       "1.0",
		"source_id": "forge-go-module-026",
		"provenance": map[string]any{
			"source_id": "forge-go-module-026",
		},
		"entities": []any{
			map[string]any{"id": "i", "type": "intent", "label": "intent"},
			map[string]any{"id": "a", "type": "acceptance", "label": "acceptance"},
			map[string]any{"id": "c", "type": "constraint", "label": "constraint"},
			map[string]any{"id": "r", "type": "resource", "label": "resource"},
			map[string]any{"id": "s", "type": "state", "label": "state"},
			map[string]any{"id": "g", "type": "gate", "label": "gate"},
		},
		"relations": []any{
			map[string]any{
				"source": "i",
				"target": "a",
				"type":   "verified_by",
				"provenance": map[string]any{
					"source_id": "forge-go-module-026",
				},
			},
		},
	}
	if err := validate(doc, "forge-go-module-026"); err != nil {
		t.Fatalf("validate: %v", err)
	}
	out, err := emit(doc)
	if err != nil {
		t.Fatalf("emit: %v", err)
	}
	if len(out) == 0 || out[len(out)-1] != '\n' {
		t.Fatalf("emit missing trailing newline")
	}
}

func TestFixtureValidateEmitIfPresent(t *testing.T) {
	// Prefer repo-relative fixture when tests run from adapters/go via `go test`.
	candidates := []string{
		filepath.Join("..", "..", "docs", "reference", "conformance", "fixtures", "forge-go-module-026.okf.json"),
	}
	if root := os.Getenv("CARGO_MANIFEST_DIR"); root != "" {
		candidates = append(candidates, filepath.Join(root, "docs", "reference", "conformance", "fixtures", "forge-go-module-026.okf.json"))
	}

	var path string
	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && !st.IsDir() {
			path = c
			break
		}
	}
	if path == "" {
		t.Skip("forge-go-module-026 fixture not found from adapters/go")
	}

	if code := run([]string{"okf-adapter", "validate", path}); code != 0 {
		t.Fatalf("validate exit %d", code)
	}
	if code := run([]string{"okf-adapter", "emit", path}); code != 0 {
		t.Fatalf("emit exit %d", code)
	}
}
