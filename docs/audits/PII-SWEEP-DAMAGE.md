# PII sweep damage audit

**Scope:** collateral damage from the 2026-09-16 repo-wide PII redaction sweep
and from the commit that silenced compiler warnings instead of fixing them.
**Snapshot:** `da51939f` (2026-09-19). **Nothing was modified to produce this
report** — every count is read-only (`git grep`, `git show`, `cargo metadata`,
`cargo check` with `--force-warn`, `plutil -lint`, `node`).

## Headline

The sweep replaced exactly **one token family** — the owner's username in six
case variants — **44,496 times** across 4,214 files. Of the **41,291** residue
sites still present at HEAD:

| # | What the site actually is | Sites | Share |
|---|---|---|---|
| A | Genuine PII removal (an email local-part) | 277 | **0.7%** |
| B | Destroyed non-PII information (paths, repo names, provenance, links) | 38,878 | 94.2% |
| C | Broken syntax / a reference that cannot resolve | 2,124 | 5.1% |
| D | Degenerate form (already-broken stacked pattern) | 12 | 0.0% |

**≈41,014 genuinely-damaged (non-PII) sites, vs 277 that redacted real PII.**
The sweep was over-broad by roughly two orders of magnitude, and it also failed
at its own goal: **2,182 files still contain the literal name it was meant to
remove.**

---

## 0. Method and reproducibility

| Question | Command used |
|---|---|
| Per-commit volume | `git show <hash> --shortstat` |
| What was replaced, exactly | `git show <hash> --format="" -U0`, then a greedy reconstruction: split the added line on `<REDACTED>`, walk the removed line, and whatever sits between two matched fragments **is** the replaced token. No fuzzy diffing, so no alignment artefacts. |
| Residue today | `git grep -I -o -F '<REDACTED>'` (text) and a direct file scan (adds 18 binary artefacts) |
| Warning suppression | `RUSTFLAGS="--force-warn dead_code --force-warn missing_docs" cargo check -p <crate> --all-targets`. `--force-warn` overrides in-source `#[allow]` attributes, so the repo is untouched and the hidden diagnostics become visible. |
| Plist validity | `plutil -lint <file>` |
| npm name validity | `node -e '<npm package-name regex>'` |
| mailmap resolution | `git check-mailmap '<email>'`, A/B against a known-good entry |

The parser was validated against git's own numbers: for `3b6d8798` it recovers
**35,813** modified-line pairs, exactly matching `--shortstat`. The working tree
is live — other agents landed two commits during this audit — so all totals are
pinned to `da51939f` and will drift upward.

---

## 1. Quantifying the sweep

### 1.1 Per-commit volume

| Commit | Files | +/- lines | What it actually did |
|---|---|---|---|
| `3b6d8798` chore: PII sweep | 4,214 | 35,813 / 35,813 | **100% of added lines contain `<REDACTED>`** — 35,813 modified lines, **44,496 token replacements**. Zero restoration. |
| `eb6fd899` chore: PII deep-clean pass 2 | 1,691 | 7,643 / 7,643 | Mixed: 658 lines redacted, **6,985 lines restored** (URL repair). |
| `5b903999` fix: restore GitHub URLs in Cargo.toml | 3 | 4 / 4 | Pure restoration. |
| `ed4c0642` fix: "unstack nested REDACTED" | 54 | 113 / 113 | **Not a repair — see §1.4. It added 113 tokens from a baseline of zero.** |
| `cc6b8e39` fix(npm): scopes/github refs | 10 | 259 / 302 | Pure restoration. Net −43 lines. |
| `d0fe3aa3` fix: suppress all warnings | 8 | 19 / 9 | Suppressions, not repairs — see §4. |

### 1.2 The complete inventory of what was replaced

Across all 44,496 replacements in pass 1, the distinct replaced tokens were
**exactly six** — six case-variants of one string:

| Token | Replacements |
|---|---|
| `kooshapari` | 24,462 |
| `KooshaPari` | 19,904 |
| `KOOSHAPARI` | 111 |
| `Kooshapari` | 16 |
| `koosha` | 2 |
| `kooshaPari` | 1 |

No other string was redacted anywhere in 4,214 files. This is the single most
important fact in the audit: the sweep was not a PII policy, it was a
**one-pattern `sed`** applied to a token that is simultaneously the owner's
account name and **the public GitHub org that hosts every repository here**.

### 1.3 Categories the sweep rewrote (with before/after)

Context breakdown of the 44,496 replacements:

