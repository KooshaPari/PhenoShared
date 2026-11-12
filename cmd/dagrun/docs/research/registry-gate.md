# Registry gate/artifact inventory relevant to the SCTBDD + autograder ecosystem direction

**Repo:** `~/CodeProjects/Phenotype/repos/phenotype-registry` (branch `docs/session-record-final-state`)
**Date:** 2026-11-11
**Task:** read-only. Identify the *actual existing* stage-gate and artifact governing documents, with exact paths and the applicable steps.
**Method:** 5 bounded read-only calls (agentgrep find/grep, bash listings, targeted `read`). No repo file was modified.

---

## 0. Headline: three negative findings that change the framing

| Query | Result across the whole repo | Meaning |
|---|---|---|
| `SCTBDD` | **0 matches in 0 files** | SCTBDD has **no artifact at all** in the registry. It is not yet a curated repo/product. Nothing in this repo governs it today. |
| `stage[- ]gate` | **2 matches, both incidental** — `chat-harvest/remote-desktop/transcript.md` (a raw chat transcript) and `ledger/stories/HeliosLab.story.md` (one commit-log line: `merge: Merge branch 'main' into fix/stage-gate-scripts-20260828`) | There is **no document named "stage gate"** in the repo. The concept exists, but under different names (see §1). Do not cite a "stage-gate doc" that does not exist. |
| `autograder` | 22 matches in 15 files — **all** in `audits/**`, `chat-harvest/**`, `handbook/specs/research/**` | **No live governing doc for "autograder" exists.** Every hit is an archived finding, a curated ask transcript, or SOTA research. |

**Consequence:** the SCTBDD/autograder direction cannot be attached to a pre-existing gate doc by name. It must be attached to the repo's *actual* gate vocabulary, which is: **capability/intent boundary → spec → WBS/DAG → PR stack → happy-path guard → reported-vs-verified evidence → atlas QA cell/obligation → grade artifact.**

---

## 1. TIER 1 — live governing documents (these are the real gates)

### 1.1 `docs/SSOT.md` — Capability & Intent SSOT (top of the authority chain)

**Governs:** what each repo in the fleet owns and does NOT own. Explicit precedence clause: *"When any other doc — `docs/registries.md`, README, the bound prompts, or the per-repo `docs/intent/<repo>.md` — contradicts this section, this section wins."*

**Canonical artifacts (4 files, L7-001 → L7-008 chain):**

| Path | Role |
|---|---|
| `docs/intent/<repo>.md` | canonical intent statement ("why does this repo exist, what is 'done'?") |
| `docs/boundary/<repo>.md` | in-scope / out-of-scope / crossings |
| `_bindings.json` (curation-data) | curated prompt hash list (provenance) |
| `ECOSYSTEM_MAP.md` (repo root) | role row in the §1 taxonomy |

Contract sources: `docs/intent/README.md` (L7-001) and `docs/boundary/_template.md` (L7-001).

**Applicable steps for SCTBDD / autograder:**
1. Create `docs/intent/SCTBDD.md` + `docs/boundary/SCTBDD.md` from the `_bindings.json` chain (L7-001 template), answering explicitly **who owns the grader** and **who owns the harness adapters**.
2. Regenerate the map: `python3 scripts/regen-ecosystem-map.py` (idempotent, ad-hoc on topology change).
3. Cadence gate: weekly Monday 09:00 PDT launchd job `com.phenotype.weekly-refresh` runs scrape → resolve-collision → render → propagate (71-pillar audit per ADR-041). Ad-hoc Saturday for new repo / archive / absorption / role reclassification.
4. Full render+propagate: `python3 scripts/render-per-repo.py --force` then `python3 scripts/propagate-intent-to-repos.py --force`.

**Authority precedence (2026-10-12 addendum, `docs/SSOT.md` §"bounded owner addendum"):** SSOT owns *capability boundaries*; each product's verbatim user intent owns *human requirements*; accepted ADRs own *their* decisions; implementation/test evidence owns *runtime capability claims*. A new addendum never silently rewrites the June 2026 census.

