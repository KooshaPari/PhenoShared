# Template Workflow Hardening — Session Overview

## Goal
Standardize workflow governance across template repositories and define which workflow checks/actions should remain global vs project-specific.

## Scope
13 repositories in the template family, aligned on PR #4 (`chore/branch-protection-audit-contract`):
- template-commons
- template-domain-service-api
- template-domain-webapp
- template-lang-elixir-hex
- template-lang-go
- template-lang-kotlin
- template-lang-mojo
- template-lang-python
- template-lang-rust
- template-lang-swift
- template-lang-typescript
- template-lang-zig
- template-program-ops

## Current State
- Branch protection audit and policy-gate contracts are consistent across all 13 repositories.
- PR block remains external (`CodeRabbit` check failure), not from branch-protection contract enforcement.