| Category | Replacements | Share | Before → After |
|---|---|---|---|
| Absolute home paths | 18,594 | 41.8% | `- **Repo**: /Users/kooshapari/CodeProjects/Phenotype/repos/heliosApp`<br>`+ - **Repo**: /Users/<REDACTED>/CodeProjects/Phenotype/repos/heliosApp` |
| GitHub owner namespace / URLs | 9,233 | 20.8% | ``- Go 1.23+, use `go mod init github.com/KooshaPari/pheno-cli` ``<br>``+ Go 1.23+, use `go mod init github.com/<REDACTED>/pheno-cli` `` |
| Repo references in prose / commands | 8,474 | 19.0% | ``- Generated CI workflows reference `KooshaPari/phenotypeActions/...` ``<br>``+ Generated CI workflows reference `<REDACTED>/phenotypeActions/...` `` |
| Bare identifiers / prose | 7,124 | 16.0% | `- #     set_by: kooshapari` → `+ #     set_by: <REDACTED>` |
| npm scopes | 473 | 1.1% | `- name: "@kooshapari/phenotype-ui"` → `+ name: "@<REDACTED>/phenotype-ui"` |
| Domains | 426 | 1.0% | `- url: "https://dashboard.kooshapari.com/testing"` → `+ url: "https://dashboard.<REDACTED>.com/testing"` |
| **Emails (the only real PII)** | **172** | **0.4%** | `- ...at [kooshapari@gmail.com](mailto:kooshapari@gmail.com)` → `+ ...at [<REDACTED>@gmail.com](mailto:<REDACTED>@gmail.com)` |

Two specific information-destroying rewrites worth naming:

- **Case distinction collapsed.** An audit table that deliberately distinguished
  `KooshaPari/Configra` from `kooshapari/Configra` (the whole point of the row was
  that both 404) now reads `<REDACTED>/Configra` twice, destroying the evidence.
- **`.github/workflows` `uses:` refs** — 158 `uses: <REDACTED>/…` sites at HEAD,
  3 of them live and unresolvable (see §3).

### 1.4 `ed4c0642` made the damage worse, not better

Its message claims it *unstacked nested `REDACTED` patterns*. Measured, it did
the opposite: of its 113 changed lines, **92 went from zero tokens to one, 12
from 1 to 2, 7 from 0 to 2, and 2 from 2 to 4** — a net **+113 tokens added from
a baseline of 0**. It was a second, smaller sweep.

Its effect on `.mailmap` is the clearest example — clean, resolvable addresses
were turned into invalid ones:

```
- KooshaPari <kooshapari@phenotype.ai>
+ KooshaPari <kooshapari<REDACTED>@phenotype.ai>

- KooshaPari <claude@phenotype.ai>
+ KooshaPari <claude<REDACTED>@phenotype.ai>
```

---

## 2. Classifying the residue

**Note on the figure given in the brief.** The stated "2,541 files / 1,985 `.md`"
could not be reproduced. Verified at `da51939f`: **3,404** files contain the sweep
marker, **3,425** contain `REDACTED` in any form, **1,979** are `.md`. (The `.md`
figure is close; the total is not.) Hypotheses tested and rejected as the source
of 2,541: excluding `audits/` → 2,815; excluding `crates/` → 2,306; files with
≥2 occurrences → 1,680. No exclusion reproduces it. I report the verified
numbers and flag the discrepancy rather than restating an unverified count.

### 2.1 Class table (mutually exclusive; sums to 41,291)

| Class | Sites | Share | Meaning |
|---|---|---|---|
| **A — genuine PII** | | | |
| `a1` email local-part (`<REDACTED>@domain.tld`) | 277 | 0.7% | The only defensible redaction. |
| **B — destroyed non-PII information** | | | |
| `b1` account name inside `/Users/<REDACTED>/` | 21,770 | 52.7% | Destroys path reproducibility and breaks copy-paste; redaction *intent* is arguable, effect is not. |
| `b2` `<REDACTED>/<repo>` owner references | 8,172 | 19.8% | Public repo provenance, destroyed. |
| `b4` prose / identifiers | 5,599 | 13.6% | Repo names in narrative, audit trails, commit-message templates. |
| `b3` filesystem paths in commands/scripts | 3,337 | 8.1% | Non-runnable runbooks and scripts. |
| **C — broken syntax / unresolvable** | | | |
| `c1` URL or scheme authority (`://`, `github.com/`, `repos/`) | 1,924 | 4.7% | Link or API path cannot resolve. |
| `c2` GitHub Actions `uses: <REDACTED>/…` | 138 | 0.3% | Workflow cannot resolve the called workflow. |
| `c4` npm scope `@<REDACTED>/…` | 44 | 0.1% | **Invalid npm package name** (verified, §3.2). |
| `c3` Actions `repository: <REDACTED>/…` | 18 | 0.0% | `actions/checkout` targets a non-existent owner. |
| **D — degenerate** | | | |
| `c5` `X<REDACTED>@domain` (invalid email) | 12 | 0.0% | A word char glues to the marker inside an address. |

