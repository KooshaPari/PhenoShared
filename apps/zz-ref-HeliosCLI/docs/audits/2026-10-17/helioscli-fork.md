# HeliosCLI — Generic Fork Audit (2026-10-17)

## UPSTREAM
`openai/codex` — Rust-based coding-agent CLI with multi-crate workspace, release-please driven, currently ~10k+ commits ahead.

## FORK IDENTITY
`KooshaPari/helios-cli` (atlas-product record `HeliosCLI`, repo ID `1165315873`) — renamed/rebranded fork marketing itself as "heliosCLI" with claimed performance optimizations, a multi-crate harness envelope, and Phenotype-org governance overlays. Default branch `main` pinned at release tag `v0.11.10` (HEAD `5093c0b7bb`, 2026-10-08).

## FORK INTENT
Condensed from `README.md` + atlas prompt: take upstream Codex and produce a Phenotype-governed, signed+notarized macOS distributable, with a sandbox/harness envelope, "AP-itemized" CI fix loop, and slodge-tier AI-slop disclosures. No published design-novelty thesis; positioning is "community fork + Phenotype plumbing".

## FORK CURRENT STATE
- HEAD: `5093c0b7bb chore(deps-dev): bump @modelcontextprotocol/sdk from 1.26.0 to 1.31.0 (#700)`. Tracking tag `v0.11.10` (`87f5beb7cb`).
- Working tree: only `demos/` is untracked; tracked source is unmodified. No active development on `main`.
- Divergence vs `upstream/main`: **260 fork-unique commits** vs **10,242 upstream-unique commits** — i.e., the fork is ~2.5% the size of upstream delta and has effectively stopped syncing. Fork-unique commits in the visible window are predominantly release-please chore bumps, CI race-condition fixes (paths-ignore, attestations pinning, Mergify condition syntax), Dependabot/security bumps for `aws-smithy-json` and `quinn-proto`/`rustls`, plus a code-license declaration.
- 8 stale local branches with date stamps mid-Aug → mid-Sep 2026: `feat/harness-envelope-stress-demo`, `feat/helios-cli-macos-signing-infisical-...v3`, `fix/perf-models-refresh-timeout-20260908`, `fix/perf-url-scheme-validation-20260909`, `fix/sandbox-dead_code-vitest-cve-20260903`, `fix/helios-checkpoint-store-rollback-integration-20260901`, `fix/trunk-jq-20260902`, `security/quinn-proto-0.11.19-rustls-0.23.45`. None merged to `main`. Upstream-shaped CI/Mergify chore-merge pattern only.
- No fork-authored-author commits visible in top-of-log; "KooshaPari" appears via release-please bot merges and PR authoring, not as the primary committer.
- Renamed-fork heuristics: `codex-rs/` keeps upstream crate naming (no crate-rename pass), `[tool.uv]` and bundling still say `codex`. Rebrand is at the README + GitHub-repo-name level only, not the source tree.
- `~/.helios/` does not exist on this host (per KCode-style multi-fork decollision note): the fork was never built/installed/run here. The "real installed binary" acceptance criterion in the atlas prompt is unmet.

## DIVERGENCE INVENTORY
| Category | What shipped | Gap to upstream | Stale branches |
|---|---|---|---|
| CI/Infra | release-please churn, Dependabot coverage expand, CI race fixes (paths-ignore release files, attest-build pin v2.1.0, Mergify condition syntax), least-privilege perms | Mostly mirror changes already in upstream's workflow-audit; net-new value vs upstream trunk ≈ minimal | `pr-665-fix`, `fix/harness-json-utf8-cap-ap-item-6-h05r4` supersede older AP-ITEM branches |
| Security bumps | `aws-smithy-json 0.62.7` (GHSA-8ffr-xgwf-xj56), `quinn-proto 0.11.19`, `rustls 0.23.45` | Strict subset of upstream's automated bump chain — useful as cherry-picks, never as a standalone track | `security/quinn-proto-0.11.19-rustls-0.23.45` (Oct 13 — most recent, candidate to merge) |
| Sandbox/Harness | `fix(helios-sandbox): remove dead LandlockRulesetAttrVersions struct`, `fix/sandbox-dead_code-vitest-cve-20260903` | Upstream sandbox moves faster; these are localized cleanup, not an envelope feature | `feat/harness-envelope-stress-demo`, `fix/sandbox-dead_code-vitest-cve-20260903`, `fix/helios-checkpoint-store-rollback-integration-20260901` |
| Perf patches | `perf(model-provider): raise models refresh HTTP timeout from 5s to 30s`, `fix(model-provider-info): reject ws://http:// double-scheme base_url` | Provider-config defensive patches — possibly worth upstreaming, currently fork-local | `fix/perf-models-refresh-timeout-20260908`, `fix/perf-url-scheme-validation-20260909` |
| Release channel | `feat(helios-cli-macos-signing-infisical-...)` v3 with Infisical secrets for macOS notarization | Distinct distribution track not present upstream; sign+notarize is real owned value | `feat/helios-cli-macos-signing-infisical-20260902T0556Z-v3` |
| Licensing | License declaration PR merged (Aug 31) | Resolves a fork pre-existing defect (per atlas) | `fix/current-main-pr647-pr648-closure-20260901` |
| Brand rename | Repository-level rename to `helios-cli`; markdown rebrand | Source tree not renamed (still `codex-rs/`); no crate-rename pass — rebrand is cosmetic | n/a |

## FWD PATH
1. **Pick a stance** — fork exists for Phenotype governance + notarized macOS release; everything else is CI noise. Decide whether to own the release channel (KEEP) or retire to a release-only mirror (SUNSET).
2. **Land the security branch** (10m) — merge `security/quinn-proto-0.11.19-rustls-0.23.45` to `main`; it's a real dependency bump currently stuck on a side branch.
3. **Decide on the macOS signing feature branch** (10m) — diff `feat/helios-cli-macos-signing-infisical-...v3` against `main`; either finish the v3 notarization (KEEP signal) or close it as deferred (SUNSET signal).
4. **Re-establish upstream sync cadence** (10m) — `git fetch upstream && git rebase upstream/main` on a fresh branch; record how many of the 10,242 upstream-only commits apply cleanly. Calibrates how "alive" the fork is.
5. **Branch cleanup** (10m) — close the 7 stale `fix/*` and `feat/*` branches older than mid-Sep 2026 that have nothing to land on `main`, with one `git branch -d` round (NOT `-D`).

## TIME-TO-FINISH
~30 minutes wallclock (5 × 10m focused steps above) to either a clean KEEP state with security landed + macOS channel active, or a SUNSET state with branches archived and a clear retirement note on `main`.

## SUNSET/KEEP CALL
**Tentative KEEP, conditional.** The fork carries a real owned asset (Infisical-driven macOS sign+notarize release channel) plus disciplined CI hardening. The 260-vs-10,242 divergence means it has effectively stopped tracking upstream — which is fine if the fork is treated as a *distribution fork* not an *engineering fork*. If the macOS signing branch can be merged in step 3 and the 10m rebase in step 4 confirms a viable upstream-sync path, KEEP. Otherwise SUNSET to a release-mirror README and close stale branches.
