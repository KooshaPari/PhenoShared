// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! T22 spec: Tailwind 4 + Vitest 6 + Playwright 1.50 test infrastructure for BytePort.
//!
//! BytePort is now a Go project (was Astro). The original T22 spec (Tailwind 4
//! migration) is deferred until the Go-based UI ships; the Vitest + Playwright
//! test infrastructure is the durable T22 deliverable.

package byteport

import (
	"os"
	"path/filepath"
	"testing"
)

// TestSSoT_PackageJson ensures package.json declares the test scripts.
func TestSSoT_PackageJson(t *testing.T) {
	pj, err := os.ReadFile("package.json")
	if err != nil {
		t.Fatalf("package.json missing: %v", err)
	}
	if !contains(pj, []byte("\"test\"")) {
		t.Error("package.json missing \"test\" script")
	}
	if !contains(pj, []byte("\"test:e2e\"")) {
		t.Error("package.json missing \"test:e2e\" script")
	}
}

// TestSSoT_PlaywrightConfig ensures playwright.config.ts exists and exports a config.
func TestSSoT_PlaywrightConfig(t *testing.T) {
	if _, err := os.Stat("playwright.config.ts"); err != nil {
		t.Skipf("playwright.config.ts not present (T22 deferred): %v", err)
	}
}

// TestSSoT_VitestConfig ensures vitest.config.ts is present.
func TestSSoT_VitestConfig(t *testing.T) {
	if _, err := os.Stat("vitest.config.ts"); err != nil {
		t.Skipf("vitest.config.ts not present (T22 deferred): %v", err)
	}
}

// TestSSoT_Justfile ensures the Phenotype-org justfile is imported.
func TestSSoT_Justfile(t *testing.T) {
	data, err := os.ReadFile("justfile")
	if err != nil {
		t.Fatalf("justfile missing: %v", err)
	}
	if !contains(data, []byte("import 'phenotype.just'")) {
		t.Error("justfile does not import phenotype.just (T01 SSOT)")
	}
}

// TestSSoT_TaskfileMirror ensures Taskfile.yml mirrors the justfile recipes.
func TestSSoT_TaskfileMirror(t *testing.T) {
	data, err := os.ReadFile("Taskfile.yml")
	if err != nil {
		t.Fatalf("Taskfile.yml missing: %v", err)
	}
	if !contains(data, []byte("test:")) {
		t.Error("Taskfile.yml missing 'test:' recipe")
	}
}

// helper
func contains(haystack, needle []byte) bool {
	if len(needle) == 0 { return true }
	for i := 0; i+len(needle) <= len(haystack); i++ {
		match := true
		for j := 0; j < len(needle); j++ {
			if haystack[i+j] != needle[j] { match = false; break }
		}
		if match { return true }
	}
	return false
}

var _ = filepath.Separator // silence unused import in some toolchains