Total: **41,291**. Of these, `git grep -I` (text files only) sees **40,483**; the
remaining ~800 sit in 18 binary artefacts that a direct file scan reads and
`git grep` suppresses.

### 2.2 Residue cross-tabs

**By extension** (files containing the sweep marker): `.md` 1,979 · `.json` 322 ·
`.yml` 186 · `.py` 119 · `.rs` 114 · `.toml` 112 · `.sh` 69 · `.txt` 42 ·
`.astro` 40 · `.cs` 29 · `CODEOWNERS` 28 · `.yaml` 25 · `.mjs` 22 · `.plist` 21 ·
`.patch` 18. **390 of these are executable source files.**

**By directory cluster:**

| Cluster | Files |
|---|---|
| `crates/argis-extensions/findings` | 117 |
| `audits/absorption-justifications` | 85 |
| repo root | 50 |
| `docs/reference` | 45 |
| `docs/boundary` | 45 |
| `crates/hexa-kit/docs/reference` | 45 |
| `absorption/resume-all` | 64 |
| `audits/org-audits` | 373 |
| `crates/hexa-kit` | 400 |

**Provenance destroyed:** 1,719 distinct `<REDACTED>/<name>` tokens, and 526
distinct repo names inside `.md` links alone. Frequent casualties:
`phenotypeActions` (262), `pheno-mcp-router` (285), `AgilePlus` (390),
`phenotype-registry` (177), `Configra` (138), `phenotype-tooling` (136).

### 2.3 Worst 50 files

| Sites | File |
|---|---|
| 3,600 | `audits/org-audit-snapshots/curation/forge/candidates.tsv` |
| 3,599 | `audits/org-audits/2026-07/zz-archive-archive2/modified-files/curation/forge/candidates.tsv.pre-2026-07-14` |
| 3,599 | `audits/org-audits/curation/forge/candidates.tsv` |
| 3,553 | `crates/hexa-kit/docs/worklogs/data/phenotype_session_extract_2026-03-26_2026-03-29.json` |
| 3,552 | `docs/worklogs/data/phenotype_session_extract_2026-03-26_2026-03-29.json` |
| 1,034 | `registry/disposition-index.json` |
| 1,017 | `archives/zz-archive-phenotype-registry/docs/absorption/DevHex-PlatformKit/patches/PlatformKit/local-ahead.patch` |
| 444 | `pheno-cli/pheno-test` |
| 408 | `repos/home-recovery-2026-07/manifests/home_entries.tsv` |
| 335 | `.broken_md_refs.txt` |
| 311 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/forge-runner-scripts/bin/subagents-orchestration/dag_launch_2026_06_13.sh` |
| 311 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/forge-runner-scripts/bin/subagents-orchestration/dag_launch_2026_06_13.sh` |
| 309 | `audits/org-audit-snapshots/forge-runner-scripts/bin/subagents-orchestration/dag_launch_2026_06_13.sh` |
| 309 | `scripts/org-audits/scripts/org-audits/forge-runner/bin/subagents-orchestration/dag_launch_2026_06_13.sh` |
| 265 | `crates/argis-extensions/findings/2026-06-20-pr-triage.md` |
| 254 | `crates/argis-extensions/api/graphql/gen/generated.go` |
| 253 | `audits/org-audit-snapshots/forge-runner-scripts/bin/subagents-orchestration/launch_all_subagents.sh` |
| 253 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/forge-runner-scripts/bin/subagents-orchestration/launch_all_subagents.sh` |
| 253 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/forge-runner-scripts/bin/subagents-orchestration/launch_all_subagents.sh` |
| 253 | `scripts/org-audits/scripts/org-audits/forge-runner/bin/subagents-orchestration/launch_all_subagents.sh` |
| 248 | `audits/org-audit-snapshots/curation/forge/curated-top.md` |
| 248 | `audits/org-audits/curation/forge/curated-top.md` |
| 237 | `audits/org-audit-snapshots/forge-runner-scripts/bin/subagents-orchestration/resume_all_subagents.sh` |
| 237 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/forge-runner-scripts/bin/subagents-orchestration/resume_all_subagents.sh` |
| 237 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/forge-runner-scripts/bin/subagents-orchestration/resume_all_subagents.sh` |
| 237 | `scripts/org-audits/scripts/org-audits/forge-runner/bin/subagents-orchestration/resume_all_subagents.sh` |
| 198 | `_archived/byteport/backend/nvms/log.txt` |
| 185 | `.work-audit/repo-manifest.json` |
| 185 | `crates/hexa-kit/.work-audit/repo-manifest.json` |
| 156 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816/beads.jsonl` |
| 154 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/inventory/AUTHORITATIVE_REPO_INVENTORY.md` |
| 154 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/inventory/AUTHORITATIVE_REPO_INVENTORY.md` |
| 154 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816T0137Z/beads.jsonl` |
| 154 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816T0238Z/beads.jsonl` |
| 154 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816T0305Z/beads.jsonl` |
| 154 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816T0314Z/beads.jsonl` |
| 154 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260816T0336Z/beads.jsonl` |
| 153 | `docs/sessions/20260722-repository-preservation-wave/custody/cockpit/20260815/beads.jsonl` |
| 139 | `archives/zz-archive-phenotype-registry/docs/absorption/Conft-Settly/patches/Settly/local-ahead.patch` |
| 136 | `crates/argis-extensions/slm-server/slm-server` (binary) |
| 95 | `crates/argis-extensions/scripts/adr_backlink_baseline.txt` |
| 87 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/plans/2026-06-17-v7-dag-stable.md` |
| 87 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/plans/2026-06-17-v7-dag-stable.md` |
| 85 | `audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/inventory/github_remote_inventory.md` |
| 85 | `audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/inventory/github_remote_inventory.md` |
| 75 | `audits/org-audits/2026-07/_phenofleet-decisions/2026-07-06-reactivation-decision.md` |
| 75 | `docs/org-audits/reactivation-decision-2026-07-06.md` |
| 74 | `audits/org-audit-snapshots/plans/2026-06-17-v7-dag-stable.md` |
| 74 | `docs/monorepo-state/plans/2026-06-17-v7-dag-stable.md` |
| 74 | `docs/org-audits/plans/2026-06-17-v7-dag-stable.md` |

