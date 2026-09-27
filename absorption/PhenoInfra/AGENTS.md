---
governance_version: 1
---

# phenotype-infra — Forge Agents Instructions

This file is read automatically at the start of every Forge conversation
within this repository. It extends the global `~/forge/AGENTS.md`.

---

## <EXTREMELY-IMPORTANT>

If you think there is even a 1% chance a skill might apply to what you are
doing, you ABSOLUTELY MUST invoke the skill.

If a skill applies to your task, you do not have a choice. You must use it.

This is not negotiable. This is not optional. You cannot rationalize your
way out of this.

</EXTREMELY-IMPORTANT>

## Skill discovery

- Use the `:skill` command to list every skill Forge has loaded.
- The `skill` tool is available inside the conversation. Invoke it by name
  before responding to a user request.
- Skills live in three locations; precedence is
  **project `.forge/skills/` > `~/.agents/skills/` > `~/forge/skills/` >
  built-in**. The `superpowers` skills are installed under
  `~/forge/skills/superpowers/<name>/SKILL.md`.

## Instruction priority

1. User's explicit instructions (this file, `AGENTS.md`, direct requests) — highest priority
2. Superpowers skills — override default system behaviour where they conflict
3. Default system prompt — lowest priority

## Mandatory invocation rules

1. Before responding to ANY user message, invoke the
   `superpowers/using-superpowers` skill.
2. Before doing any work that could be characterised as "build X",
   "add a feature", or "let's make", invoke
   `superpowers/brainstorming` first.
3. Before debugging any non-trivial issue, invoke
   `superpowers/systematic-debugging`.
4. Before writing any new code, invoke
   `superpowers/test-driven-development` unless the user explicitly
   opts out.
5. Before claiming work is done, invoke
   `superpowers/verification-before-completion`.
6. Before opening or responding to a PR, invoke
   `superpowers/requesting-code-review` (sender) or
   `superpowers/receiving-code-review` (reviewer).
7. Before ending a feature branch, invoke
   `superpowers/finishing-a-development-branch`.
8. When writing or editing another skill, invoke
   `superpowers/writing-skills`.

## Project-specific conventions

- **Language stack**: Rust (edition 2021), Go 1.23+, TypeScript/Svelte
- All Rust crates MUST use `edition = "2021"` and inherit workspace package
  fields from `[workspace.package]`.
- Architecture decisions belong in `docs/adr/` as numbered ADR documents.
- Infrastructure configuration MUST be validated with `cargo check` and
  `cargo clippy` before commit.
- Pre-commit hooks are configured — run `pre-commit install` on first clone.
- Go code must pass `go vet ./crates/nanovms-core/...`.
- Secret scanning uses `.gitleaks.toml` (extending upstream defaults).

## Crate layout

```
crates/
├── nanovms-core/    # Go 3-tier isolation (WASM/gVisor/Firecracker)
├── nvms-ffi/        # Rust FFI bindings to NVMS Go Core
├── pheno-compose/   # High-level Rust driver
└── pheno-config/    # Shared configuration
```

## Quality checks

```bash
cargo check --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
go vet ./crates/nanovms-core/...
pre-commit run --all-files
```

## MCP tools available

- `github` — read/write issues, PRs, branches, file contents, run actions.
- `playwright` — headless browser automation for UI testing and verification.
- `chrome-devtools-mcp` — full DevTools protocol: traces, network, performance.
- `firecrawl` — web fetch + clean Markdown extraction.
- `context7` — resolve library docs from a crate ID.
