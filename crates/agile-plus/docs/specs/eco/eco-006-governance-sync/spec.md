---
spec_id: eco-006-governance-sync
state: IN_PROGRESS
plan_status: REQUIRED
last_audit: 2026-05-02
---

# Specification: Governance Sync Automation
**Slug**: eco-006-governance-sync | **Date**: 2026-05-02 | **State**: in_progress

## Problem Statement

The Phenotype/AgilePlus ecosystem spans 61+ Rust repos, multiple worktrees, and a growing body of governance docs. Governance drift — stale CLAUDE.md files, missing policy requirements, orphaned worklog entries, or out-of-sync kitty-specs — erodes compliance and makes it impossible for agents to trust workspace state. Manual governance audits do not scale.

## Target Users

- Agent workflows (via `dispatch` skill and `agileplus governance` CLI)
- DevOps / platform engineers monitoring ecosystem health
- Compliance auditors (via audit query CLI and compliance reports)

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-GOV-01 | Inventory all governance artifacts (CLAUDE.md, kitty-specs, worklogs, policy docs) across the ecosystem |
| FR-GOV-02 | Generate canonical fingerprints for each governance artifact |
| FR-GOV-03 | Detect drift between current inventory and canonical baseline |
| FR-GOV-04 | Classify drift by severity: BREAKING, MINOR, DOCUMENTATION, ORPHANED |
| FR-GOV-05 | Trigger governance sync on every PR via CI workflow |
| FR-GOV-06 | Block merge on BREAKING drift (GitHub status check) |
| FR-GOV-07 | Route notifications based on drift type and severity |
| FR-GOV-08 | Suppress repeat alerts for same drift within 24h window |
| FR-GOV-09 | Hold BREAKING drift in ReviewQueue for human approval |
| FR-GOV-10 | Auto-fix MINOR/DOCUMENTATION drift without human intervention |
| FR-GOV-11 | Rollback applied fixes via `agileplus governance rollback` |
| FR-GOV-12 | Maintain hash-chained evidence ledger of all sync events |
| FR-GOV-13 | Audit query CLI for compliance reporting |

## Non-Functional Requirements

- **Latency**: iMessege alerts fire within 60s of drift detection
- **Safety**: No auto-fix for BREAKING drift; always requires human approval
- **Tamper-evidence**: Ledger hash chain detects any modified event
- **Auditability**: All sync events logged with actor, timestamp, and diff
- **CI-compatible**: Governance sync runs in non-interactive mode for GitHub Actions

## Constraints & Dependencies

- Relies on agent-imessage MCP for iMessege delivery
- GitHub API access required for PR comments and status checks
- Relies on existing worklogs/ directory structure
- Hash-chain ledger stored in `agileplus/.governance-ledger/`

## Acceptance Criteria

| AC | Criterion |
|----|-----------|
| AC01 | `agileplus governance sync --dry-run` produces valid JSON/CSV output without modifying any files |
| AC02 | CI workflow triggers on every PR and blocks merge on BREAKING drift |
| AC03 | iMessege alert fires for BREAKING drift within 60s of detection |
| AC04 | ReviewQueue holds BREAKING drift until approved |
| AC05 | Hash-chain ledger is tamper-evident (modified event breaks chain) |
| AC06 | Audit query returns correct event history for a given repo |
| AC07 | Orphaned kitty-spec entries are detected and flagged |