A structural finding hiding in this list: the same file exists **4–6 times** under
`audits/org-audits/…`, `audits/org-audit-snapshots/…`, `scripts/org-audits/…` and
`docs/…`. The sweep multiplied a pre-existing duplication problem, so each repair
must be applied N times.

### 2.4 A class that must NOT be counted as damage

21 files contain `REDACTED` but never the sweep marker. These are **pre-existing,
legitimate** uses and are excluded from every count above:

`crates/argis-extensions/pheno-config/src/secrets.rs` (`const REDACTED: &str =
"***REDACTED***"`), `crates/focus-telemetry/src/pii_scrubber.rs` and
`crates/focus-observability/src/privacy_filter.rs` (`[REDACTED_EMAIL]`,
`[REDACTED_PHONE]`, `[REDACTED_TOKEN]`), `pheno/evidence/redaction.py`,
`patterns/feature-flagging.md`, `tests/test_evidence_registry.py`.

### 2.5 One high-severity false positive, caught by inspection

`git grep 'REDACTED' -- '*.rs'` surfaces:

```
crates/argis-extensions/pheno-config/src/secrets.rs:70:  f.write_str(REDACTED)
```

This looks like a string literal turned into a bare identifier — a compile error.
It is not. `REDACTED` is a real pre-existing `const`, and `git show 3b6d8798 --
<file>` is **empty**: the sweep never touched this file. Recorded because
pattern-matching alone would report it as a break; it is not one.

---

## 3. What is still broken NOW

Verified by execution, not by pattern-matching.

### 3.1 launchd plists are malformed XML — 21 of 27 cannot be loaded

`<REDACTED>` is not valid XML text: the parser reads it as an element start tag.
`plutil -lint` fails on **21 of 27** tracked plists, e.g.

```
absorption/resume-all/launchd/com.REDACTED.resume-all-bridge-health.plist:
(Encountered unexpected character R on line 6 while looking for close tag)
```

Line 6 is `<string>com.<REDACTED>.resume-all-bridge-health</string>`. Two
independent defects stack at every one of these sites:

1. **Malformed XML** → `launchctl bootstrap` cannot read the file at all.
2. **Filename ≠ Label** → all 15 `absorption/resume-all/launchd/*.plist` files
   declare a `Label` that does not match their filename (`com.REDACTED.…plist`
   vs `com.<REDACTED>.…`), which launchd also rejects.

