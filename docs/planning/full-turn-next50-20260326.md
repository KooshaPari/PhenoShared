---
title: Full-turn Next 50 (DAG)
---

# Next 50 — full-turn + shipping (5 agents × 10 waves)

**Norm:** [Full-turn delivery](../guides/full-turn-delivery.md)

## Batch shape (DAG)

| Concept | Definition |
|--------|-------------|
| **Lanes** | **A–E** — at most **one active task per lane** (five concurrent agents). |
| **Waves** | **W1–W10** — each wave schedules up to **five** tasks (one per lane). **50 tasks** total (`T01`–`T50`). |
| **Edges** | **Depends** lists upstream task IDs. A task is **ready** when all dependencies are **done** (merged or explicitly checked off). |
| **Parallelism** | Within a wave, tasks are independent **unless** Depends says otherwise. **Do not** exceed five concurrent tasks across lanes. |
| **Merge rule** | Each **full turn** still lands **≥1 PR** to `main` or `release/*`, with **`gh` visibility**, **CHANGELOG**, **version note**, and **docs build** as in the guide. |

### ASCII DAG (skeleton)

```text
        W1          W2          W3                    W10
     ┌──────┐    ┌──────┐    ┌──────┐              ┌──────┐
  A  │ T01  │───►│ T06  │───►│ T11  │─── ... ─────►│ T46  │
  B  │ T02  │───►│ T07  │───►│ T12  │─── ... ─────►│ T47  │
  C  │ T03  │───►│ T08  │───►│ T13  │─── ... ─────►│ T48  │
  D  │ T04  │───►│ T09  │───►│ T14  │─── ... ─────►│ T49  │
  E  │ T05  │───►│ T10  │───►│ T15  │─── ... ─────►│ T50  │
     └──────┘    └──────┘    └──────┘              └──────┘
     (cross-links and merge gates add edges across lanes/waves — see Depends per task)
```

---

## W1 — bootstrap (all parallel)

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T01 | A | Record **PR URL** + merge ref in **CHANGELOG [Unreleased]** or PR body for every ship. | — |
| T02 | B | **CHANGELOG** discipline: every user-visible merge updates **[Unreleased]**; note if version N/A. | — |
| T03 | C | **Full-turn** callout on [views index](/views/); link guide + this Next 50. | — |
| T04 | D | Document **CodeQL `languages: actions`** rationale (VitePress/Vue vs JS extraction) in workflow comment or `docs/`. | — |
| T05 | E | **gh** habit: `gh pr list`, `gh pr view`, `gh pr checks` before merge; keyring auth only. | — |

## W2 — GitHub + visibility

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T06 | A | Optional **`full-turn`** label on merge PRs; document in guide. | T01 |
| T07 | B | **Version**: when to bump `package.json` (tagged release vs docs-only); CalVer vs SemVer note. | T02 |
| T08 | C | **Roadmap** line: “Full-turn discipline” under next milestones. | T03 |
| T09 | D | **Deploy** `deploy.yml`: confirm **post-merge** run and badge matches repo. | T04 |
| T10 | E | **Release branch** naming (`release/x.y`) in guide if used. | T05 |

## W3 — Changelog + site

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T11 | A | **Stacked PRs:** one sentence in **AGENTS** — each layer merges before closing turn; linear history for policy-gate. | T06 |
| T12 | B | **When not to bump** version (typo, internal-only) — README or small doc. | T07 |
| T13 | C | **Workspace views → changelog** page links root **CHANGELOG** clearly. | T08 |
| T14 | D | **CI parity:** local `bun run build` matches **Deploy** job. | T09 |
| T15 | E | **Metrics:** merged PR count / month in roadmap narrative (manual is OK). | T10 |

