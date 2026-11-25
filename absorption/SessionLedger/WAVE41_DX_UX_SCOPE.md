# Wave-41 scope — AX/DX/UX polish (SessionLedger)

**Base:** `origin/main` @ `6283ce5` (Wave-39 closure #316–#320, 394/402 A)  
**Method:** Deep audit across CLI ergonomics, docs discoverability, viewer UX (ADR 0001 boundary), a11y workflow gaps, and developer onboarding — then parallel polish lanes with conservative score expectations (DX/UX does not move audit pillars unless evidence scripts land).

**Worktree:** `C:\workspace\SessionLedger-wtrees\w41-dx-ux-audit`  
**Branch:** `feat/sl-w41-dx-ux-scope`

---

## Executive summary — top gaps

| #   | Gap                                                                                                                                                                          | Severity   | Area              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------- |
| 1   | **Live Feed hardcodes `localhost:9001`** while daemon, Search, Replay, `.env.example`, and runbook use `:8080` — tab fails on default `make dev`                             | **P0 bug** | Viewer UX         |
| 2   | **No unified runtime daemon URL** in viewer (`search_view` const, `replay_view` compile-time `SL_DAEMON_URL`, `live_feed` wrong port)                                        | **P0**     | Viewer DX         |
| 3   | **First-run “Open corpus…” CTA is inert** — button renders with no handler (`async_states.rs`)                                                                               | **P1**     | Viewer UX         |
| 4   | **`llms.txt` / README onboarding index thin** — QUICKSTART, HELP, a11y, ADR 0001, `.env.example`, CONTRIBUTING not linked from README                                        | **P1**     | Docs              |
| 5   | **`sl-daemon search` empty results** lacked actionable hint (fixed in scope PR: widen filters + `list`)                                                                      | **P1**     | CLI               |
| 6   | **`sl-viewer --help` minimal** — no env vars, no doc cross-links, no daemon URL guidance                                                                                     | **P1**     | CLI               |
| 7   | **Native WebView a11y parity remains soft** (C09) — manual NVDA/VO checklists exist; automation is fixture-only                                                              | **P2**     | A11y              |
| 8   | **Fluent i18n migration incomplete** (C01 L16) — viewer/CLI production strings not in `.ftl` catalogs                                                                        | **P2**     | i18n              |
| 9   | **ADR 0001-aligned gaps:** no sidebar daemon health chip, no About/Releases link for manual update path                                                                      | **P2**     | Viewer (in-scope) |
| 10  | **Onboarding doc drift:** CONTRIBUTING says “Rust stable”; AGENTS/runbook pin `rust-toolchain.toml`; worktree paths differ (`.claude/worktrees/` vs `SessionLedger-wtrees/`) | **P2**     | Onboarding        |

**Explicitly out of scope (ADR 0001):** system tray, menubar companion, login items, silent/background auto-update.

---

## Audit findings (by research area)

### CLI ergonomics (`sl-daemon`, viewer entry)

**Strengths**

- `clap` subcommands with rich `after_help` examples (`serve`, `search`, `export`, `completions`).
- Documented exit codes in crate docs and `cli.rs` (`0` / `1` / `2`).
- `status` prints `daemon_down_message` with start hint; global `--url` for client commands.
- Shell completions committed under `crates/sl-daemon/completions/` + install scripts.
- Non-loopback bind + `SL_API_KEY` errors are explicit and tested.

**Gaps**

| Gap                                                                 | Evidence                       | Polish action                                              |
| ------------------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------- |
| Search empty set message terse                                      | `main.rs` `run_search`         | **Done (scope):** hint to widen filters + `sl-daemon list` |
| Export/search skip bad files silently                               | `load_metas` warnings only     | Lane: stderr summary `N skipped, M exported`               |
| Replay rustdoc mentions `--bundle`; CLI uses positional `bundle_id` | `main.rs` Replay doc comment   | Lane: align help text                                      |
| `session-ledger` is library-only — newcomers expect a binary        | root `Cargo.toml`              | Lane: README callout “CLI = `sl-daemon`”                   |
| `sl-viewer -h` one-liner only                                       | `crates/sl-viewer/src/main.rs` | Lane: env table + doc URLs                                 |
| No `--url` hint when `list`/`export` fail mid-request               | `exit_on_reqwest`              | Lane: append `hint:` for non-connect errors                |

### Docs discoverability

**Strengths**

- `llms.txt` agent entry with build/test/API block.
- `docs/HELP.md`, `viewer-hotkeys.md`, `docs/a11y/*`, ADR series, ops runbook, TRACEABILITY.json.
- `scripts/mcp-scope-check.ps1` validates llms + ADR 0006 anchors.

**Gaps**

| Gap                                                   | Evidence                | Polish action                            |
| ----------------------------------------------------- | ----------------------- | ---------------------------------------- |
| llms missing a11y, ADR 0001, QUICKSTART, CONTRIBUTING | `llms.txt`              | **Done (scope):** table rows added       |
| README has no developer doc hub                       | `README.md`             | Lane: “Developers” section w/ links      |
| No ops doc index                                      | `docs/ops/` (121 files) | Lane: `docs/ops/README.md` curated index |
| ADR 0001 not in agent entry                           | `AGENTS.md`             | Lane: one-line + link (tray scope)       |

### Viewer / desktop companion UX (ADR 0001 boundary)

**In-scope polish (no tray/updater)**

| Gap                                    | Evidence                                           | Lane                                                    |
| -------------------------------------- | -------------------------------------------------- | ------------------------------------------------------- |
| Live Feed wrong port                   | `live_feed.rs:12` `9001` vs `8080`                 | **w41-daemon-url-unify** (P0)                           |
| Split daemon URL sources               | `search_view.rs`, `replay_view.rs`, `live_feed.rs` | **w41-daemon-url-unify**                                |
| Dead first-run CTA                     | `async_states.rs` `FirstRunEmpty` button           | **w41-first-run-cta**                                   |
| No connection status in chrome         | viewer sidebar                                     | **w41-daemon-status-chip**                              |
| Manual update path invisible in UI     | ADR 0001 §Consequences                             | **w41-about-releases** (version + GitHub Releases link) |
| Help overlay cites paths as plain text | `help_overlay.rs`                                  | Optional: `file://` or copy-to-clipboard                |

**Out of scope (document, don’t build)**

- Tray/menubar, login startup, silent updater — ADR 0001 Accepted.

### Accessibility (WCAG workflow)

**Strengths**

- Blocking `a11y.yml` + Playwright `a11y.spec.js` (axe, tablist, overlays, progressive disclosure).
- Status/alert regions, overlay escape precedence, reduced-motion guard documented + tested.
- Manual NVDA/VoiceOver checklists + `record-native-webview-smoke.ps1`.

**Gaps (from SCORECARD / GAP_QA_MATRIX)**

| Gap                                        | Pillar             | Lane                                             |
| ------------------------------------------ | ------------------ | ------------------------------------------------ |
| Native WebView parity not machine-blocking | C09                | **w41-native-a11y-evidence**                     |
| Real screen reader not in CI               | L81.4              | Keep manual cadence; add release checklist gate  |
| Fluent migration stub only                 | C01 L16            | **w41-fluent-strings** (viewer error/copy first) |
| Vale warning-only                          | CONTRIBUTING       | Promote to CI warning → blocking later           |
| Live Feed error copy cites wrong host:port | `live_feed.rs:149` | Fixed by daemon-url-unify                        |

### Developer onboarding

**Strengths**

- `QUICKSTART.md` five-step path; `runbook.md`; comprehensive `.env.example` + CI hygiene job.
- `AGENTS.md`, TRACEABILITY lint, pre-commit, property-test guidance in CONTRIBUTING.

**Gaps**

| Gap                                                 | Evidence                                   | Lane                                   |
| --------------------------------------------------- | ------------------------------------------ | -------------------------------------- |
| README → QUICKSTART / `.env.example` / CONTRIBUTING | README                                     | **w41-onboarding-hub**                 |
| Toolchain wording mismatch                          | CONTRIBUTING vs `rust-toolchain.toml`      | Align CONTRIBUTING to pinned toolchain |
| Worktree location inconsistency                     | AGENTS vs operator `SessionLedger-wtrees/` | Document both or standardize in AGENTS |
| `traceability_lint.ps1` not in README quick path    | ops scripts                                | Add to QUICKSTART verify step          |
| No `mise.toml` / `.tool-versions`                   | C03 residual                               | Optional P3                            |

---

## Prioritized polish lanes

| Priority | Lane ID                  | Branch suffix                 | Target                                                                                                                    | Effort | Score note                 |
| :------: | ------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------- | :----: | -------------------------- |
|  **P0**  | w41-daemon-url-unify     | `feat/sl-w41-daemon-url`      | Single runtime daemon base URL module; fix Live Feed `:9001` → configurable default `:8080`; align Search/Replay/LiveFeed |   M    | UX bugfix; no pillar delta |
|  **P1**  | w41-cli-hints            | `feat/sl-w41-cli-hints`       | Search hint (landed), export skip summary, replay help text, richer reqwest hints                                         |   S    | DX                         |
|  **P1**  | w41-sl-viewer-help       | `feat/sl-w41-viewer-help`     | Expand `--help` / `--version`; document `SL_DAEMON_URL`, `FORGE_DB`                                                       |   S    | DX                         |
|  **P1**  | w41-llms-onboarding      | `feat/sl-w41-llms-onboarding` | llms rows (landed), README developer hub, `docs/ops/README.md` index                                                      |   S    | Docs                       |
|  **P2**  | w41-first-run-cta        | `feat/sl-w41-first-run-cta`   | Wire corpus picker or hide CTA until implemented                                                                          |   S    | UX                         |
|  **P2**  | w41-daemon-status-chip   | `feat/sl-w41-daemon-status`   | Sidebar `/healthz` badge (connected / degraded / offline)                                                                 |   M    | ADR 0001-safe              |
|  **P2**  | w41-about-releases       | `feat/sl-w41-about-releases`  | About dialog: version, link to Releases (manual update)                                                                   |   S    | ADR 0001-aligned           |
|  **P2**  | w41-native-a11y-evidence | `feat/sl-w41-native-a11y`     | Expand native smoke recorder + optional CI artifact                                                                       |   M    | C09 evidence               |
|  **P2**  | w41-fluent-strings       | `feat/sl-w41-fluent`          | Migrate top viewer error/empty strings to `locales/en.ftl`                                                                |   L    | C01 L16                    |
|  **P3**  | w41-vale-blocking        | `feat/sl-w41-vale`            | CI warning → blocking for docs style                                                                                      |   S    | C01                        |
|  **P3**  | w41-onboarding-tooling   | `feat/sl-w41-mise`            | `mise.toml` pins mirroring rust-toolchain                                                                                 |   S    | C03                        |

**Suggested merge order (conflict risk):** daemon-url-unify → cli-hints → sl-viewer-help → llms-onboarding → parallel P2 lanes → fluent/vale.

---

## Scope PR contents (this branch)

1. **`WAVE41_DX_UX_SCOPE.md`** (this file) — audit + lane plan.
2. **Tiny DX wins (already applied on branch):**
   - `sl-daemon search`: actionable empty-filter message.
   - `llms.txt`: QUICKSTART, HELP, hotkeys, USER_JOURNEYS, a11y smoke, ADR 0001, `.env.example`, CONTRIBUTING.

**Do not edit** in feature lanes: `audit/SCORECARD.md`, `GAP_QA_MATRIX.md`, `TRACEABILITY.json`, `WBS.md` status — reaudit only.

---

## Verify (post-lane)

```powershell
pwsh ./docs/ops/traceability_lint.ps1
cargo test -p sl-daemon --locked
cargo test -p sl-viewer --locked
cd tests/visual/harness; npx playwright test a11y.spec.js
```

---

## Git bootstrap (operator)

```powershell
cd C:\workspace\SessionLedger
git fetch origin
git worktree add -b feat/sl-w41-dx-ux-scope `
  C:\workspace\SessionLedger-wtrees\w41-dx-ux-audit origin/main
# Copy or cherry-pick scope commit; then:
git push -u origin feat/sl-w41-dx-ux-scope
gh pr create --title "Wave-41: DX/UX polish scope" --body "Adds WAVE41_DX_UX_SCOPE.md + search hint + llms.txt discoverability."
```

---

## AgilePlus mapping (stub)

| WBS stub | Epic                   | Story                                  |
| -------- | ---------------------- | -------------------------------------- |
| WBS-8.60 | Lifecycle / NFR        | W41 DX/UX scope — audit + lane DAG     |
| WBS-8.61 | Viewer UX (C09)        | Daemon URL unification + first-run CTA |
| WBS-8.62 | Agent experience (C01) | llms onboarding index + CLI hints      |

Run `.\scripts\agileplus-sync.ps1` after scope merge.
