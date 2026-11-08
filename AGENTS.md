# AGENTS.md — PhenoKits

This file gives AI agents the operating context for working in the **PhenoKits** repository.

## Identity (read this first)

PhenoKits has two roles, and agents must not conflate them:

1. **Umbrella checkout (parent directory).** When this repo is cloned alongside the rest of the Phenotype org, `PhenoKits/` becomes the workspace root — a parent directory holding ~30 sibling repos (AgilePlus, heliosApp, thegent, Civis, bifrost, etc.) as subdirectories for cross-cutting work. In this role PhenoKits has no code of its own; it is just the directory the org is checked out into.
2. **Shared-artifact monorepo (this repo).** `<REDACTED>/PhenoKits` is also a real git repo with 12 categories of shared artifacts (`templates/`, `configs/`, `libs/`, `governance/`, etc.) consumed by every Phenotype project.

`HexaKit/` inside this repo is a **sub-monorepo** included as a git submodule (`.gitmodules` → `https://github.com/KooshaPari/HexaKit.git`) — it has its own Cargo workspace and is excluded from the root `Cargo.toml` (`members = []`). To build it, `cd HexaKit && cargo build`.

If you ever feel uncertain whether a path is part of PhenoKits or a sibling repo, check whether the parent has its own `.git` directory — sibling repos do; PhenoKits subdirectories do not.

## How to work here

- **Do not add a workspace member to the root `Cargo.toml`.** It intentionally excludes `templates/`, `template-domain/`, `template-program-ops/`, `HexaKit/`, and the language-specific `libs/*` workspaces. Cross-language and template artifacts must stay isolated.
- **Build inside the relevant sub-workspace** (`HexaKit/`, `libs/rust/`, etc.), not at the repo root.
- **Edits to `governance/`, `policies/`, `schemas/`, `secrets/`, `credentials/`, `security/`** must follow the mutability rules in the README's category table. When in doubt, treat as locked and propose a change in `governance/` first.
- **Sibling repos (Civis, AgilePlus, heliosApp, etc.)** are separate clones at the umbrella level. Do not vendor or copy code from them into PhenoKits; reference them via the `libs/` and `governance/` patterns instead.

## Reference

See [`README.md`](README.md) for the full category table, agent interaction matrix, and quick-start commands.

For Codex model and subagent selection, follow
[`docs/governance/codex-model-routing-policy-2026-04-26.md`](docs/governance/codex-model-routing-policy-2026-04-26.md):
default to the cheapest reliable model/effort, prefer Spark-style bounded
sidecars for routine fanout, and escalate to frontier/high-reasoning models
only with evidence.
