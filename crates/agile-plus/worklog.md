# Worklog

**This project is managed through AgilePlus.**

## TruffleHog + deny.toml Fixes — 2026-05-03

| Item | Status |
|------|--------|
| deny.toml: add allow-registry to 23 Rust repos | ✅ 15 committed+pushed, 5 already correct, 3 N/A |
| trufflehog.yml: expand branch scan to chore/** feat/** fix/** | ✅ Applied |
| AGENTS.md: clean CRLF/binary corruption, re-create | ✅ Applied |
| Branch: reset to origin/main (force-pushed by org-bootstrap agent) | ✅ Clean base |

## TruffleHog + deny.toml Fixes — 2026-05-03

| Item | Status |
|------|--------|
| deny.toml: add allow-registry to 23 Rust repos | ✅ 15 committed+pushed, 5 already correct, 3 N/A |
| trufflehog.yml: expand branch scan to chore/** feat/** fix/** | ✅ Applied |
| AGENTS.md: clean CRLF/binary corruption, re-create | ✅ Applied |
| Branch: reset to origin/main (force-pushed by org-bootstrap agent) | ✅ Clean base |

## Ecosystem Cleanup Complete - 2026-03-29

### ECO Work Package Status

| ID | Work Package | Status |
|----|-------------|--------|
| ECO-001 | Worktree Remediation | ✅ COMPLETE |
| ECO-002 | Branch Consolidation | ✅ COMPLETE |
| ECO-003 | Circular Dependency Resolution | ✅ SHIPPED (CI CONFIGURED) |
| ECO-004 | Hexagonal Migration | ✅ NO WORK NEEDED |
| ECO-006 | Final Merge Stabilization | ✅ COMPLETE (2026-03-29) |

### Merge Stabilization Complete

| Repo | PRs Merged | Status |
|------|------------|--------|
| thegent | pr-679, pr-680, pr-681, pr-682, pr-833 | ✅ |
| AgilePlus | pr-208 | ✅ |
| portage | phase2-decompose branches | ✅ |
| template-commons | governance, policy, hardening | ✅ |
| 4sgm | fix/stabilize branches | ✅ |
| agentapi-plusplus | fix/pr16 | ✅ |
| phenotype-config | stabilization | ✅ |
| cliproxyapi | pr-928 closed (diverged) | ✅ |
| trace | stabilization | ✅ |
| tokenledger | stabilization | ✅ |

### Quality Gate Results

| Metric | Result |
|--------|--------|
| Python syntax errors | 0 (1 fixed) |
| Ruff lint errors | 0 (21 fixed) |
| Tests passed | 83/83 |
| Non-canonical folders | Cleaned (tmp, hoohacks, 485, 20 empty packages) |

### Cleanup Actions Completed

| Action | Status | Location |
|--------|--------|----------|
| WP20 worktree path | ✅ Updated | tasks/WP20-hidden-subcommands.md |
| WP21 worktree path | ✅ Updated | tasks/WP21-cli-triage-queue.md |
| Archived legacy wtrees | ✅ Done | archive/legacy-wtrees/2026-03-28/ |
| ECO-001 spec | ✅ Updated | kitty-specs/eco-001-worktree-remediation/spec.md |
| ECO-002 spec | ✅ Updated | kitty-specs/eco-002-branch-consolidation/spec.md |
| ECO-003 spec | ✅ Updated | kitty-specs/eco-003-circular-dep-resolution/spec.md |
| ECO-004 spec | ✅ Updated | kitty-specs/eco-004-hexagonal-migration/spec.md |

### Key Findings

- **AgilePlus is ALREADY hexagonal compliant** per ADR-002
- **45 stale branches deleted** from thegent
- **9 legacy worktrees archived** to `archive/legacy-wtrees/2026-03-28/`
- **230 PRs analyzed** with categorization for merge/rebase/close

### Full Audit Report

**Reference:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/docs/governance/ECOSYSTEM_AUDIT_COMPLETION_SUMMARY.md`

---

## Strategic Initiatives

### G037 — Plane Fork / Shared PM Substrate

**Decision:** Fork Plane (plane.so, Apache 2.0) as the shared PM substrate. Keep AgilePlus as the custom orchestration/control-plane layer. Keep TracerTM custom.

**Spec:** `.agileplus/specs/008-plane-shared-pm-substrate/`
**Session:** `docs/sessions/20260327-plane-fork-pm-substrate/`

| WP | Description | Status |
|----|-------------|--------|
| G037-WP1 | Fork Plane repo into org GitHub | pending (gate: org approval + GitHub admin) |
| G037-WP2 | Define AgilePlus → Plane API boundary adapter | pending |
| G037-WP3 | Migrate or quarantine duplicate PM dashboard code | pending |
| G037-WP4 | Wire existing controls into Plane | pending |
| G037-WP5 | Validate co-existence with Plane | pending |
| G037-WP6 | Archive TracerTM and TheGent from PM surface | pending |

### Open Work Ledger

**Session:** `docs/sessions/20260327-open-work-ledger/`

Prioritized cross-repo backlog covering AgilePlus, portage, heliosApp, and heliosCLI. See session for full DAG/WBS.

---

## AgilePlus Tracking

All feature work is tracked in AgilePlus:
- Reference: /Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus
- CLI: agileplus (run from AgilePlus directory)

## Quick Commands

```bash
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus

# List all features
agileplus list

# Show feature details
agileplus show <feature-id>

# Update work package status
agileplus status <feature-id> --wp <wp-id> --state <state>
```

## Current Work

See AgilePlus database for current work status:
- /Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus/.agileplus/agileplus.db

## Work History

Historical work is documented in:
- AgilePlus worklog: /Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus/.work-audit/worklog.md
- Git history for merged work


## Governance Implementation - 2026-03-29

### Implementation Completed

| Component | Status | Location |
|-----------|--------|----------|
| worktree_governance_inventory.py | ✅ Implemented | thegent/scripts/ |
| worktree_legacy_remediation_report.py | ✅ Implemented | thegent/scripts/ |
| worktree_governance.sh | ✅ Implemented | thegent/scripts/ |
| cli_git_worktree_governance.py | ✅ Implemented | thegent/src/thegent/cli/commands/ |
| MCP server worktree export | ✅ Implemented | thegent/src/thegent/mcp/ |

### Governance Tests
- Unit tests: 10/10 passing
- Location: thegent/tests/unit/governance/

### Non-Canonical Cleanup
- Removed orphaned phenotype-gauge-wtrees/ directory
- Stashed WIP in thegent-wtrees/rebase-fix-cache-test-pyright
- All legacy worktrees archived to archive/legacy-wtrees/2026-03-28/

### AgilePlus Specs Updated
- kitty-specs/eco-001-worktree-remediation/spec.md → completed
- kitty-specs/eco-002-branch-consolidation/spec.md → completed

### Remaining Non-Conformant Worktrees (by design)
- thegent-wtrees/rebase-fix-cache-test-pyright (fix/cache-test-pyright)
- thegent-wtrees/rescued-detached-head (feat/rescued-detached-head-work)

---

## Polyrepo Ecosystem Audit — 2026-04-02

### Audit Scope
- **GitHub repos**: 247 total under <REDACTED>
- **Local repos**: 9 cloned, 89 GB disk usage
- **AgilePlus specs**: 35 in kitty-specs/
- **Agents used**: 4 parallel worker agents for comprehensive audit

### Key Findings

#### Repo Classification
| Cluster | Count | Priority | Status |
|---------|-------|----------|--------|
| Core Platform | 13 | P0 | Active development |
| Agent Orchestration | 8 | P0 | Active development |
| SDK & DevTools | 16 | P1 | Needs consolidation |
| Templates & Kits | 7 | P2 | Needs deduplication |
| Peripheral/Archive | 23+ | P3 | Archive candidates |
| Learning/Personal | 6+ | P3 | Move to separate org |

#### Local State Issues
- **Dirty repos**: 7 of 9 have uncommitted changes
- **Open PRs**: 15+ across cloned repos (10 in infrakit, 5 in thegent)
- **Build artifacts**: 22 GB (77% of disk usage)
- **Stale branches**: 50+ without PRs
- **Empty worktrees**: 3 directories (docs/, infrastructure/, phenotype-errors/)
- **Off-main repos**: thegent, heliosApp, heliosCLI not on main

#### AgilePlus Spec Status
- **Complete**: 3 specs (001, 002, 003)
- **Partial**: 8 specs (need plans, tasks, or research)
- **Spec only**: 15 specs (need full artifact structure)
- **New**: 1 spec created (021-polyrepo-ecosystem-stabilization)

### Actions Taken

| Action | Status | Details |
|--------|--------|---------|
| Created spec 021 | ✅ | Full stabilization plan with 20 WPs |
| Created tasks.md for spec 021 | ✅ | 4 phases, 48 tasks |
| Created plan.md for spec 021 | ✅ | Dependency graph, checkpoints |
| Created research.md for spec 021 | ✅ | Audit methodology, findings |
| Created STRATEGY.md | ✅ | docs/stabilization/STRATEGY.md |
| Identified merge candidates | ✅ | 15 repos → 8 targets |
| Identified archive candidates | ✅ | 28 repos for archival |
| Documented disk optimization | ✅ | 89 GB → 20 GB target |

### Next Steps

1. **Phase 1 (Days 1-7)**: Commit dirty files, merge PRs, clean artifacts, set up org CI
2. **Phase 2 (Weeks 2-3)**: Merge duplicates, archive stale, set up package publishing
3. **Phase 3 (Weeks 4-6)**: SDK monorepo, docs federation, health checks
4. **Phase 4 (Weeks 7-12)**: Full CI/CD, governance compliance, performance benchmarks

### References
- Strategy: `docs/stabilization/STRATEGY.md`
- Spec 021: `kitty-specs/021-polyrepo-ecosystem-stabilization/`
- Audit reports: Session documentation from 2026-04-02


## Cross-Repo Health Dashboard 2026-05-02
Summary:
Total repos: 475  
Repos CI: 367  
Repos LICENSE: 337  
Repos README: 372  
Repos uncommitted changes: 147  

| Repo | Lang | License | README | Workflows | Last Commit | Dirty | Branches |
|------|------|---------|--------|-----------|------------|-------|----------|
| agent-devops-setups | JS/TS | yes | yes | 11 | 2026-05-03 00:58:55 -0700 | 0 | 6 |
| agent-devops-setups | Unknown | yes | yes | 15 | 2026-04-27 23:26:49 -0700 | 11 | 3 |
| agent-devops-setups-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| agent-user-status | Python | yes | yes | 6 | 2026-05-03 00:00:45 -0700 | 0 | 9 |
| agent-wave-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| agentapi-plusplus | Go | yes | yes | 29 | 2026-05-03 00:00:44 -0700 | 0 | 29 |
| agentapi-plusplus-docs | Go, JS/TS | yes | yes | 22 | 2026-04-02 15:17:17 -0700 | 11 | 29 |
| AgentMCP | Unknown | yes | yes | 3 | 2026-05-02 22:27:48 -0700 | 0 | 11 |
| agentops-policy-federation-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Agentora | Rust | yes | yes | 5 | 2026-05-03 08:24:28 -0700 | 0 | 2 |
| agile-main | Rust | yes | yes | 37 | 2026-05-03 07:57:51 -0700 | 2 | 111 |
| AgilePlus | Unknown | no | no | 1 | 2026-05-03 07:57:51 -0700 | 0 | 111 |
| AgilePlus-fmt-sweep-20260501-merged | Unknown | no | no | 0 | n/a | 0 | 0 |
| agileplus-landing | JS/TS | yes | yes | 2 | 2026-05-03 04:10:38 -0700 | 0 | 6 |
| agileplus-plugin-core-clippyfix | Unknown | no | no | 0 | n/a | 0 | 0 |
| agileplus-plugin-core-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| agileplus-plugin-git-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| agileplus-plugin-sqlite-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| AgilePlus-security-alerts-20260426-20260501-merged | Unknown | no | no | 0 | n/a | 0 | 0 |
| agslag-docs-ghost-2026-05-02 | Unknown | yes | yes | 3 | 2026-05-02 09:51:44 -0700 | 2 | 8 |
| Apisync-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| AppGen | JS/TS | no | yes | 4 | 2026-05-04 03:24:36 -0700 | 0 | 4 |
| argis-extensions | Go | yes | yes | 11 | 2026-05-03 13:32:34 -0700 | 0 | 11 |
| astro-build-fix-20260430 | JS/TS | yes | yes | 2 | 2026-05-04 01:40:24 -0700 | 0 | 6 |
| atoms.tech-ghost-2026-05-02 | JS/TS | yes | yes | 6 | 2026-05-02 13:43:37 -0700 | 12 | 4 |
| AtomsBot | JS/TS | yes | yes | 8 | 2026-05-03 06:47:10 -0700 | 0 | 10 |
| AuthKit | Python | yes | yes | 10 | 2026-05-03 06:13:08 -0700 | 0 | 25 |
| Authvault-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| bare-cua | Rust | yes | yes | 12 | 2026-05-03 08:26:50 -0700 | 0 | 10 |
| bare-cua-docs | JS/TS, Rust | no | yes | 6 | 2026-04-02 15:43:30 -0700 | 1 | 10 |
| bbox-ground-d6 | Rust | yes | yes | 6 | 2026-04-23 06:09:46 -0700 | 8 | 29 |
| Benchora | Rust | yes | yes | 6 | 2026-05-04 03:24:36 -0700 | 0 | 1 |
| bifrost-extensions-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| build-fix | Go, JS/TS | yes | yes | 26 | 2026-04-25 11:07:59 -0700 | 2 | 20 |
| build-fix-2 | Go, JS/TS | yes | yes | 26 | 2026-04-25 11:35:40 -0700 | 2 | 20 |
| build-fix-3 | Go, JS/TS | yes | yes | 26 | 2026-04-25 12:23:26 -0700 | 2 | 20 |
| bump-happy-dom-v20 | JS/TS | yes | yes | 8 | 2026-05-02 13:15:59 -0700 | 26 | 10 |
| bun-unblock | JS/TS | yes | yes | 8 | 2026-05-02 05:39:30 -0700 | 0 | 10 |
| BytePort | Go, Rust | yes | yes | 14 | 2026-05-03 09:20:48 -0700 | 0 | 21 |
| BytePort-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| byteport-landing | JS/TS | yes | yes | 2 | 2026-05-02 23:24:52 -0700 | 0 | 6 |
| canonical-import | Unknown | no | no | 3 | 2026-04-25 17:45:44 -0700 | 0 | 11 |
| canonical-import-health | Rust | yes | yes | 10 | 2026-04-25 17:56:22 -0700 | 4 | 29 |
| canvasApp | Python | no | yes | 2 | 2026-04-25 01:22:06 -0700 | 0 | 3 |
| cargo-deny-full-rollout-2026-04-27 | Rust | yes | yes | 36 | 2026-05-02 06:10:15 -0700 | 2 | 111 |
| cargo-update-2026-04-27 | JS/TS, Rust | yes | yes | 7 | 2026-04-26 21:35:32 -0700 | 0 | 17 |
| chatta | JS/TS | yes | yes | 10 | 2026-05-03 13:32:34 -0700 | 0 | 16 |
| cheap-llm-mcp | Python | yes | yes | 9 | 2026-05-02 22:11:46 -0700 | 0 | 5 |
| ci-cleanup-20260427 | Rust | yes | yes | 8 | 2026-04-27 03:49:43 -0700 | 4 | 25 |
| ci-wire | Rust | yes | yes | 2 | 2026-04-23 21:46:38 -0700 | 0 | 20 |
| Civis | JS/TS, Rust | yes | yes | 25 | 2026-05-03 13:32:34 -0700 | 0 | 21 |
| cliproxyapi-plusplus | Go, JS/TS | yes | yes | 28 | 2026-05-03 06:13:09 -0700 | 0 | 20 |
| cliproxyapi-plusplus-docs | Go, JS/TS | yes | yes | 27 | 2026-04-02 15:45:07 -0700 | 2 | 20 |
| cloud-docs | JS/TS | yes | yes | 15 | n/a | 0 | 0 |
| cloud-ghost-2026-05-02 | JS/TS | yes | yes | 11 | 2026-05-02 13:34:29 -0700 | 2 | 10 |
| cmdra | Unknown | no | no | 0 | n/a | 0 | 0 |
| Cmdra-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| codeql-apilink-ssrf | Go, Rust | yes | yes | 7 | 2026-04-26 10:40:55 -0700 | 0 | 21 |
| codex-pr12-followup | Rust | yes | yes | 7 | 2026-04-27 00:44:23 -0700 | 0 | 14 |
| codex-rs-unblock | JS/TS, Rust | yes | yes | 28 | 2026-04-25 11:11:16 -0700 | 2 | 14 |
| colab | JS/TS, Rust | no | yes | 12 | 2026-04-24 16:54:55 -0700 | 2 | 3 |
| commit-lockfile | Rust | yes | yes | 8 | 2026-04-25 10:45:49 -0700 | 3 | 25 |
| commit-lockfile | Unknown | yes | yes | 8 | 2026-04-25 12:25:30 -0700 | 0 | 13 |
| commit-lockfile | Rust | yes | yes | 10 | 2026-04-25 11:35:07 -0700 | 3 | 29 |
| commit-lockfile | Unknown | yes | yes | 6 | 2026-04-25 11:35:02 -0700 | 0 | 21 |
| commit-lockfile | Rust | yes | yes | 41 | 2026-05-01 08:28:03 -0700 | 4 | 6 |
| Configra | Rust | yes | yes | 19 | 2026-05-03 08:26:50 -0700 | 0 | 4 |
| Conft | Unknown | yes | yes | 7 | 2026-05-02 13:41:48 -0700 | 0 | 7 |
| container-base-bump | Rust | yes | yes | 44 | 2026-05-01 08:28:39 -0700 | 5 | 23 |
| container-base-bump | Rust | yes | yes | 36 | 2026-04-30 04:29:49 -0700 | 12 | 111 |
| cursora | Unknown | no | no | 0 | n/a | 0 | 0 |
| Cursora-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| cve-cross-bump | Rust | yes | yes | 39 | 2026-05-01 08:28:40 -0700 | 3 | 23 |
| cve-cross-bump | Rust | yes | yes | 36 | 2026-05-02 21:47:43 -0700 | 73 | 111 |
| cve-sweep | Rust | yes | yes | 41 | 2026-05-01 08:28:03 -0700 | 3 | 6 |
| cve-sweep-high | Unknown | no | no | 0 | n/a | 0 | 0 |
| cve-sweep-high | Unknown | yes | yes | 6 | 2026-04-25 11:35:53 -0700 | 0 | 21 |
| cve-sweep-residual | Rust | yes | yes | 29 | 2026-04-25 12:23:14 -0700 | 10 | 111 |
| cve-sweep-rsa | Rust | yes | yes | 10 | 2026-04-25 12:23:23 -0700 | 1 | 29 |
| DataKit | Unknown | yes | yes | 9 | 2026-05-04 03:34:10 -0700 | 0 | 10 |
| datakit-phenoshared-migrate | Unknown | yes | yes | 5 | 2026-04-25 18:19:15 -0700 | 0 | 10 |
| Datamold-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| deny-fix | Unknown | no | yes | 5 | 2026-05-02 01:41:18 -0700 | 1 | 1 |
| deny-fix | Unknown | yes | yes | 1 | 2026-05-01 20:51:43 -0700 | 0 | 1 |
| dep-high | Rust | yes | yes | 24 | 2026-04-23 21:09:02 -0700 | 17 | 111 |
| dep-nkeys | JS/TS, Rust | yes | yes | 4 | 2026-04-23 20:48:17 -0700 | 181 | 25 |
| dep-pyjwt-lodash | Rust | yes | yes | 24 | 2026-04-23 21:16:27 -0700 | 21 | 111 |
| dependabot-a8883763 | Unknown | yes | yes | 3 | 2026-05-02 06:45:38 -0700 | 0 | 11 |
| dependabot-a8883763 | Unknown | yes | yes | 8 | 2026-05-02 06:45:41 -0700 | 0 | 7 |
| deprecate-phase1-copies | Rust | yes | yes | 40 | 2026-05-01 08:28:40 -0700 | 3 | 23 |
| devenv-abstraction-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| DevHex | Go | yes | yes | 1 | 2026-05-03 01:13:24 -0700 | 0 | 7 |
| DevHex | Go | no | yes | 0 | 2026-04-24 16:54:55 -0700 | 0 | 1 |
| Dino | Unknown | yes | yes | 2 | 2026-05-03 04:10:41 -0700 | 0 | 7 |
| Dino-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| dinoforge-packs | Unknown | yes | yes | 7 | 2026-05-02 14:10:29 -0700 | 0 | 10 |
| DINOForge-UnityDoorstop | Unknown | yes | yes | 3 | 2026-05-03 04:10:38 -0700 | 0 | 8 |
| docs-build-timeouts | Rust | yes | yes | 11 | 2026-04-30 11:02:10 -0700 | 1 | 29 |
| docs-deploy-cleanup | Rust | yes | yes | 41 | 2026-05-01 08:28:03 -0700 | 3 | 7 |
| docuverse | Unknown | no | no | 0 | n/a | 0 | 0 |
| Docuverse-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| dup-route-fix | Rust | yes | yes | 29 | 2026-04-25 15:11:47 -0700 | 10 | 111 |
| Eidolon | Rust | yes | yes | 11 | 2026-05-03 04:10:41 -0700 | 0 | 6 |
| eval-suite | Python | yes | yes | 29 | 2026-05-03 13:47:07 -0700 | 1 | 13 |
| Evalora | Rust | yes | yes | 10 | 2026-04-28 19:35:07 -0700 | 2 | 1 |
| eyetracker | Rust | yes | yes | 9 | 2026-05-03 13:32:34 -0700 | 0 | 7 |
| fix-hooks-canonical | Rust | yes | yes | 29 | 2026-04-25 15:07:49 -0700 | 9 | 111 |
| fix-landing-ui | JS/TS | yes | yes | 1 | 2026-05-01 20:02:04 -0700 | 0 | 6 |
| fix-sqlx | Rust | yes | yes | 15 | 2026-05-02 15:33:54 -0700 | 3 | 1 |
| FixitRs | Unknown | no | yes | 1 | 2026-04-24 16:54:55 -0700 | 0 | 2 |
| flowra | Rust | no | no | 0 | 2026-05-01 18:32:38 -0700 | 0 | 1 |
| FocalPoint | Rust | yes | yes | 5 | 2026-05-03 08:20:31 -0700 | 0 | 7 |
| foqos-private | Unknown | yes | yes | 8 | 2026-05-03 00:52:46 -0700 | 0 | 4 |
| forgecode | JS/TS, Rust | yes | yes | 9 | 2026-05-03 09:20:50 -0700 | 1 | 8 |
| GDK | Rust | yes | yes | 15 | 2026-05-03 08:35:30 -0700 | 0 | 11 |
| GDK | Rust | no | yes | 1 | 2026-04-24 16:54:56 -0700 | 0 | 3 |
| generated-temp-spec | JS/TS, Python | yes | yes | 13 | 2026-04-27 00:37:11 -0700 | 0 | 12 |
| generated-temp-untrack | JS/TS, Python | yes | yes | 13 | 2026-04-26 21:54:27 -0700 | 0 | 12 |
| ghp-publish | Rust | yes | yes | 1 | 2026-04-23 21:22:03 -0700 | 0 | 20 |
| go | Go | no | no | 1 | 2026-05-03 00:50:43 -0700 | 0 | 1 |
| go-nippon | Unknown | no | yes | 1 | 2026-04-24 16:54:56 -0700 | 0 | 2 |
| gov-bootstrap | Unknown | yes | yes | 2 | 2026-05-02 05:12:55 -0700 | 0 | 2 |
| gui-recorder-rehydrate | Rust | yes | yes | 11 | 2026-04-30 05:28:13 -0700 | 1 | 29 |
| helios-cli | JS/TS, Rust | yes | yes | 36 | 2026-05-03 13:32:34 -0700 | 1 | 15 |
| helios-router | Python, Rust | yes | yes | 15 | 2026-05-03 13:32:34 -0700 | 1 | 10 |
| heliosApp | JS/TS | yes | yes | 27 | 2026-05-03 13:32:35 -0700 | 0 | 32 |
| heliosapp-pr362-clean | JS/TS | yes | yes | 22 | 2026-04-05 20:02:18 -0700 | 4 | 31 |
| heliosBench | JS/TS, Python | yes | yes | 5 | 2026-05-02 13:51:13 -0700 | 0 | 10 |
| helioscli-pr179-policy-fix | Unknown | no | no | 0 | n/a | 0 | 0 |
| helioscope | JS/TS, Python, Rust | yes | yes | 51 | 2026-05-03 08:26:50 -0700 | 0 | 21 |
| HeliosLab | JS/TS, Rust | yes | yes | 18 | 2026-05-03 09:26:44 -0700 | 0 | 21 |
| hexago | Unknown | no | no | 0 | n/a | 0 | 0 |
| hexagon-ts-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| HexaKit | Rust | yes | yes | 51 | 2026-05-03 08:20:15 -0700 | 0 | 13 |
| HexaPy-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| HexaType-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Httpora | Python | yes | yes | 7 | 2026-05-02 23:24:58 -0700 | 0 | 10 |
| Httpora-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| hwLedger | Unknown | yes | yes | 6 | 2026-05-04 03:24:36 -0700 | 0 | 29 |
| hwledger-landing | JS/TS | yes | yes | 4 | 2026-05-02 23:26:23 -0700 | 0 | 5 |
| hygiene-refactor | Go, Rust | yes | yes | 10 | 2026-04-30 11:12:59 -0700 | 37 | 21 |
| iac-integration | Unknown | yes | yes | 9 | 2026-04-25 14:15:50 -0700 | 0 | 13 |
| journey-fix | Go, JS/TS | yes | yes | 27 | 2026-05-01 18:45:55 -0700 | 0 | 20 |
| journey-impl | Go | yes | yes | 6 | 2026-05-01 20:38:41 -0700 | 0 | 7 |
| journey-impl | Unknown | yes | yes | 7 | 2026-05-01 20:40:37 -0700 | 0 | 14 |
| journey-impl | JS/TS | yes | yes | 6 | 2026-05-01 20:40:03 -0700 | 0 | 5 |
| journey-impl | Go | yes | yes | 7 | 2026-05-01 20:45:35 -0700 | 0 | 9 |
| journey-impl | Unknown | yes | yes | 4 | 2026-05-01 20:40:01 -0700 | 0 | 12 |
| journey-impl | Unknown | yes | yes | 7 | 2026-05-01 20:39:00 -0700 | 0 | 4 |
| journey-impl | JS/TS | yes | yes | 1 | 2026-05-01 20:43:44 -0700 | 0 | 6 |
| journey-impl | JS/TS | yes | yes | 3 | 2026-05-01 20:45:33 -0700 | 0 | 8 |
| journey-impl | Go, JS/TS | no | yes | 9 | 2026-05-01 20:39:51 -0700 | 0 | 7 |
| journey-impl | Unknown | yes | yes | 10 | 2026-05-01 20:45:41 -0700 | 3 | 13 |
| journey-impl | Unknown | no | yes | 5 | 2026-05-01 20:39:24 -0700 | 1 | 29 |
| journey-impl | Rust | yes | yes | 47 | 2026-05-02 01:52:12 -0700 | 4 | 23 |
| journey-impl | Unknown | yes | yes | 5 | 2026-05-01 20:45:31 -0700 | 0 | 7 |
| journey-impl | Unknown | yes | yes | 11 | 2026-05-01 20:43:23 -0700 | 1 | 7 |
| journey-impl | Rust | yes | yes | 18 | 2026-05-01 20:38:33 -0700 | 3 | 4 |
| journey-impl | Unknown | no | yes | 1 | 2026-05-01 20:40:21 -0700 | 0 | 5 |
| journey-impl | Rust | yes | yes | 12 | 2026-05-01 20:45:20 -0700 | 1 | 8 |
| journey-impl | Python | yes | yes | 7 | 2026-05-01 08:53:37 -0700 | 0 | 5 |
| journey-impl | Unknown | no | no | 0 | n/a | 0 | 0 |
| journey-impl | Rust | yes | yes | 11 | 2026-05-01 18:58:54 -0700 | 1 | 8 |
| journey-impl | Unknown | no | yes | 7 | 2026-05-01 18:44:40 -0700 | 0 | 11 |
| journey-impl | JS/TS | no | yes | 3 | 2026-05-01 20:45:28 -0700 | 0 | 6 |
| journey-impl | JS/TS, Python | yes | yes | 8 | 2026-05-02 01:52:23 -0700 | 1 | 7 |
| journey-impl | JS/TS | yes | yes | 26 | 2026-05-01 20:39:15 -0700 | 0 | 31 |
| journey-impl | JS/TS, Python | yes | yes | 3 | 2026-05-01 18:40:13 -0700 | 4 | 10 |
| journey-impl | JS/TS | yes | yes | 3 | 2026-05-01 20:40:12 -0700 | 0 | 3 |
| journey-impl | Rust | yes | yes | 10 | 2026-04-30 15:36:41 -0700 | 2 | 8 |
| journey-impl | JS/TS, Python | yes | yes | 9 | 2026-05-01 20:40:07 -0700 | 0 | 11 |
| journey-impl | Python | yes | yes | 18 | 2026-05-01 20:40:32 -0700 | 0 | 12 |
| journey-impl | JS/TS, Rust | yes | yes | 13 | 2026-05-01 20:45:22 -0700 | 1 | 10 |
| journey-impl | JS/TS, Rust | yes | yes | 14 | 2026-05-01 20:39:33 -0700 | 1 | 17 |
| journey-impl | JS/TS | yes | yes | 3 | 2026-05-01 20:39:28 -0700 | 0 | 5 |
| journey-impl | JS/TS | yes | yes | 5 | 2026-05-01 20:45:02 -0700 | 0 | 7 |
| journey-impl | JS/TS, Python | yes | yes | 13 | 2026-05-01 20:45:00 -0700 | 0 | 12 |
| journey-impl | Rust | yes | yes | 7 | 2026-05-01 20:39:37 -0700 | 0 | 10 |
| journey-impl | JS/TS | yes | yes | 3 | 2026-05-02 01:52:30 -0700 | 0 | 6 |
| journey-impl | Unknown | no | yes | 8 | 2026-05-01 20:43:28 -0700 | 0 | 7 |
| journey-impl | JS/TS | yes | yes | 10 | 2026-05-01 20:45:24 -0700 | 1 | 13 |
| journey-impl | Unknown | yes | yes | 6 | 2026-05-01 20:38:49 -0700 | 0 | 10 |
| journey-impl | Python | yes | yes | 29 | 2026-05-02 05:50:01 -0700 | 1 | 13 |
| journey-impl | JS/TS | yes | yes | 8 | 2026-05-01 20:38:23 -0700 | 0 | 15 |
| journey-impl | JS/TS | yes | yes | 8 | 2026-05-01 20:37:44 -0700 | 0 | 10 |
| journey-impl | Go, JS/TS | yes | yes | 6 | 2026-05-02 01:52:18 -0700 | 0 | 5 |
| journey-impl | Unknown | yes | yes | 1 | 2026-05-01 20:45:26 -0700 | 0 | 8 |
| journey-impl | Rust | yes | yes | 11 | 2026-05-01 20:25:16 -0700 | 1 | 20 |
| journey-impl | Python | yes | yes | 4 | 2026-05-01 20:39:47 -0700 | 0 | 15 |
| journey-impl | Rust | yes | yes | 8 | 2026-05-01 20:40:23 -0700 | 1 | 4 |
| journey-impl | Rust | yes | yes | 11 | 2026-05-01 20:40:42 -0700 | 1 | 11 |
| journey-impl | Go, Rust | yes | yes | 13 | 2026-05-01 20:38:09 -0700 | 0 | 21 |
| journey-impl | Rust | yes | yes | 7 | 2026-04-30 14:50:28 -0700 | 1 | 6 |
| journey-impl | Unknown | yes | yes | 6 | 2026-05-01 20:38:37 -0700 | 0 | 7 |
| journey-impl | Rust | yes | yes | 9 | 2026-05-01 20:45:30 -0700 | 1 | 7 |
| journey-impl | Go | yes | yes | 4 | 2026-05-01 00:11:30 -0700 | 0 | 10 |
| journey-impl | Go | yes | yes | 8 | 2026-05-01 20:39:43 -0700 | 0 | 9 |
| journey-impl | JS/TS, Rust | yes | yes | 25 | 2026-05-02 02:15:08 -0700 | 1 | 20 |
| journey-impl | Rust | yes | yes | 14 | 2026-05-01 20:39:10 -0700 | 0 | 11 |
| journey-impl | JS/TS, Rust | yes | yes | 12 | 2026-05-01 20:45:34 -0700 | 1 | 14 |
| journey-impl | JS/TS, Python | yes | yes | 18 | 2026-05-01 20:45:04 -0700 | 1 | 12 |
| journey-impl | Python | yes | yes | 2 | 2026-05-01 20:45:39 -0700 | 0 | 6 |
| journey-impl | Rust | yes | yes | 37 | 2026-05-02 13:25:14 -0700 | 1 | 2 |
| journey-impl | JS/TS | yes | yes | 1 | 2026-05-01 20:38:14 -0700 | 0 | 6 |
| journey-impl | Rust | yes | yes | 12 | 2026-05-01 20:40:46 -0700 | 3 | 13 |
| journey-impl | Python | no | yes | 4 | 2026-04-30 14:17:20 -0700 | 0 | 9 |
| journey-impl | Rust | yes | yes | 10 | 2026-05-01 20:38:55 -0700 | 1 | 6 |
| journey-impl | Unknown | yes | yes | 6 | 2026-05-01 20:40:13 -0700 | 0 | 12 |
| KaskMan | JS/TS | yes | yes | 4 | 2026-04-24 16:54:56 -0700 | 0 | 1 |
| KDesktopVirt | JS/TS, Rust | yes | yes | 14 | 2026-05-03 13:32:35 -0700 | 0 | 17 |
| kdesktopvirt-sladge-badge | JS/TS, Rust | yes | yes | 7 | 2026-04-29 07:35:46 -0700 | 0 | 17 |
| KlipDot | Rust | yes | yes | 8 | 2026-05-03 00:00:46 -0700 | 0 | 10 |
| kmobile-20260502-archived | Rust | yes | yes | 3 | 2026-05-02 15:18:46 -0700 | 3 | 9 |
| KodeVibeGo-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Kogito-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| koosha-portfolio | Unknown | no | no | 0 | 2026-05-04 03:40:29 -0700 | 2 | 145 |
| kwality | Go | yes | yes | 7 | 2026-05-03 07:29:31 -0700 | 0 | 5 |
| license-changelog | Python | yes | yes | 1 | 2026-04-27 01:22:00 -0700 | 1 | 10 |
| license-year | JS/TS, Rust | yes | yes | 7 | 2026-04-30 03:02:12 -0700 | 1 | 17 |
| license-year | JS/TS | yes | yes | 8 | 2026-04-27 18:22:39 -0700 | 1 | 13 |
| localbase3 | Unknown | no | yes | 2 | 2026-05-04 03:24:36 -0700 | 0 | 11 |
| lockfile-regen-2026-04-27 | Unknown | no | no | 0 | n/a | 0 | 0 |
| lockfile-regen-2026-04-27 | JS/TS, Python | yes | yes | 37 | 2026-04-27 00:37:55 -0700 | 0 | 2 |
| lockfile-regen-2026-04-27 | Rust | yes | yes | 41 | 2026-05-01 08:28:03 -0700 | 3 | 6 |
| lockfile-retry | Rust | yes | yes | 8 | 2026-04-25 11:54:58 -0700 | 3 | 25 |
| lockfile-retry | Rust | yes | yes | 10 | 2026-04-25 11:54:55 -0700 | 2 | 29 |
| lockfile-update | Unknown | no | no | 0 | n/a | 0 | 0 |
| lockfile-update | Python | yes | yes | 17 | 2026-04-28 18:54:33 -0700 | 1 | 12 |
| lockfile-update | Go, Rust | yes | yes | 11 | 2026-04-27 23:13:50 -0700 | 1 | 21 |
| lockfile-update | Go | yes | yes | 26 | 2026-04-29 02:53:05 -0700 | 2 | 29 |
| lockfile-update | Unknown | no | yes | 6 | 2026-04-27 02:40:44 -0700 | 0 | 12 |
| Logify | Unknown | no | no | 0 | n/a | 0 | 0 |
| Logify-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| main-ci-followup-20260427 | Rust | yes | yes | 26 | 2026-04-27 03:35:08 -0700 | 2 | 11 |
| main-clean-20260426 | Go | yes | yes | 27 | 2026-04-25 21:36:39 -0700 | 2 | 29 |
| manifest-fix-and-lockfile-2026-04-27 | Python | yes | yes | 18 | 2026-04-26 21:38:02 -0700 | 0 | 12 |
| MCPForge | Go | yes | yes | 9 | 2026-05-03 01:02:49 -0700 | 0 | 9 |
| McpKit | Python | yes | yes | 5 | 2026-05-04 03:34:16 -0700 | 0 | 15 |
| Metron | Rust | yes | yes | 13 | 2026-05-03 05:41:30 -0700 | 0 | 4 |
| Metron-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| msrv-fix | Unknown | no | no | 0 | n/a | 0 | 0 |
| nanovms | Go, JS/TS | yes | yes | 10 | 2026-05-02 13:39:37 -0700 | 0 | 7 |
| netweave-final2 | Go | yes | yes | 5 | 2026-05-03 06:47:11 -0700 | 0 | 10 |
| npm-sweep | Unknown | no | no | 0 | n/a | 0 | 0 |
| nvms-parser-cleanup | Go, Rust | yes | yes | 10 | 2026-04-27 18:56:11 -0700 | 7 | 21 |
| ObservabilityKit | Unknown | yes | yes | 9 | 2026-05-03 06:13:14 -0700 | 0 | 7 |
| omniroute-fixes | Rust | yes | yes | 11 | 2026-04-30 13:39:10 -0700 | 4 | 25 |
| omniroute-temp-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| org-github-docs | JS/TS | no | yes | 9 | n/a | 0 | 0 |
| org-github-ghost-2026-05-02 | Unknown | no | yes | 8 | 2026-04-02 10:27:28 -0700 | 9 | 6 |
| p1-test-fixes-2026-04-27-merged-ghost | Unknown | no | no | 0 | n/a | 0 | 0 |
| Paginary | JS/TS | yes | yes | 7 | 2026-05-03 00:58:27 -0700 | 0 | 5 |
| Parpoura | JS/TS, Python | yes | yes | 13 | 2026-05-03 04:10:35 -0700 | 0 | 11 |
| pathsafe | Go, JS/TS | yes | yes | 26 | 2026-04-25 10:56:43 -0700 | 2 | 20 |
| pgai | Unknown | yes | yes | 7 | 2026-04-24 16:54:57 -0700 | 0 | 1 |
| phench-ghost-2026-05-02 | Python | yes | yes | 13 | 2026-05-02 14:51:43 -0700 | 53 | 1 |
| pheno | Rust | yes | yes | 48 | 2026-05-03 08:25:05 -0700 | 0 | 23 |
| pheno | Rust | no | yes | 2 | 2026-04-24 16:54:56 -0700 | 0 | 5 |
| pheno-xdd | Unknown | yes | yes | 7 | 2026-04-04 03:47:22 -0700 | 5 | 3 |
| pheno-xdd-lib | Rust | yes | yes | 10 | 2026-04-04 03:47:22 -0700 | 11 | 4 |
| PhenoAgent | Unknown | yes | yes | 8 | 2026-05-04 03:33:58 -0700 | 0 | 10 |
| phenoAI | Rust | yes | yes | 13 | 2026-05-03 08:26:51 -0700 | 0 | 8 |
| PhenoCompose | Go, JS/TS | yes | yes | 7 | 2026-05-04 03:24:36 -0700 | 0 | 5 |
| phenoData | JS/TS, Rust | yes | yes | 14 | 2026-05-03 08:26:51 -0700 | 0 | 10 |
| phenoDesign | JS/TS | yes | yes | 11 | 2026-05-03 04:10:40 -0700 | 0 | 13 |
| PhenoDevOps | Go, Rust | yes | yes | 41 | 2026-05-03 14:04:55 -0700 | 0 | 14 |
| phenodocs | JS/TS, Python | yes | yes | 14 | 2026-05-03 04:10:35 -0700 | 0 | 12 |
| phenodocs | JS/TS, Python | yes | yes | 9 | 2026-04-24 16:54:56 -0700 | 0 | 1 |
| phenodocs-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenodocs-scorecard-remediation | JS/TS, Python | yes | yes | 14 | 2026-05-03 01:00:47 -0700 | 5 | 12 |
| phenoEvaluation | JS/TS, Python | yes | yes | 9 | 2026-04-24 16:54:56 -0700 | 2 | 1 |
| phenoForge | Rust | yes | yes | 9 | 2026-05-03 08:26:51 -0700 | 0 | 1 |
| PhenoHandbook | JS/TS | yes | yes | 6 | 2026-05-03 04:10:40 -0700 | 0 | 8 |
| PhenoKits | Rust | yes | yes | 13 | 2026-05-03 08:26:51 -0700 | 0 | 25 |
| PhenoKits-fix-dependabot | Rust | yes | yes | 8 | 2026-04-25 11:54:29 -0700 | 3 | 25 |
| PhenoKits-forced-adoption-reality | Rust | yes | yes | 8 | 2026-04-25 18:15:52 -0700 | 3 | 25 |
| phenokits-landing | JS/TS | yes | yes | 4 | 2026-05-03 00:58:29 -0700 | 1 | 3 |
| PhenoKits-tracera-fr-scaffold | JS/TS, Rust | yes | yes | 4 | 2026-05-01 08:28:25 -0700 | 2666 | 25 |
| PhenoLang | Go | yes | yes | 5 | 2026-05-03 13:32:35 -0700 | 0 | 9 |
| PhenoLang-actual | JS/TS, Rust | yes | yes | 41 | 2026-04-24 16:54:56 -0700 | 3 | 2 |
| PhenoLibs | Unknown | no | yes | 3 | 2026-04-25 01:04:19 -0700 | 8 | 9 |
| PhenoMCP | Go, JS/TS, Python, Rust | yes | yes | 11 | 2026-05-04 03:18:47 -0700 | 0 | 12 |
| PhenoObservability | Rust | yes | yes | 17 | 2026-05-03 13:32:35 -0700 | 0 | 21 |
| PhenoPlugins | Rust | yes | yes | 13 | 2026-05-03 04:05:24 -0700 | 0 | 14 |
| PhenoProc | Rust | yes | yes | 14 | 2026-05-03 14:18:39 -0700 | 7 | 19 |
| PhenoProject | Unknown | yes | yes | 7 | 2026-05-04 03:24:37 -0700 | 0 | 12 |
| PhenoProject | Unknown | no | yes | 0 | 2026-04-24 16:54:57 -0700 | 0 | 2 |
| phenoResearchEngine | JS/TS, Python | yes | yes | 10 | 2026-05-03 13:32:36 -0700 | 0 | 8 |
| PhenoRuntime | Go, JS/TS, Python, Rust | yes | yes | 16 | 2026-05-03 04:10:36 -0700 | 0 | 9 |
| PhenoRuntime | Go, JS/TS, Python, Rust | no | yes | 1 | 2026-04-24 16:54:57 -0700 | 0 | 3 |
| phenoSDK-orphan-2026-04-26 | Unknown | no | yes | 48 | 2026-04-25 07:23:23 -0700 | 2200 | 5 |
| phenoShared | JS/TS, Rust | yes | yes | 18 | 2026-05-03 06:57:37 -0700 | 0 | 15 |
| PhenoSpecs | Unknown | yes | yes | 1 | 2026-05-03 00:00:46 -0700 | 0 | 12 |
| phenospecs-archive-purge | Unknown | yes | yes | 4 | 2026-04-25 18:22:26 -0700 | 0 | 12 |
| phenospecs-docs-research | Unknown | yes | yes | 4 | 2026-04-25 18:19:55 -0700 | 0 | 12 |
| phenospecs-platform-registry | Unknown | no | yes | 1 | 2026-04-25 18:17:53 -0700 | 0 | 12 |
| phenotype-agent-core-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-auth-ts | JS/TS | yes | yes | 8 | 2026-05-02 12:50:45 -0700 | 0 | 6 |
| phenotype-auth-ts-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-bus | Rust | yes | yes | 10 | 2026-05-03 04:10:40 -0700 | 0 | 7 |
| phenotype-cipher-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-cli-extensions-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-config | Rust | yes | yes | 17 | 2026-05-03 00:57:46 -0700 | 26 | 1 |
| phenotype-config-ts-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-dep-guard-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-design-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-docs-engine-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-evaluation-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-forge-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-gauge-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-go-kit-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-hub | Unknown | yes | yes | 7 | 2026-05-03 04:10:39 -0700 | 0 | 7 |
| phenotype-hub-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-infra | Unknown | yes | yes | 11 | 2026-05-03 13:32:36 -0700 | 0 | 14 |
| phenotype-infra-oci-hooks | Unknown | yes | yes | 8 | 2026-04-25 07:02:07 -0700 | 0 | 13 |
| phenotype-journeys | Rust | yes | yes | 16 | 2026-05-04 03:18:54 -0700 | 0 | 20 |
| phenotype-logging-zig-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-middleware-py-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-nexus-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-omlx | Python | yes | yes | 3 | 2026-05-03 04:10:36 -0700 | 0 | 6 |
| phenotype-ops-mcp | Go | yes | yes | 8 | 2026-05-03 04:10:39 -0700 | 0 | 9 |
| phenotype-ops-mcp-fix-20260502-ghost | Go | yes | yes | 7 | 2026-05-02 04:39:45 -0700 | 2 | 5 |
| phenotype-org-audits | JS/TS | yes | yes | 5 | 2026-05-02 18:47:41 -0700 | 0 | 5 |
| phenotype-patch-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-registry | JS/TS | yes | yes | 4 | 2026-05-03 04:10:39 -0700 | 0 | 8 |
| phenotype-research-engine-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-sentinel-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-shared-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-skills-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-task-engine-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-templates-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-tooling | JS/TS, Rust | yes | yes | 13 | 2026-05-03 08:26:51 -0700 | 0 | 14 |
| phenotype-toolkit | Rust | yes | yes | 0 | 2026-04-05 02:02:55 -0700 | 0 | 1 |
| phenotype-types-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-vessel-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-xdd-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotype-xdd-lib-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenotypeActions-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| phenoUtils | Rust | yes | yes | 9 | 2026-05-03 08:24:43 -0700 | 0 | 4 |
| PhenoVCS | Rust | yes | yes | 12 | 2026-05-03 04:10:40 -0700 | 0 | 8 |
| phenoXdd | Unknown | yes | yes | 8 | 2026-05-03 13:32:37 -0700 | 0 | 9 |
| Pine | Unknown | yes | yes | 1 | 2026-05-03 06:13:17 -0700 | 0 | 6 |
| Planify | JS/TS | yes | yes | 12 | 2026-05-03 04:10:34 -0700 | 0 | 6 |
| Planify-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| PlatformKit | Unknown | yes | yes | 1 | 2026-05-03 04:10:32 -0700 | 0 | 5 |
| PlayCua | Rust | yes | yes | 12 | 2026-05-03 08:26:51 -0700 | 0 | 8 |
| PolicyStack | JS/TS, Python | yes | yes | 18 | 2026-05-03 14:10:18 -0700 | 5 | 12 |
| PolicyStack-docs | JS/TS | yes | yes | 11 | 2026-04-02 19:01:10 -0700 | 3 | 12 |
| portage | Python | yes | yes | 29 | 2026-05-03 04:10:39 -0700 | 1 | 14 |
| portage-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| portage-eval-suite | Rust | yes | yes | 39 | 2026-05-02 16:00:47 -0700 | 3 | 111 |
| Portalis-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| pr-207-pin-actions-sha | JS/TS, Python | yes | yes | 13 | 2026-05-02 05:47:54 -0700 | 0 | 12 |
| pr-208-pin-github-actions | JS/TS, Python | yes | yes | 13 | 2026-05-02 05:47:54 -0700 | 0 | 12 |
| pr-22-pin-github-actions | Unknown | yes | yes | 7 | 2026-05-02 05:47:54 -0700 | 0 | 5 |
| pr-274-chore-pin-github-actions-shas | JS/TS, Python, Rust | yes | yes | 51 | 2026-05-02 05:48:12 -0700 | 1 | 22 |
| pr-275-fix-pin-github-actions-sha | JS/TS, Python, Rust | yes | yes | 51 | 2026-05-02 05:48:12 -0700 | 1 | 22 |
| pr-28-chore-pin-github-actions | JS/TS | yes | yes | 3 | 2026-05-02 05:48:55 -0700 | 0 | 5 |
| pr-33-chore-pin-github-actions | Rust | yes | yes | 9 | 2026-05-02 05:47:51 -0700 | 1 | 5 |
| Profila-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| projects-landing | JS/TS | yes | yes | 4 | 2026-05-03 04:10:40 -0700 | 0 | 6 |
| py-sweep | Unknown | no | no | 0 | n/a | 0 | 0 |
| Pyron | JS/TS, Python | yes | yes | 9 | 2026-04-24 16:54:57 -0700 | 4 | 1 |
| QuadSGM | Python | yes | yes | 19 | 2026-05-03 04:10:35 -0700 | 0 | 12 |
| quality-gate | Rust | yes | yes | 17 | 2026-05-02 08:35:26 -0700 | 1 | 20 |
| quality-gate | Rust | yes | yes | 11 | 2026-05-02 08:35:17 -0700 | 0 | 20 |
| quality-gate | Rust | yes | yes | 39 | 2026-05-02 14:56:54 -0700 | 1 | 111 |
| Queris-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Quillr-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| readme-worklog | Unknown | no | yes | 5 | 2026-04-27 01:41:40 -0700 | 0 | 7 |
| release-cut-adopt | Unknown | no | yes | 2 | 2026-04-24 16:15:20 -0700 | 0 | 12 |
| release-cut-adopt | JS/TS | yes | yes | 23 | 2026-04-24 16:15:20 -0700 | 2 | 31 |
| release-cut-adopt | Rust | yes | yes | 6 | 2026-04-27 22:47:57 -0700 | 2 | 13 |
| remove-vendor-tree | Go | yes | yes | 27 | 2026-04-25 18:38:34 -0700 | 6 | 29 |
| repos | Rust | yes | yes | 37 | 2026-05-04 03:34:02 -0700 | 2 | 145 |
| ResilienceKit | Unknown | yes | yes | 8 | 2026-05-04 03:31:44 -0700 | 0 | 14 |
| reusable-ci | Rust | yes | yes | 6 | 2026-04-24 01:30:55 -0700 | 7 | 29 |
| rich-cli-kit | Rust | yes | yes | 12 | 2026-05-04 03:24:37 -0700 | 0 | 8 |
| RIP-Fitness-App | Java | no | yes | 6 | 2026-04-24 16:54:57 -0700 | 0 | 1 |
| rust-sweep | Unknown | no | no | 0 | n/a | 0 | 0 |
| Schemaforge-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| seedloom | JS/TS | no | no | 0 | 2026-04-05 06:51:20 -0700 | 1 | 1 |
| Seedloom-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Settly-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| sharecli-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| shot-deprecate-align | Rust | yes | yes | 0 | 2026-04-23 03:11:48 -0700 | 0 | 20 |
| shot-gallery-v0.1.1 | Rust | yes | yes | 0 | 2026-04-22 20:18:25 -0700 | 0 | 20 |
| Sidekick | Rust | yes | yes | 12 | 2026-05-03 04:17:26 -0700 | 0 | 11 |
| sladge-badge | Go | yes | yes | 0 | 2026-04-29 06:39:34 -0700 | 0 | 9 |
| sladge-badge | Python, Rust | yes | yes | 6 | 2026-04-29 08:15:18 -0700 | 0 | 10 |
| sladge-badge | Unknown | yes | yes | 10 | 2026-04-29 08:40:41 -0700 | 1 | 7 |
| sladge-badge | Rust | yes | yes | 7 | 2026-04-29 05:51:03 -0700 | 0 | 8 |
| sladge-badge | Python | yes | yes | 4 | 2026-04-29 05:30:44 -0700 | 0 | 5 |
| sladge-badge | Unknown | no | no | 0 | n/a | 0 | 0 |
| sladge-badge | Unknown | no | no | 0 | n/a | 0 | 0 |
| sladge-badge | Go, Python | yes | yes | 5 | 2026-04-29 08:02:38 -0700 | 0 | 11 |
| sladge-badge | JS/TS, Rust | yes | yes | 34 | 2026-04-29 05:16:58 -0700 | 2 | 14 |
| sladge-badge | JS/TS | yes | yes | 25 | 2026-04-29 20:14:31 -0700 | 0 | 31 |
| sladge-badge | Rust | no | yes | 3 | 2026-04-30 01:08:17 -0700 | 0 | 8 |
| sladge-badge | Rust | yes | yes | 4 | 2026-04-29 18:23:53 -0700 | 0 | 8 |
| sladge-badge | Rust | yes | yes | 6 | 2026-04-29 21:20:01 -0700 | 0 | 10 |
| sladge-badge | Go | yes | yes | 9 | 2026-04-29 17:58:57 -0700 | 0 | 10 |
| sladge-badge | Unknown | no | no | 0 | n/a | 0 | 0 |
| sladge-badge | Rust | yes | yes | 8 | 2026-04-29 19:33:19 -0700 | 1 | 10 |
| sladge-badge | Rust | no | yes | 4 | 2026-04-29 07:49:42 -0700 | 0 | 3 |
| sladge-badge | JS/TS | yes | yes | 5 | 2026-04-29 18:54:24 -0700 | 0 | 10 |
| sladge-badge | Rust | yes | yes | 3 | 2026-04-30 01:23:12 -0700 | 0 | 20 |
| sladge-badge | Python | yes | yes | 1 | 2026-05-01 18:57:53 -0700 | 0 | 15 |
| sladge-badge | Rust | yes | yes | 6 | 2026-04-29 18:11:15 -0700 | 1 | 11 |
| sladge-badge | Go, Rust | yes | yes | 10 | 2026-04-29 05:53:32 -0700 | 1 | 21 |
| sladge-badge | Unknown | no | no | 0 | n/a | 0 | 0 |
| sladge-badge | Rust | yes | yes | 4 | 2026-04-29 22:14:57 -0700 | 1 | 7 |
| sladge-badge | Go | yes | yes | 7 | 2026-04-29 05:35:05 -0700 | 0 | 9 |
| sladge-badge | Rust | yes | yes | 7 | 2026-04-29 06:25:49 -0700 | 0 | 11 |
| sladge-badge | JS/TS, Rust | yes | yes | 9 | 2026-04-29 22:00:40 -0700 | 1 | 14 |
| sladge-badge | JS/TS, Python | yes | yes | 16 | 2026-04-29 18:27:04 -0700 | 0 | 12 |
| sladge-badge | Rust | yes | yes | 25 | 2026-04-29 06:10:31 -0700 | 0 | 11 |
| sladge-badge | Python | yes | yes | 1 | 2026-04-29 07:05:53 -0700 | 0 | 6 |
| sladge-badge | Unknown | yes | yes | 3 | 2026-04-30 00:38:54 -0700 | 1 | 11 |
| sladge-badge | Python | yes | yes | 4 | 2026-04-29 05:18:43 -0700 | 0 | 9 |
| sladge-badge | Rust | yes | yes | 6 | 2026-04-29 19:20:23 -0700 | 1 | 6 |
| source-manifests | Rust | yes | yes | 6 | 2026-04-23 08:29:50 -0700 | 5 | 29 |
| spec-014-observability-stack-completion | Rust | yes | yes | 38 | 2026-05-02 13:04:29 -0700 | 2 | 111 |
| Stashly-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Tasken | Rust | yes | yes | 21 | 2026-05-03 13:32:37 -0700 | 0 | 9 |
| Tasken-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| template-commons-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| template-program-ops-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| templates-fix | Rust | yes | yes | 8 | 2026-04-25 11:44:22 -0700 | 3 | 25 |
| TestingKit | Unknown | yes | yes | 9 | 2026-05-04 03:34:27 -0700 | 0 | 11 |
| thegent | JS/TS, Python | yes | yes | 24 | 2026-05-03 14:34:03 -0700 | 1 | 57 |
| thegent-dispatch | Rust | yes | yes | 11 | 2026-05-04 03:24:37 -0700 | 0 | 3 |
| thegent-docs | JS/TS | yes | yes | 17 | 2026-04-03 00:47:33 -0700 | 12328 | 57 |
| thegent-landing | JS/TS | yes | yes | 4 | 2026-05-03 04:10:38 -0700 | 0 | 4 |
| thegent-pr908-policy-fix | JS/TS, Python | yes | yes | 7 | 2026-04-02 15:09:44 -0700 | 9 | 57 |
| thegent-sharecli-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| thegent-workspace | Rust | yes | yes | 11 | 2026-05-03 08:14:23 -0700 | 0 | 3 |
| Tokn | Rust | yes | yes | 28 | 2026-05-03 06:21:21 -0700 | 0 | 11 |
| Tokn-docs | JS/TS, Rust | yes | yes | 19 | 2026-04-03 02:53:27 -0700 | 3 | 11 |
| Tossy-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Tracely | Rust | yes | yes | 13 | 2026-05-03 08:26:52 -0700 | 0 | 13 |
| tracely-docs | JS/TS, Rust | yes | yes | 6 | 2026-04-29 05:10:59 -0700 | 1 | 13 |
| Tracera | JS/TS, Python | yes | yes | 38 | 2026-05-04 01:38:36 -0700 | 7 | 9 |
| Tracera-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Tracera-recovered-20260502-ghost | JS/TS, Python | yes | yes | 38 | 2026-05-02 14:19:39 -0700 | 0 | 16 |
| trufflehog | Unknown | yes | yes | 2 | 2026-05-02 05:32:02 -0700 | 0 | 2 |
| trufflehog | JS/TS | yes | yes | 27 | 2026-05-02 05:32:00 -0700 | 0 | 2 |
| trufflehog | Go, JS/TS | yes | yes | 27 | 2026-05-02 05:33:03 -0700 | 0 | 2 |
| trusted-publishing | Unknown | yes | yes | 4 | 2026-04-24 15:20:13 -0700 | 0 | 14 |
| trusted-publishing | Unknown | yes | yes | 4 | 2026-04-24 15:20:13 -0700 | 0 | 10 |
| urlguard | Go, JS/TS | yes | yes | 26 | 2026-04-25 10:58:09 -0700 | 2 | 20 |
| user-story-batch1 | Rust | yes | yes | 0 | 2026-04-22 03:38:32 -0700 | 0 | 20 |
| vibeproxy | Unknown | yes | yes | 13 | 2026-05-03 13:32:37 -0700 | 0 | 8 |
| vibeproxy-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| vibeproxy-monitoring-unified | Unknown | yes | yes | 10 | 2026-05-03 04:10:38 -0700 | 0 | 7 |
| vibeproxy-monitoring-unified-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| viewer-013 | Rust | yes | yes | 6 | 2026-04-23 08:16:41 -0700 | 7 | 29 |
| viewer-v0.1.3 | Rust | yes | yes | 0 | 2026-04-23 08:15:59 -0700 | 0 | 20 |
| vitepress | Unknown | yes | yes | 7 | 2026-05-02 08:25:36 -0700 | 0 | 2 |
| wip-byteport-residual-stash | Go, Rust | yes | yes | 8 | 2026-04-27 18:52:12 -0700 | 3 | 21 |
| wip-git-parallelism | JS/TS, Python | yes | yes | 22 | 2026-05-01 20:20:49 -0700 | 2 | 57 |
| wip-heliosapp-observability-completion | JS/TS | yes | yes | 21 | 2026-04-05 06:25:53 -0700 | 2 | 31 |
| wip-helioslab-license-badge | JS/TS, Rust | yes | yes | 17 | 2026-05-02 08:21:50 -0700 | 2 | 20 |
| wip-idea-seeds | JS/TS, Python | yes | yes | 22 | 2026-05-01 18:42:15 -0700 | 2 | 57 |
| wip-localbase3-provider-tests | Unknown | yes | yes | 4 | 2026-05-02 07:48:28 -0700 | 0 | 11 |
| wip-phenoDesign-archive-undo | JS/TS | yes | yes | 8 | 2026-04-27 18:21:47 -0700 | 0 | 13 |
| wip-phenodocs-link-checker | JS/TS, Python | yes | yes | 13 | 2026-05-02 04:59:52 -0700 | 0 | 12 |
| wip-PhenoPlugins-spec | Rust | no | yes | 2 | 2026-04-23 20:26:48 -0700 | 0 | 14 |
| wip-PhenoSpecs-charter | Unknown | no | yes | 1 | 2026-04-25 19:41:37 -0700 | 0 | 12 |
| workflow-worklog-hygiene-20260427 | Rust | yes | yes | 26 | 2026-04-27 03:21:29 -0700 | 2 | 11 |
| worklog-index | Unknown | no | yes | 8 | 2026-04-27 01:53:09 -0700 | 0 | 7 |
| workspace-deps-fix | JS/TS, Rust | yes | yes | 28 | 2026-04-25 11:17:26 -0700 | 3 | 14 |
| worktree-manager | Rust | no | yes | 5 | 2026-05-01 20:51:30 -0700 | 1 | 1 |
| zen-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
| Zerokit-docs | Unknown | no | no | 0 | n/a | 0 | 0 |
