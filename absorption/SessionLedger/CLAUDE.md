# CLAUDE.md — SessionLedger

Claude Code agent entrypoint. Read before editing.

## Working directory

Cargo workspace. Feature work in a git worktree, never on `main`:

```
git worktree add -b <type>/<topic> .claude/worktrees/<topic> origin/main
```

`<type>` ∈ `feat|fix|chore|ci|docs`. Worktrees under `.claude/worktrees/` only.

## Build / test / lint

```bash
cargo build --all-targets --locked        # build
cargo test  --all-features --locked       # run the suite (86+ tests)
cargo clippy --all-targets --all-features # lint
cargo fmt --all --check                   # format check
```

sl-viewer (Dioxus 0.6 desktop) needs the Dioxus CLI: `cargo install dioxus-cli`, then `dx serve` / `dx bundle` from `crates/sl-viewer`.

Fast inner loop: `cargo test --manifest-path crates/sl-daemon/Cargo.toml` /
`cargo check -p sl-viewer`. Measured budgets: [`docs/ops/feedback-budgets.md`](docs/ops/feedback-budgets.md).

## Key files

| Path                              | What                                                            |
| --------------------------------- | --------------------------------------------------------------- |
| `crates/sl-daemon`                | watch → compile session bundles (the compiler daemon)           |
| `crates/sl-viewer`                | Dioxus 0.6 desktop viewer (bundle/history/memory tabs)          |
| `docs/functional_requirements.md` | FR-NNN catalog + acceptance refs                                |
| `docs/USER_JOURNEYS.md`           | Named user journeys mapped to FRs and existing tests            |
| `PLAN.md` / `WORK_DAG.md`         | claimable tasks + dependency graph                              |
| `llms.txt`                        | LLM-friendly repo map + build/test commands                     |
| `docs/ops/runbook.md`             | `make dev`, healthz :8080, common failures                      |
| `docs/ops/feedback-budgets.md`    | measured check/test/`make lint` loop budgets + nextest          |
| `README.md`                       | overview + Releases link                                        | `.github/workflows/release.yml` | per-OS viewer build |
| `docs/adr/0006-no-mcp-server.md`  | Explicit N/A: not an MCP host/server; no MCP pin list (C06 L57) |

## Forbidden

- No direct commits to `main` (protected — PR only).
- No `git reset --hard`, `git stash`, `git clean` in worktrees.
- No `--no-verify` / hook bypass without operator approval.
- No AI attribution in commit/PR metadata.
- Do not work a branch/worktree another actor is on.

## Gotchas

- Exact rustc is pinned in `rust-toolchain.toml` (see `docs/ops/rustc-toolchain-pin.md`); workspace MSRV is `rust-version = "1.85"`.
- clippy warnings — fix, don't `#[allow]` without a tracking-issue comment.
- sl-viewer is Dioxus 0.6 — `dx` toolchain required for desktop bundling (see electrobun/dioxus codesign notes when packaging macOS).
- CI uses `--locked` — keep `Cargo.lock` committed and current.
