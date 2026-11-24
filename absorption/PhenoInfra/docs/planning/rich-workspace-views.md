# Rich workspace views — product plan

PhenoDocs federates multi-repo documentation. **Workspace views** are first-class **modules** (or routed pages) oriented around how teams actually work: **plan**, **research**, **spec**, **work**, **roadmap**, **changelog**, **git history**, and **WBS/DAG**—not only static articles.

## Goals

| View | Purpose | Rich elements |
|------|---------|----------------|
| **Plan** | Execution intent, phases, owners | Tables, status badges, links to WPs |
| **Research** | Discovery, options, citations | Callouts, comparison tables, external links |
| **Spec** | SHALL/acceptance, contracts | Numbered requirements, trace IDs |
| **Work** | Tasks, worklogs, PRs | Checklists, commit/PR references |
| **Roadmap** | Time horizons, themes, bets | Timeline bands, priority matrix (see [Roadmap](/roadmap/)) |
| **Changelog** | User-visible deltas | Version sections, categories (Added/Changed/Fixed) |
| **Commit log** | Engineering audit trail | SHA, author, repo, subject ([demo](/views/commits)) |
| **WBS / DAG** | Dependencies, ordering | Graph or table DAG (see [governance WBS](/governance/stacked-prs/02-wbs-and-dag)) |

## Existing building blocks

- **Document index** buckets: [Planning](/index/planning), [Specs](/index/specs), [Research](/index/research), [Worklogs](/index/worklogs).
- **Components:** `AuditTimeline`, `CategorySwitcher`, `ModuleSwitcher`, `KBGraph`, `NavTabs`, `ContentTabs`, `DocStatusBadge` (see `.vitepress/theme/components/`).
- **Governance:** stacked PRs, branching, WBS content under [Governance](/governance/overview).

## Phased delivery

### Phase 1 — IA + samples (current)

- [Workspace views hub](/views/) with changelog, commit log, and WBS entry points.
- `CommitLog` Vue view backed by `.vitepress/data/commit-log.json` (CI can overwrite from `git log --json` or similar).
- `audit-log.json` present so `AuditTimeline` builds.

### Phase 2 — Generated data

- Nightly or on-merge job: emit `commit-log.json`, `changelog.json` (parsed Keep a Changelog), `roadmap.json` from repo manifests or GitHub Projects.
- Optional: embed **mermaid** for DAG after adding `vitepress-plugin-mermaid`.

### Phase 3 — Cross-repo federation

- Pull plan/spec snippets from linked repos (manifest in hub config) into unified **Plan** and **Spec** surfaces with provenance footer.

## Contracts (draft)

- **`commit-log.json`:** array of `{ sha, date, author, subject, repo? }`.
- **`audit-log.json`:** array of `{ title, date, type, status, path? }` (existing `AuditTimeline` shape).
- **Changelog:** prefer hub `CHANGELOG.md` or JSON slice for embedding in a rich page without duplicating prose.

## Related

- [Workspace views hub](/views/)
- [Roadmap](/roadmap/)
