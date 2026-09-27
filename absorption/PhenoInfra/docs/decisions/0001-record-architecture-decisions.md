# AU2 Decision Records Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — AU2 (Auditability: decision records) is P2 priority (7/11 audited repos at score 0).
> **Method:** Add a `docs/decisions/` directory with Architecture Decision Records (ADRs) for the major decisions in the repo.
> **How to use:** Copy the template below to your repo as `docs/decisions/0001-template.md`, then fill in real decisions. Lifts AU2 from 0 to 2 (wired).

## What is AU2?

AU2 (Auditability: decision records) = significant decisions in the repo are recorded in a structured, searchable format with date, status, context, decision, and consequences. The classic format is MADR (Markdown Any Decision Record) or the older Nygard ADR.

**The "wired" (AU2=2) signal**: `docs/decisions/` (or `docs/adr/`) exists with at least 1 ADR; the ADRs are indexed (e.g., README.md links to them); at least 1 ADR is dated within the last year.

## Template: `docs/decisions/0001-record-architecture-decisions.md`

```markdown
# 1. Record architecture decisions

Date: 2026-06-17

## Status

Accepted

## Context and Problem Statement

We need to record the architectural decisions made on this project. Which decisions are documented, in what format, and how are they maintained?

## Considered Options

- **MADR** (https://adr.github.io/madr/) — Markdown Any Decision Records. Lightweight, lives in the repo, no tooling required.
- **adr-tools** (https://github.com/npryce/adr-tools) — CLI for managing ADRs. Adds tooling dependency.
- **Lightweight decision log** — single file, no per-decision file. Simpler but less searchable.
- **No decision log** — implicit. Loses institutional knowledge.

## Decision Outcome

Chosen option: **MADR**, because it lives in the repo (no external tooling), is searchable via grep, and follows a well-known template.

### Consequences

* Good, because decisions are durable + searchable.
* Good, because new contributors can read the rationale for past decisions.
* Bad, because the ADRs add documentation overhead.
* Neutral, because MADR is just markdown — no tooling lock-in.

### Confirmation

- [ ] `docs/decisions/` directory exists
- [ ] This template is checked in
- [ ] Future decisions are added as `NNNN-short-title.md` with the same template

## Pros and Cons of the Options

### MADR

* Good, because lives in the repo, no external tooling.
* Good, because well-known template.
* Bad, because requires manual discipline to add new ADRs.

### adr-tools

* Good, because CLI-driven.
* Bad, because adds tooling dependency.
* Bad, because not all developers will install the CLI.

### Lightweight decision log

* Good, because simplest.
* Bad, because not searchable.
* Bad, because doesn't scale beyond a handful of decisions.

### No decision log

* Good, because zero overhead.
* Bad, because institutional knowledge is lost when contributors leave.
* Bad, because new contributors don't know why things are the way they are.
```

## How to apply

1. Copy the template above to your repo as `docs/decisions/0001-record-architecture-decisions.md`.
2. Add at least 1 more ADR documenting a real decision the repo has made (e.g., why a particular dependency, why a particular pattern).
3. Create `docs/decisions/README.md` that lists all ADRs (this is the index).
4. Reference from the repo's main `README.md` (1 line under "Documentation").
5. Commit + push + open a PR.

## AU2 score lift

- **0 → 1 (ad-hoc):** `docs/decisions/` exists but no ADRs.
- **0 → 2 (wired):** `docs/decisions/` exists with at least 1 ADR; the ADRs are indexed in a README; the repo's main README links to `docs/decisions/`.
- **0 → 3 (measured):** the repo's PR template requires an ADR for any change to a "critical" file (e.g., CI workflows, security configs); a CI check fails if a "critical" PR doesn't have an ADR.

## Reference: OmniRoute

OmniRoute is the reference repo for AU2 (AU2=3). It has 4 ADRs in `docs/adr/`, indexed by `docs/adr/README.md`, referenced from the main `README.md`, and a PR template that requires an ADR for any critical-file change. The template above is a minimal extraction of that pattern.

## How to validate

After applying:
1. `ls docs/decisions/` — should show at least 1 ADR + README.md
2. `grep "decisions\|ADR" README.md` — should find a reference
3. The ADR file follows the MADR template (Status, Context, Decision, Consequences sections)

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (AU2 P2)
- **Reference repo:** `KooshaPari/OmniRoute` (AU2=3)
- **License:** Same as the parent repo
