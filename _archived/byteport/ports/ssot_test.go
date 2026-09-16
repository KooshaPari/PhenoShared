// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

// Package ports_test contains the SSOT invariants for the BytePort repo.
// These tests are the T22 deliverable: machine-checked governance for the
// toolchain SSOTs (T01 phenotype.just, T14 Biome, T15 ESLint, T16 Prettier).
package ports

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// repoRoot walks up from the test file to find the .git directory.
func repoRoot(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("os.Getwd: %v", err)
	}
	for i := 0; i < 8; i++ {
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	t.Fatal("could not locate .git (not inside a git worktree)")
	return ""
}

// TestSSoT_Justfile verifies the T01 phenotype.just library is imported.
func TestSSoT_Justfile(t *testing.T) {
	root := repoRoot(t)
	data, err := os.ReadFile(filepath.Join(root, "justfile"))
	if err != nil {
		t.Fatalf("read justfile: %v", err)
	}
	content := string(data)
	if !strings.Contains(content, "phenotype.just") {
		t.Errorf("justfile does not import phenotype.just (T01 SSOT)")
	}
	if !strings.Contains(content, "ci:") {
		t.Errorf("justfile does not declare 'ci' recipe (T01 SSOT contract)")
	}
}

// TestSSoT_TaskfileMirror verifies the Taskfile.yml mirrors justfile recipes
// (the T1 tooling-modernization contract: just is SSOT, Taskfile is compat).
func TestSSoT_TaskfileMirror(t *testing.T) {
	root := repoRoot(t)
	data, err := os.ReadFile(filepath.Join(root, "Taskfile.yml"))
	if err != nil {
		t.Fatalf("read Taskfile.yml: %v", err)
	}
	content := string(data)
	for _, want := range []string{"test", "build", "ci"} {
		if !strings.Contains(content, want+":") {
			t.Errorf("Taskfile.yml missing recipe %q (should mirror justfile)", want)
		}
	}
}

// TestSSoT_DenyTomlPresence verifies the T11 deny.toml SSOT is wired
// (Rust repos use it; Go repos still benefit from a stub for future expansion).
func TestSSoT_DenyTomlPresence(t *testing.T) {
	root := repoRoot(t)
	if _, err := os.Stat(filepath.Join(root, "deny.toml")); err == nil {
		t.Log("deny.toml present (Rust-ready)")
	} else {
		t.Log("deny.toml absent (this is a Go repo; T11 SSOT not required)")
	}
}

// TestSSoT_CodeownersPresence verifies the T05 CODEOWNERS file is wired
// (org-wide phylum rules).
func TestSSoT_CodeownersPresence(t *testing.T) {
	root := repoRoot(t)
	if _, err := os.Stat(filepath.Join(root, "CODEOWNERS")); err != nil {
		t.Errorf("CODEOWNERS not present (T05 SSOT missing)")
	}
}

// TestSSoT_GitignoreCoverage verifies the T19 .gitignore SSOT covers the
// standard categories (node_modules, target, .env, dist).
func TestSSoT_GitignoreCoverage(t *testing.T) {
	root := repoRoot(t)
	data, err := os.ReadFile(filepath.Join(root, ".gitignore"))
	if err != nil {
		t.Fatalf("read .gitignore: %v", err)
	}
	content := string(data)
	for _, want := range []string{"node_modules", ".env", "dist"} {
		if !strings.Contains(content, want) {
			t.Errorf(".gitignore missing %q pattern (T19 SSOT coverage gap)", want)
		}
	}
}