## W4 — Quality + docs

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T16 | A | **PR template** snippet: checklist for changelog, version note, `gh` link. | T11 |
| T17 | B | Research **changesets** vs **git-cliff**; one-paragraph recommendation in planning note. | T12 |
| T18 | C | **`docs/views/commits`:** sketch **CI job** to refresh `commit-log.json` (issue or session artifact). | T13 |
| T19 | D | **Lint:** run `bun run lint` on PR when only `docs/**/*.md` touched (workflow or doc). | T14 |
| T20 | E | **Cross-link** [AgilePlus](https://github.com/KooshaPari/AgilePlus) `full-turn-delivery` one sentence (org norm). | T15 |

## W5 — Automation + federation

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T21 | A | **Dead links:** `bun run check-links` (uses `uv run python …`) before merge when links change. | T16 |
| T22 | B | **Sidebar:** keep **Planning** + **Workspace views** in sync with new pages. | T17 |
| T23 | C | **Rich workspace views** plan: pick **three** implementation tasks for next implementation PR. | T18 |
| T24 | D | **Security guard** workflows: document what runs on PR vs `main`. | T19 |
| T25 | E | **Worktree policy** xref (`repos/worktrees/...`) in **AGENTS** or guide. | T20 |

## W6 — Org + integration

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T26 | A | **Phenotype Git protocol** link in full-turn guide (stacked PRs, CI completeness). | T21 |
| T27 | B | **Tag strategy:** document `v0.x` tags for hub vs moving **Unreleased** to dated section. | T22 |
| T28 | C | **ModuleSwitcher / nav:** verify new planning page appears everywhere needed. | T23 |
| T29 | D | **Dependabot:** review open PRs; document merge policy for deps. | T24 |
| T30 | E | **Post-merge:** `git pull` integrator clones; script one-liner in README. | T25 |

## W7 — Research + depth

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T31 | A | **Mermaid** optional for DAG diagrams in **views/wbs** (embed vs build-time). | T26 |
| T32 | B | **ADR stub:** “Why Actions-only CodeQL” — link CHANGELOG + troubleshooting URL. | T27 |
| T33 | C | **Federation** doc: how other repos feed PhenoDocs (index + ownership). | T28 |
| T34 | D | **Reusable workflow** audit: which jobs could be `workflow_call` for forks. | T29 |
| T35 | E | **Ownership:** CODEOWNERS for `docs/` + `.vitepress/` (if not present, add issue). | T30 |

## W8 — Hardening

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T36 | A | **Branch protection** doc: what blocks direct push (matches your **policy-gate** story). | T31 |
| T37 | B | **Semantic versioning** for `package.json` when publishing npm package (if ever). | T32 |
| T38 | C | **Search:** verify local search includes `/planning/` new pages. | T33 |
| T39 | D | **Artifact retention** for workflow runs (days) documented for debugging CI. | T34 |
| T40 | E | **Secrets:** confirm no tokens in PR bodies; link GitHub secret scanning. | T35 |

## W9 — Polish + scale

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T41 | A | **Contributing:** “full turn” subsection for external contributors. | T36 |
| T42 | B | **Changelog** archive: move old [Unreleased] blocks to dated sections on release. | T37 |
| T43 | C | **Preview deploy** for PRs (if not already): document URL pattern. | T38 |
| T44 | D | **Node version** matrix: document `engines` vs CI `node-version`. | T39 |
| T45 | E | **50-item batch** retrospective: what to automate next (issue). | T40 |

## W10 — Closeout

| ID | Lane | Task | Depends |
|----|------|------|---------|
| T46 | A | **Dogfood:** one PR that only updates **Next 50** + evidence links; merge. | T41 |
| T47 | B | **Version bump** only if releasing; else PR states **version: N/A**. | T42 |
| T48 | C | **Site** smoke: home, `/views/`, `/planning/full-turn-next50-20260326`. | T43 |
| T49 | D | **CI green** on `main` after last merge; screenshot or `gh run list` note. | T44 |
| T50 | E | **Next batch:** fork this file to `full-turn-next50-<date>.md`; reset DAG; rotate themes. | T45 |

---

## Done when

- **≥1 merged PR** per full turn to **`main`** or **`release/*`**, with **`gh`** trail, **CHANGELOG** (when user-visible), **version** note, **docs build** when site changes.
- **Five agents** stay within **five concurrent tasks**; **Depends** respected (DAG, not a free-for-all).
- This **50-item** batch is reviewable in **10 waves** of parallel work.

## Supersedes

- [Full-turn Next 24](./full-turn-next24-20260326.md) — smaller batch; keep for history.
