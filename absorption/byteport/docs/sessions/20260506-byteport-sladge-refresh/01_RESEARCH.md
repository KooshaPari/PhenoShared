# Research

## Current State

- Canonical checkout: `BytePort`
- Active branch: `ci/add-golangci-lint`
- Current HEAD before work: `bacb6ac6`
- Canonical local changes before work: workflows, `SPEC.md`, Go modules, and
  backend source files.

## Badge Applicability

The README describes BytePort as a deployment and portfolio platform that uses
an LLM to generate showcase metadata and project descriptions. Sladge
disclosure is appropriate.

## Checkout Notes

The isolated worktree emitted pre-existing LFS pointer warnings for tmp build
artifacts during checkout, but `git status` and `git lfs status` reported no
staged or unstaged changes before the README/session-doc patch.