Consequently the repo's own health check can never pass:
`absorption/resume-all/bin/health-check.py` probes
`gui/<uid>/com.<REDACTED>.resume-all-{snapshot,ipc,watch,zmx}` against a live
system whose jobs are not named that. It is **guaranteed to report `DEGRADED`**.
15 distinct launchd labels are affected.

### 3.2 npm package names are invalid — publish would fail

`.github/workflows/release-landing-packages.yml:24,26`:

```yaml
            name: "@<REDACTED>/phenotype-ui"
            name: "@<REDACTED>/phenotype-design-tokens"
```

Validated against npm's own name grammar with `node`:

```
"@kooshapari/phenotype-ui"  valid: true
"@<REDACTED>/phenotype-ui"  valid: false
"<REDACTED>/phenotype-ui"   valid: false
```

`<` and `>` are not permitted in a scope, so this is an invalid manifest /
publish target. 9 distinct npm scopes are affected repo-wide (`@<REDACTED>/design`,
`/devops`, `/gateway`, `/omniroute`, `/phenotype-ui`, `/phenotype-design-tokens`,
`/quillts`, `/security`, `/pheno-tracing-maintainers`) across 44 sites.
`crates/phinbox/Cargo.toml:19` carries the same break in metadata:
`npm-scope = "@<REDACTED>"`.

### 3.3 Three GitHub Actions workflows call workflows that cannot resolve

```
.github/workflows/deploy.yml:14:            uses: <REDACTED>/phenoShared/.github/workflows/vitepress-pages.yml@d1f40cb9…
.github/workflows/release-macos.yml:23:     uses: <REDACTED>/phenotype-fleet-ops/.github/workflows/macos-release.yml@main
.github/workflows/a11y-phenodocs.yml:34:    uses: <REDACTED>/OmniRoute-3rd/.github/workflows/reusable-a11y.yml@main
```

A reusable-workflow `uses:` must name a real `owner/repo`; `<REDACTED>` is not a
GitHub owner, so these jobs fail at workflow-load time. 158 `uses: <REDACTED>/`
occurrences exist repo-wide (the rest are in docs/templates that instruct a human
to paste a now-broken snippet). The §2.1 class table counts 138 here because it
tallies only line-initial `uses:` forms in its mutually-exclusive scheme; 158 is
the raw occurrence count. `actions/checkout` is also broken by
`repository: <REDACTED>/…` at 18 sites (e.g. `ai-testing-orchestration.yml:35,59,82`
targeting `nanovms`, `AgilePlus`, `thegent`), and
`.github/workflows/naming-conventions.sh:15` defaults `ORG="${ORG:-<REDACTED>}"`.

### 3.4 `.mailmap` identity mappings are silently dead

Verified by A/B test — the good line maps, the corrupted lines do not:

```
git check-mailmap '<kooshapari@gmail.com>'   -> KooshaPari <kooshapari@gmail.com>   (applied)
git check-mailmap '<kooshapari@phenotype.ai>' -> <kooshapari@phenotype.ai>          (NOT applied)
git check-mailmap '<claude@phenotype.ai>'     -> <claude@phenotype.ai>              (NOT applied)
```

`ed4c0642` broke these two entries by gluing a marker into the address. Git
ignores the malformed lines, so two identities quietly stop canonicalising.

### 3.5 Runtime defaults point at directories that do not exist

Not documentation — live code paths:

| Site | Impact |
|---|---|
| `servers/forge3-bridge/bin/forge3-ctl-src/src/main.rs:44` | `#[arg(long, default_value = "/Users/<REDACTED>/.cargo/bin/forge3")]` — the CLI's default binary path does not exist, so the tool fails to find `forge3` unless `--bin` is passed. |
| `infrakit/crates/agileplus-dashboard-server/src/main.rs:18` | `unwrap_or_else(\|_\| "/Users/<REDACTED>/CodeProjects/Phenotype/repos".to_string())` — the fallback root is invalid. |
| `crates/audit-privacy/src/main.rs:9` | hard-coded target path, now non-existent. |
| `crates/teamcomm-daemon/tests/daemon_e2e.rs:243` | test fixture path invalid. |
| `absorption/resume-all/bin/{chat-fork-state-writer,fuzz-test}.py` | `RESUME_ALL_DIR` default and `DAEMON_BIN`/`MCP_BIN` are non-existent paths. |

### 3.6 Build manifests: verified NOT broken