---

### 1.2 `docs/governance/overview.md` — the actual review stage gate

**The fixed sequence (verbatim from the doc):**

```
Draft → Auto-Validation → Review → Approval → Publish
  │             │              │        │         │
  │             │              │        │         └─ Deploy to production
  │             │              │        └─ Approve content
  │             │              └─ Technical review
  │             └─ Link check, build check
  └─ Initial creation
```

Quality-standard thresholds (the gate's pass criteria): broken links 0% (weekly link checker), build success 100% (CI), response time <3s (Lighthouse), accessibility 100% (axe-core).

**Applicable steps for any SCTBDD/autograder change that touches this repo:** Draft the change → run the link checker and build check → get technical review → get explicit approval → publish. Nothing skips Auto-Validation.

**Sub-governances linked from it (real paths):**

| Path | Step it adds |
|---|---|
| `docs/governance/stacked-prs/01-branching-and-channels.md` | branch + release channel selection |
| `docs/governance/stacked-prs/02-wbs-and-dag.md` | WBS/DAG rules for the change |
| `docs/governance/stacked-prs/03-pr-template.md` | PR stack template (required artifact shape) |
| `docs/governance/stacked-prs/04-merge-scenarios.md` | which merge path is legal |
| `docs/governance/stacked-prs/05-pr-reconciliation.md` | reconciling a stack before merge |
| `docs/governance/stacked-prs/README.md` | entry point |
| `governance/happy-path-checklist.md` | the 7 rules + 2 pitfalls, with FAIL patterns / PASS evidence (CNCF SLSA, OpenSSF, Google SRE, Microsoft SDL) |
| `governance/happy-path-precommit.sh` | executable guard on the staged diff, exits non-zero on collapse patterns |
| `governance/test-happy-path-allowlist.sh` | allowlist test for the guard |
| `docs/patterns/validation-rules.md` | validation-rule patterns |
| `patterns/traceability/requirements.md` | requirement traceability pattern |
| `patterns/methodology/xdd.md` | XDD methodology pattern (spec-driven loop) |
| `patterns/methodology/wrap-over-handroll.md` | wrap-over-handroll pattern |
| `patterns/governance/work-location-policy.md` | where work artifacts may live |
| `patterns/governance/mcp-fork-selection.md`, `patterns/governance/retired-mcp-repos.md` | MCP fork admission / retirement |

**Happy-path collapse guard — applicable steps (verbatim knobs):**
- Local run: `git add -A && bash governance/happy-path-precommit.sh`
- Pre-commit hook: `happy-path-collapse-guard` on the `commit` stage (`.pre-commit-config.yaml`)
- CI mirror: `.github/workflows/happy-path-precommit.yml` on every push and PR
- Knobs: `HAPPY_PATH_FAIL_ON=block|warn|off`, `HAPPY_PATH_DISABLE=rule1,rule2,...`, `HAPPY_PATH_BIG_CONSTANT_ALLOW=...`

**Project admission / retirement gates in the same doc:**
- Addition (5 steps): Proposal (open issue) → Review (docs lead checks structure) → Integration (add to HubGenerator) → Verification (test build and navigation) → Launch (merge and announce). Addition criteria: active project, proper structure, required frontmatter, designated owner.
- Removal (4 steps): Notice (30-day warning) → Archive (move to `/archive/`) → Remove (from HubGenerator) → Update (regenerate hub). Removal criteria: no commits >6 months, archived upstream, owner requests.

---

### 1.3 `asks-ledger/MANAGEMENT-CONTRACT.md` — the repo's existing "grader" semantics (highest leverage for an autograder)

**Governing principle (verbatim):** the cockpit separates *what an agent claims* from *what has been independently checked*. A `reported_state` of `DONE` **is a claim, not a fact** until `verified_state` says otherwise. Every new ask loads with `verified_state = "Pending review"`, `reviewed = 0`.

**Two-axis model:**

| Field | Owner | Values |
|---|---|---|
| `reported_state` | the doer / claimant | `DONE`, `RUNNING`, `TRACKED`, `PARTIAL`, `DEFERRED-BY-HIM`, `WAITING-ON-HIM`, … |
| `verified_state` | independent reviewer | defaults to `Pending review` |
| `reviewed` | reviewer | 0/1 |

**Evidence shape (the artifact an autograder must emit):**
```json
{"kind":"commit|pr|issue|file|url","ref":"...","observed_at":"RFC3339"}
```

**Five mechanically-validated invariants (these are the gate):**
1. `reported_state = DONE` requires non-empty evidence — a claim without a reference is noise.
2. `verified_state` may only be advanced by a reviewer who cites evidence.
3. A single occurrence of an ask is never evidence of completion.
4. `reconciled_at` is set only when `verified_state` leaves `Pending review`.
5. `DEFERRED-BY-HIM` / `WAITING-ON-HIM` are legitimate states but **must name who is blocking**, never a silent drop.

**One authority per fact (surface map):** `asks.json` (dataset — the only place an ask's identity lives) · Cloudflare D1 `job-cockpit` (queryable store the dashboard reads) · Paperclip `PHE-###` (management rollups) · GitHub issues (engineering traceability) · `dash.kooshapari.com` (read-only view). Every other surface references by ID and never re-states it.

**Canonical field mapping (do not invent parallel names):** `original_text`, `interpretation`, `first_asked_at`, `source_refs_json[{kind,at}]`, `task_links_json[{label,status}]`, `reported_state`, `verified_state`, `reconciled_at`, `updated_at`.

**Identity:** `ASK-000001`…`ASK-002259` (six digits, deterministic from `(day, time, normalised text)` so a reload never renumbers); themes `THEME-T###` only when `count >= 2` (125 of 2,091).

**Revision note (Revision 2, 2026-11-09):** Revision 1's invented status lifecycle was **removed**; this contract conforms to the cockpit's existing model instead of duplicating it.

**Why this matters for SCTBDD/autograder:** the repo already owns a *reported-vs-verified* gate with evidence invariants and DB-level enforcement. An SCTBDD autograder should be a **verifier that populates `verified_state` + evidence**, not a second, parallel grading path.

---

### 1.4 `asks-ledger/gate-invariants.sql` — machine-enforced form of §1.3

DB triggers/constraints (~8 `BEGIN` blocks) that encode the invariants at the storage layer. Any new artifact field (e.g. an autograder verdict) must be admitted here first, not in application code.

---

### 1.5 `asks-ledger/policies.md` — 65 standing rules that bind any autograder fleet

Rebuilt 2026-11-09 from `register.json` + `themes.json` after the original lane outputs were lost in the `Phenotype/repos` deletion. **The original restatement ranking is NOT reproducible** and is not claimed; rules are listed by area then chronologically. Directly binding rules for this direction:

| # | Area | Rule |
|---|---|---|
| 56 | harness | Prohibit the main agent from doing research and planning directly — delegate to sub-agents |
| 32 / 33 | general | Enforce one-agent-per-repo and one-agent-per-non-repo-bound-intent concurrency |
| 44 | general | Recover work that agents never committed or mangled into deep branch and commit sprawl |
| 45 | general | Never return with unknown information; research until resolved |
| 46 | general | Investigate and fix unexpected operator-interaction faults |
| 37 / 49 | general | Never use paid GitHub Actions CI / never let GitHub receive a charge |
| 41 | general | Sign Pose Snap ASAP without deferring |
| 34 / 35 | general | Never let work silently stall; actually begin and advance stalled items |
| 61 | instinct | Point direct-access at always-on assistants |

---

### 1.6 `docs/governance/atlas/` — the artifact-contract layer (obligations, QA cells, applet contract)

This is where a new ecosystem participant's *artifacts* are formally typed. Concrete artifact files:

| Path | Artifact |
|---|---|
| `docs/governance/atlas/MANIFEST.json` | manifest of the atlas governance corpus |
| `docs/governance/atlas/SHA256SUMS` | integrity digests for the artifacts |
| `docs/governance/atlas/federation/input-artifact-review.json` | the **input-artifact review** gate (federation) |
| `docs/governance/atlas/examples/obligation.json` | obligation contract |
| `docs/governance/atlas/examples/qa-cell.json` | QA cell (one cell = one checkable claim) |
| `docs/governance/atlas/examples/qa-manifest.json` | QA manifest |
| `docs/governance/atlas/examples/qa-report-synthetic.json` | QA report shape |
| `docs/governance/atlas/examples/pilot-plan.json` | pilot plan |
| `docs/governance/atlas/examples/ecosystem-impact.json` | ecosystem-impact assessment |
| `docs/governance/atlas/examples/applet.json` | applet boundary contract |
| `docs/governance/atlas/examples/entity.json`, `relation.json` | entity/relation model |
| `docs/governance/atlas/examples/dissatisfaction.json` | dissatisfaction record |
| `docs/governance/atlas/products/PhenoRegistry/PILOT.json` | this product's pilot entry |
| `docs/governance/atlas/portfolio/topic-proposals.json` | portfolio topic proposals |
| `docs/governance/atlas/references/prior-62-assessments.json` | prior assessment baseline |

**Applicable steps:** an SCTBDD/autograder ecosystem proposal is admitted as an atlas **applet** with an `obligation.json` set, a `qa-cell.json` per checkable claim, a `qa-manifest.json` aggregating them, an `ecosystem-impact.json`, and a `pilot-plan.json`; the input artifact then passes `input-artifact-review.json`; digests land in `SHA256SUMS`.

---

### 1.7 `docs/contracts/event-envelope.md` + `docs/contracts/event-envelope.schema.json` + `docs/decisions/0003-global-ledger-event-envelope.md`

The event-envelope contract any autograder verdict/report must conform to in order to be ledger-visible. Decision record `docs/decisions/0001-record-architecture-decisions.md` explains the ADR convention.

### 1.8 `docs/decisions/0002-global-nested-ledger-actor-contract.md` (+ the `docs/SSOT.md` addendum that references it)

One global logical, immutable, recursively nested ledger; `Human` and `SoftwareAgent` under the same `Actor` superclass. **Product scope table is the boundary gate for an autograder ecosystem:**

| Product | Canonical scope |
|---|---|
| ShareCLI | local work admission, optimizer, shared producers, native resource governor |
| PhenoFabric | cross-host topology/placement, object residency, authority epochs, local coordinator persistence |
| PhenoRegistry | fleet capability/intent index, historical curation, owner policy — **"Do not execute or store live transactions"** |

**Applicable step:** the autograder's authority boundary must be assigned to one of these. PhenoRegistry cannot host the runtime grader; it can only index it.

---

## 2. TIER 2 — gate machinery that exists but is design-level, not enforced

| Path | What it gives an SCTBDD/autograder direction |
|---|---|
| `docs/specs/pheno-specs/specs/platform/002-org-wide-release-governance-dx-automation/tasks/WP06-gate-evaluation-engine.md` | **The only real "gate engine" design in the repo.** T032 Gate Criteria Data Model, T033 Gate Evaluator Implementation, T034 **Risk-Based Promotion Rules**, T035 Structured Report Formatting. This is the design an autograder should conform to (gate criteria → evaluator → promotion rule → structured report). |
| `docs/specs/pheno-specs/specs/platform/002-org-wide-release-governance-dx-automation/meta.json` | enclosing spec metadata |
| `docs/specs/pheno-specs/specs/platform/001-spec-driven-development-engine/tasks/WP04-domain-governance-audit.md` | governance/audit work-package template for the SDD engine |
| `docs/specs/pheno-specs/specs/platform/gateway/SPEC.md`, `ADR.md`, `docs/research/gateway-comparison-research.md` | gateway architecture and comparison (route selection for an autograder backend) |
| `docs/governance/journey-traceability.md` and `docs/operations/journey-traceability.md` | journey-traceability gate (flows → journeys → verification) |
| `docs/spine/SPINE-DEFINITION.md`, `patterns/spine-roles.md`, `docs/spine/phenoDesign.md`, `docs/spine/PhenoMCPServers.md` | the "spine" role/element model |
| `QUALITY_LOOP.md` | the closest thing to a canonical stage-gate-with-evidence artifact: 7 measured gates (frozen install → strict TS → vitest → 8/8 FR traceability → VitePress build → 3/3 Playwright journeys → audit), 42/42 workflow-policy checks, and the `Control / State / Exact evidence` table convention ("Baseline deltas are measured, not estimated"). Use this table shape for autograder gate reporting. |
| `docs/planning/full-turn-next24-20260326.md`, `docs/planning/full-turn-next50-20260326.md` | planning-round conventions |
| `agileplus-specs/`, `kitty-specs/` | spec inputs consumed by the AgilePlus / Kitty spec-driven flows (`agileplus_specify` reads a spec under `kitty-specs/`) |

---

## 3. TIER 3 — grade and receipt artifacts (real, but thin)

| Path | Note |
|---|---|
| `grades/BytePort/2026-06-29.json` | a grade artifact — one of only **two** grade files in the repo |
| `grades/PhenoCompose/2026-06-29.json` | ditto |
| `grade.sh`, `_grade_three.py` | grading entry points (repo root) |
| `benches/criterion_bench.rs` | criterion benchmark harness |
| `audit_scorecard.json`, `user-scorecard.json` | scorecard artifacts |
| `audits/harnessdesk/state-forward-2026-10-17/REGISTRY-GATE-RECEIPT.json` | a literal **registry gate receipt** artifact (harnessdesk state-forward) |
| `docs/registry-sweep-2026-06-24.md`, `docs/state-verification-2026-06-24.md` | registry-wide sweep + state verification |

**Observation:** grades exist for exactly two repos and are dated 2026-06-29. There is no repo-wide grade pipeline. An "autograder ecosystem" is greenfield against this surface.

---

## 4. TIER 4 — archive / research / transcript material that mentions "autograder" but does NOT govern

Treat these as **provenance and prior art only**, never as policy:

| Path | What it actually is |
|---|---|
| `audits/org-audits/findings/2026-06-18-McpKit-branch-only/journey-traceability-RICH.md` | archived finding; *"Tests/Gates — unit, integration, contract, protocol compliance, lint, and journey verification acting as autograders"*; 6-flow table with "autograder gates" |
| `audits/org-audits/findings/2026-06-18-McpKit-branch-only/README.md` + `BRANCH_PROVENANCE.md` | provenance of that file; it existed only on a dangling local ref (`430a882`), never on a remote branch |
| `audits/org-audits/curation/forge/candidates.tsv` (and `audits/org-audit-snapshots/curation/forge/candidates.tsv`) | raw ask text: *"Design the autograder for `phenotype-teamcomm`. This is the conformance testing system…"* — an **ask**, not a spec |
| `chat-harvest/byteshare-old/transcript.md` | raw chat transcript containing "Oracle/autograder specification" and *"Adopt the MACE / autograder control-loop model"* |
| `chat-harvest/byteshare-old/code/block-0119.txt` | *"mechanical developer work-package DAGs and independent autograder contracts"* (transcript fragment) |
| `handbook/specs/research/ecosystem/ChatGPT-Software Project Traceability Tools.md` | SOTA research: artifacts + definitions forming "an assumed perfect autograder/oracle for agents to iterate against"; also notes audit/compliance tools are **not** autograder systems |
| `docs/operations/archive-gate-verification-2026-06-18.md` | a real but **historical** archive/delete stage gate with per-repo gate sections (`pheno archive gate (W18b-G)`, `Pyron archive gate (P4)`, `phenoShared archive gate (P4 wave 5b closeout)`) — the best available *template* if SCTBDD is ever retired |

---

## 5. Applicable steps, consolidated for the SCTBDD/autograder direction

1. **Admit the repo (SSOT chain).** `docs/intent/SCTBDD.md` + `docs/boundary/SCTBDD.md` via `docs/intent/README.md` + `docs/boundary/_template.md` (L7-001); regenerate `ECOSYSTEM_MAP.md`; absorb in the Monday `com.phenotype.weekly-refresh` cycle. — `docs/SSOT.md`
2. **Assign the authority boundary.** Decide whether the grader is admitted via ShareCLI (work admission), PhenoFabric (placement/epochs) or PhenoRegistry (index only, and it *must not* store live transactions). — `docs/decisions/0002-…`, `docs/SSOT.md` addendum
3. **Type the artifacts as atlas obligations + QA cells.** `obligation.json` per obligation, `qa-cell.json` per checkable claim, `qa-manifest.json`, `ecosystem-impact.json`, `pilot-plan.json`; then pass `federation/input-artifact-review.json`; register digests in `SHA256SUMS`. — `docs/governance/atlas/`
4. **Conform the gate engine.** Implement gate criteria → evaluator → risk-based promotion → structured report per WP06 (T032–T035) rather than inventing a new gate format. — `docs/specs/.../002-.../tasks/WP06-gate-evaluation-engine.md`
5. **Use the reported-vs-verified axis for verdicts.** Emit `{"kind","ref","observed_at"}` evidence; never write `DONE` without evidence; let an independent reviewer move `verified_state` off `Pending review`; name the blocker for `DEFERRED-BY-HIM` / `WAITING-ON-HIM`. Enforce in `asks-ledger/gate-invariants.sql`, not in app code. — `asks-ledger/MANAGEMENT-CONTRACT.md`, `asks-ledger/gate-invariants.sql`
6. **Emit ledger-visible reports through the event envelope.** — `docs/contracts/event-envelope.md` + `.schema.json`
7. **Stack and merge per the PR rules.** Branch/channel → WBS/DAG → PR template → merge scenario → reconciliation. — `docs/governance/stacked-prs/01..05`
8. **Satisfy the happy-path guard before commit.** `git add -A && bash governance/happy-path-precommit.sh`; the same checks run as a pre-commit hook and in CI. — `governance/happy-path-checklist.md`, `governance/happy-path-precommit.sh`
9. **Report gates as `Control / State / Exact evidence`** with measured (not estimated) deltas, following the existing 7-gate loop. — `QUALITY_LOOP.md`
10. **Respect the standing rules that constrain the fleet**: one-agent-per-repo / per-intent concurrency, no main-agent research, no paid GitHub Actions CI, never stall silently. — `asks-ledger/policies.md`

---

## 6. Unknowns / follow-ups (evidence-backed, not guessed)

- **`AGENTS.md` (repo root) could not be read** — the read tool returned `stream did not contain valid UTF-8`. It is the repo's own agent contract and may contain additional repo-local gates. **Action:** read it via `iconv -f UTF-8 -t UTF-8 -c AGENTS.md | head -200` or `LC_ALL=C tr -d '\000' < AGENTS.md`. It was *not* read in this pass.
- **`repos/harness-ops/AGENTS.md` and `repos/harness-ops/PROVENANCE.md`** are modified in the working tree and are plausibly the harness-adapter governance set (relevant if SCTBDD ships harness adapters). **Not read** in this pass.
- **`docs/acceptance-contracts/` is empty** — the directory exists but holds no files, so it is not a usable artifact surface despite the name.
- **Only two grade artifacts exist** (`grades/BytePort/2026-06-29.json`, `grades/PhenoCompose/2026-06-29.json`), both dated 2026-06-29. There is no general grade pipeline to extend.
- **SCTBDD itself is entirely absent** from the repo (0 hits for the string). Any prior SCTBDD spec, if it exists, is either in another repo or in the `chat-harvest/` transcripts, not in the registry's governing corpus.
- `docs/governance/overview.md` is a mirror of `handbook/docs/governance/overview.md` — treat `docs/governance/overview.md` as canonical and `handbook/` as the published copy (not independently edited).

**Method / budget:** 5 bounded read-only calls used (1 failed batch on a tool-schema error, 4 productive: agentgrep find+grep ×2, bash listings ×2, targeted reads ×3 inside batched calls). No repo file was modified; the only write is this report.
