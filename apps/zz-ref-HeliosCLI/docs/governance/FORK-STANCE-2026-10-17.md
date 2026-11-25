# HeliosCLI Fork Stance — 2026-10-17

## Decision: KEEP

The fork `KooshaPari/helios-cli` exists for two reasons:

1. **Phenotype governance overlay** — release-please chore, Dependabot coverage,
   CI race-fix hardening, least-privilege workflow permissions.
2. **Signed + notarized macOS release channel** — Infisical-backed Apple
   notarization that upstream `openai/codex` does not ship.

Per the 2026-10-17 master audit (260 fork-vs-10,242 upstream-only commit gap),
this is treated as a **distribution fork**, not an engineering fork. KEEP is
viable because the owned asset (macOS notarization pipeline) is real and the
non-owned content is disciplined CI/Mergify churn rather than divergent logic.

## Security branch status

`security/quinn-proto-0.11.19-rustls-0.23.45` tip commit `ebddf69943`
(`fix(deps): bump quinn-proto 0.11.17→0.11.19, rustls 0.23.43→0.23.45`)
is **already an ancestor of `main`** (visible as commit 2 from HEAD in
`git log main`). Branch is stale and was removed in step 5 cleanup
with `git branch -d` (NOT `-D`).

## Re-evaluation triggers (SUNSET)

Sunset to a release-only mirror if any of:

- The macOS signing branch cannot be merged cleanly to `main` (step 3 of the
  FWD path).
- The upstream rebase in step 4 produces >100 unresolved conflicts on the
  first 100 upstream-only commits.
- Three consecutive Dependabot bumps on `openai/codex` cannot be cherry-picked
  because the underlying code has diverged beyond cherry-pick reach.

Otherwise the KEEP stance holds and the next FWD step is the 2026-11 cycle.