`cargo metadata --no-deps --format-version 1` **exits 0**, so every workspace
manifest parses. No `Cargo.toml` has `REDACTED` in `name`, `version`, `path`,
`git`, `repository`, `homepage`, `keywords` or `categories`. The `Cargo.toml`
damage is confined to **64 `authors` fields and 5 `description` fields** —
cosmetic, plus one malformed author string
(`Cargo.toml:87 authors = ["<REDACTED> <<REDACTED>@phenotype.space>"]`).
This is the one surface where the earlier repair commits (`5b903999`,
`cc6b8e39`) did their job.

### 3.7 Links and references

- **221** markdown links whose target contains the marker:
  `](https://<REDACTED>.com/docs/getting-started)`, `](mailto:<REDACTED>@gmail.com)`.
- **669** `github.com/<REDACTED>/…` references (28 on `raw.githubusercontent.com`,
  which also breaks `curl`-based setup scripts such as `dedup-check.yml:16`).
- **526** distinct repo names lost from `.md` links; **1,719** distinct
  `<REDACTED>/<name>` tokens overall.
- `.broken_md_refs.txt` — a file whose purpose is tracking broken links — is
  itself saturated with 335 markers, i.e. the tracker of broken links was broken.

### 3.8 The sweep failed at its own objective

**2,182 files still contain `Koosha Pari`, `KooshaPari` or `kooshapari`.** The
pattern was applied to org names and paths but not consistently to the actual
personal name. Examples that survived:

```
crates/sidekick-observability/Cargo.toml:5:  authors = ["Koosha Pari <<REDACTED>@gmail.com>"]
crates/agile-plus/Cargo.toml:34:             authors = ["Koosha Pari <<REDACTED>@<REDACTED>.com>"]
.mailmap:5:                                   KooshaPari <kooshapari<REDACTED>@phenotype.ai>
```

So the same commit that destroyed the public namespace left the private name
readable, and also produced the half-redacted forms above. Any future redaction
pass must be idempotent and verified against the intended target, not a
substring.

---

## 4. Auditing the suppressions (`d0fe3aa3`)

All 8 files it touched, and what each change actually does. **Verified count: it
hides 152 diagnostics while fixing one file.**

| File | Change | Silences | Verdict |
|---|---|---|---|
| `crates/fabric-capture/src/main.rs:6` | `+ #![allow(dead_code)]` | 15 dead-code diagnostics | Binary crate: blanket allow hides all unreachable code program-wide. Real dead code present (whole unused capture functions). |
| `crates/fabric-daemon/src/main.rs:6` | `+ #![allow(dead_code)]` | 24 | Hides an entire unused auth stack — `auth/oauth.rs` alone has `generate_auth_url`, `generate_auth_url_with_scopes`, `exchange_code`, `refresh_access_token`, `get_user`, `scopes_string`, `with_client`, `clear_cache` all unused; likewise `auth/middleware/mod.rs` (`get_current_user`, `attach_auth`) and `fabric-graph/src/score.rs`. Oversized relative to the 1-line fix. |
| `crates/fabric-terminal/src/main.rs:7` | `+ #![allow(dead_code)]` | 18 | Hides unused `web_main.rs` items (`capture_pane`, `get_layout`, unused fields). Note: the *second* allow at `:92` (`SyncSnapshot`) came from `365a3572`, **not** this commit. |
| `crates/fabric-terminal/src/tmux_capture.rs:69` | `+ #[allow(dead_code)]` on `find_tf_mux_binary` | **0 — redundant** | `--force-warn` never flags it: the function has **3 call sites** (`tmux_capture.rs:120`, `web_main.rs:581`, plus a test at `:312`). The attribute silences nothing; it was added without checking whether the warning existed. |
| `crates/orchestrator/src/lib.rs:19` | `- #![warn(missing_docs)]` → `+ #![allow(missing_docs)]` | 45 | **A lint downgrade, strictly worse than doing nothing.** The file previously *chose* to warn; the commit converted intent-to-enforce into intent-to-ignore, making 45 doc gaps invisible in `dispatcher.rs` and friends. |
| `crates/orchestrator/src/watcher.rs` | Moved `NoopWaker` + `use std::sync::Arc` / `Wake` into `mod tests`; deleted 5 dead lines, 2 unused imports | — | **The only genuine fix in the commit.** Dead code was removed and correctly relocated to test scope instead of silenced. |
| `crates/substrate-tui/src/main.rs:3` | `+ #![allow(dead_code)]` | 50 | Largest single blanket. Hides `boot.rs` entirely (`SPINNER`, `enum BootPhase`, `label`/`progress`/`next`), plus unused `app.rs` fields and methods. |
| `crates/substrate-tui/src/sparkline.rs` | Added a blank line only | **0 — no lint effect** | Confirmed whitespace-only. A no-op edit inside a commit whose purpose was suppressing warnings. |

