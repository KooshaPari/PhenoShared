# Fork: Portage

- **Upstream:** `evalplus/Portage` (CLI 0.1.42) — https://github.com/evalplus/Portage
- **<REDACTED> fork:** `<REDACTED>/portage-fork` (planned, N18)
- **Upstream SHA pinned:** `63f6e67cbb7a0a883452a67323016ac8ccb3911e` (last-known-good, worktree `portage-clean-harbor`)
- **License:** Apache-2.0 (verify `LICENSE` on fork)
- **Divergence rationale (≤5 lines):** Local-Qwen adapter + TB2 native harness; harbor worktree fallback; no merge into main until `validate_harbor_primary.ps1` passes.
- **Rebase cadence:** monthly (track upstream `main`)

## Evidence

- `plans/2026-07-24-forward-dag-v2/INDEX.md` §5, `RUN_REGISTRY.md` §8 (worktree @63f6e67c), `pheno-harness` `config/evidence_registry.yaml`.