**Silenced vs fixed**

| | Count |
|---|---|
| Suppression directives added | 6 (5 × `dead_code`, 1 × `missing_docs` downgrade) |
| Files changed with zero lint effect | 2 (`find_tf_mux_binary` redundant, `sparkline.rs` whitespace) |
| Files with a real fix | 1 (`watcher.rs`) |
| Diagnostics hidden at HEAD (measured, repo-local) | **152** (107 `dead_code` + 45 `missing_docs`) |
| Commit message claim | "44 → 3 warnings" |

### 4.1 The aggravating context: the lint gate was dead at the time

Timeline, all verified from `git show -s --format=%ci`:

| Time | Event |
|---|---|
| 2026-09-16 02:51 | `7a8ef302` absorbs PhenoMLX, bringing a root `clippy.toml` containing only `warn = [...]` / `allow = [...]` — neither is a valid `clippy.toml` field. This is a **hard config error for every crate in the workspace**. |
| 2026-09-16 04:23 | `d0fe3aa3` suppresses warnings. |
| 2026-09-18 06:30 | `476ec57f` removes the invalid `clippy.toml`. |

`a0147e56` (2026-09-18) records the consequence in the repo's own words: with the
file gone, clippy immediately surfaced defects nobody could have seen — three
`[lints.clippy]` entries naming lints that **do not exist** (each silently inert,
so their `allow` never applied), a deprecated `rmcp::model::ServerInfo` used three
times, and pedantic lints in `platform/windows.rs`. `30bce5f7` later fixed the
last three properly rather than silencing them.

Precision matters here: `dead_code` and `missing_docs` are **rustc** lints, so the
"44 → 3" figure came from `cargo build`, which did run. The point is narrower but
damning — the deeper lints that would have caught the hidden dead code were
unavailable during the window in which 107 dead-code diagnostics were silenced.

---

## 5. Repair plan

### Tier 1 — mechanical and safe (do first, high confidence)

These have a single correct answer recoverable from git history, so they can be
reverted with `git show <pre-sweep>:<path>` rather than guessed.

1. **Revert the 5 runtime-path defaults** (§3.5). These are functionally broken
   and each has exactly one correct value. `git log -S '/Users/<REDACTED>/'` locates
   the pre-sweep text.
2. **Repair the 21 plists** (§3.1). Restore both the `Label` string and the
   filename so they match. Verifiable locally with `plutil -lint` and a
   filename/Label equality check — no system state needed.
3. **Fix the 2 `.mailmap` entries** (§3.4). Verifiable locally with
   `git check-mailmap`; the A/B test above is the acceptance criterion.
4. **Fix the 3 live workflow `uses:`/`repository:` refs** (§3.3) and
   `naming-conventions.sh:15`. Verifiable by workflow-load and by `actionlint`.
5. **Fix the 9 npm scopes** (§3.2). Verifiable with npm's name grammar (§3.2
   reproduces in one `node -e`).
6. **Rewrite `https://<REDACTED>.com` → the real domain** across the 221 broken
   links. The domain is recoverable per-file from `git show 3b6d8798^:<path>`.

### Tier 2 — mechanical but needs a policy decision

7. **Un-redact the public namespace globally.** The single decision that resolves
   ~39,000 of the 41,291 sites: is `KooshaPari` (the GitHub org, in URLs, owner
   refs and npm scopes) to be treated as public or redacted? The repositories are
   public on GitHub, so redaction buys no privacy and costs all provenance. A
   scripted `git show 3b6d8798^`-based revert of B-class sites is safe **once that
   decision is made** — but it must be a decision, not a heuristic, and the result
   must be diffed for the nested cases `ed4c0642` created.
8. **`/Users/<REDACTED>/` (21,770 sites).** Genuinely a judgement call: the token
   is the local account name. Recommended resolution: keep it redacted in
   *published prose*, restore it in *executable scripts, tests and doc runbooks*,
   where a placeholder makes the code wrong. That split is mechanical to apply.
9. **Strip the hidden dead code, then remove the allows.** 152 diagnostics are
   now visible via `--force-warn`. The `fabric-daemon` auth stack is the largest
   single question: delete it or wire it up? Do not simply delete the `allow`
   lines — that converts a silent state into 152 warnings and the gate stays red.
10. **`orchestrator/src/lib.rs`: restore `#![warn(missing_docs)]`** after
    documenting, or explicitly accept the debt in the code rather than silently
    flipping intent. The downgrade should not survive review.

### Tier 3 — needs human judgement / is unrecoverable

11. **Duplicate-file multiplication.** `audits/org-audits/…`,
    `audits/org-audit-snapshots/…`, `scripts/org-audits/…`, `docs/…` hold 4–6
    copies of the same damaged files. Decide which copy is canonical *before*
    repairing, or the repair must be applied N times and will drift.
12. **Semantic rewrites inside prose and audit records** (§1.3). Where the sweep
    collapsed a deliberate `KooshaPari`/`kooshapari` distinction or rewrote
    narrative, mechanical revert can restore the string but not always the
    sentence. Needs a reading pass.
13. **`.patch` files (18) and `*.pre-<date>` snapshots.** These are frozen
    evidence. Restoring them changes hashes that other documents cite, so repair
    and re-citation must move together.
14. **Genuinely lost:** the 12 degenerate sites (§2.1 D) where `ed4c0642` glued a
    marker into an address **and** the intervening commits rewrote the same line;
    `git log -S` cannot always recover the original. Verify per-site with
    `git log -S '<the specific string>'` before assuming recoverability — the
    audit found the pre-sweep text is retained for the `.mailmap` cases but that
    is not guaranteed everywhere.
15. **Cannot be repaired by any of the above:** the confidence loss. A repo that
    silently falsified 44,496 strings, and whose own broken-link tracker and
    lint gate were themselves broken, needs verification the *counts* in this
    audit remain reproducible after repair — i.e. re-run §0 and expect the
    marker count to reach 0 while 21 pre-existing legitimate uses (§2.4) survive.

### What must never be repeated

The sweep's failure mode was not over-redaction by itself; it was **redacting a
public identifier with a single non-idempotent substring pattern, without a
verification pass**. Two guardrails would have caught all of it: (a) require the
replacement to be idempotent and re-run it twice (this is exactly the class of
bug that created the `<REDACTED><REDACTED>` shapes `ed4c0642` claimed to fix),
and (b) assert that the sweep's own target is absent afterwards — 2,182 files
would have failed that assertion immediately (§3.8).

---

## Appendix — reproduction commands

```bash
# per-commit volume
for h in 3b6d8798 eb6fd899 5b903999 ed4c0642 cc6b8e39 d0fe3aa3; do
  git show --shortstat --format='%h %s' "$h"; done

# what was replaced, exactly (no fuzzy matching)
git show 3b6d8798 --format="" -U0 > sweep1.diff
# then: split the '+' line on <REDACTED>, walk the '-' line, capture the gaps

# residue at a pinned commit
H=da51939f
git grep -l  -F '<REDACTED>' $H | wc -l     # 3404
git grep -I -o -F '<REDACTED>' $H | wc -l   # 40483 (text)
git grep -l  -F 'REDACTED'    $H | wc -l    # 3425 (any form)

# suppressions: reveal what they hide, without editing the repo
RUSTFLAGS="--force-warn dead_code --force-warn missing_docs" \
  cargo check -p fabric-daemon --all-targets --message-format=short

# launchd plists
for f in $(git ls-files '*.plist'); do plutil -lint "$f"; done

# npm scope validity
node -e 'console.log(/^(?:@([a-z0-9-~][a-z0-9-._~]*)\/)?([a-z0-9-~][a-z0-9-._~]*)$/.test("@<REDACTED>/phenotype-ui"))'

# mailmap A/B
git check-mailmap '<kooshapari@gmail.com>'    # applied
git check-mailmap '<kooshapari@phenotype.ai>' # NOT applied

# manifests still parse
cargo metadata --no-deps --format-version 1 >/dev/null && echo OK
```

**Audit limitations, stated plainly:** (1) the working tree is live — two commits
landed mid-audit, so totals are a `da51939f` snapshot; (2) the 41,291-site class
table includes ~800 matches inside 18 binary artefacts that `git grep -I`
suppresses (text-only total 40,483); (3) C-and-D counts describe the **current**
residue, so sites subsequently repaired by `5b903999`/`eb6fd899`/`cc6b8e39` are
already excluded, whereas §1 describes the sweep as originally applied; (4) the
per-file attribution of the "44 → 3" warnings in `d0fe3aa3` is not recoverable
from the diff alone, because crate-level `#![allow(dead_code)]` is unbounded —
§4's 152 is a measurement at HEAD, not a reconstruction of that day's build.
