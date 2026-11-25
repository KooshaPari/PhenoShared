# gsd (open-gsd/gsd-core, successor of glittercowboy/get-shit-done)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/bmad-gsd.md (primary: https://github.com/open-gsd/gsd-core)

## What it is

GSD (get-shit-done) is a hybrid: prompt/command layer (commands/gsd/*.md, agents/*.md) plus a real Node runtime (gsd-core/bin/gsd-tools.cjs with 20 domain modules under bin/lib/), npm-published as @opengsd/gsd-core, installed via npx @opengsd/gsd-core@latest. Persistent state lives in the project's .planning/ directory. Canonical repo today open-gsd/gsd-core ("Git. Ship. Done - Core"), archived: false, default branch next, pushed 2026-11-12T07:25:30Z, 11,478 stars. TACHES-era repo glittercowboy/get-shit-done is now archived (renamed to gsd-build/get-shit-done), pushed 2026-05-31, last release v1.43.0-rc2 (2026-05-17); tags to v1.50.0-canary.2. Relationship: continuation, not a fork (same lineage, same npm package line @opengsd/gsd-core). License MIT (spdx_id MIT). Current version v1.20.1 released 2026-11-05 (previous v1.20.0 2026-11-03, v1.19.0 2026-10-26, v1.18.0 2026-10-19, v1.17.0 2026-10-14, v1.16.0 2026-10-05). Multi-runtime: Claude Code, OpenCode, Antigravity CLI, Kimi CLI, Kilo, Codex, Copilot, Cursor, Windsurf, and more. Installer required for cross-runtime compatibility - do not copy files from agents/ or commands/ directly.

## Artifact model (exact paths/filenames it writes)

From docs/reference/planning-artifacts.md (ref next):
.planning/
- PROJECT.md - project identity + core value
- ROADMAP.md - milestone + phase listing with goals
- REQUIREMENTS.md - numbered acceptance criteria
- STATE.md - living position tracker
- config.json - workflow + model configuration
- MILESTONES.md / BACKLOG.md / LEARNINGS.md / DECISIONS-INDEX.md / METHODOLOGY.md (all optional)
- HANDOFF.json - machine-readable pause state (transient)
- codebase/ (opt) onboarding/ (opt) intel/API-SURFACE.md (opt)
- phases/<NN>-<slug>/
  - <NN>-CONTEXT.md - implementation decisions (discuss)
  - <NN>-DISCUSSION-LOG.md - human-readable discussion audit (discuss)
  - <NN>-RESEARCH.md - technical research (plan)
  - <NN>-VALIDATION.md - Nyquist test-coverage strategy (plan)
  - <NN>-PATTERNS.md - codebase analog map (plan, optional)
  - <NN>-<PP>-PLAN.md - executable plan (plan)
  - <NN>-<PP>-SUMMARY.md - execution record (execute)
  - <NN>-VERIFICATION.md - phase-goal verification report (verify)
  - <NN>-UAT.md - persistent UAT session state
  - .continue-here.md - resume instructions after pause

REQUIREMENTS.md: "Numbered, checkable acceptance criteria... Each requirement carries an ID (e.g., AUTH-01) that maps to roadmap phases." STATE.md: "Living position tracker... Read at the start of every workflow run." CONTEXT.md fields: phase boundary (<domain>), locked decisions with D-NN identifiers (<decisions>), canonical document references (<canonical_refs>), existing code insights (<code_context>), specific inspirations (<specifics>), deferred ideas (<deferred>).

Phase model (docs/explanation/the-phase-loop.md): Discuss -> (UI design) -> Plan -> Execute -> Verify -> Ship. Unit of work: phase (one bounded piece with goal, requirement IDs, plans). Container: milestone (a version cycle with requirements). "A milestone is complete when all its phases are shipped and its requirements are covered."

## Traceability enforcement

Strongest partial among these tools. Stable requirement IDs (REQ/AUTH-01), blocking Requirements Coverage Gate at plan time (extract requirement IDs for phase from ROADMAP.md; verify each appears in at least one PLAN.md; uncovered requirements MUST block planning completion; report which lack coverage; runs automatically at end of /gsd-plan-phase). Nyquist Validation (VALIDATION.md) maps requirement -> test command; REQ-NYQ-02 "System MUST map each requirement to a specific test command"; REQ-NYQ-04 "Plan checker MUST enforce Nyquist compliance as 8th verification dimension"; produces {phase}-VALIDATION.md; retroactive /gsd-validate-phase [N] "Identifies gaps where requirements lack automated verification". Verifier agent produces VERIFICATION.md: checks requirement coverage (were all REQ-IDs addressed?), decision coverage (were CONTEXT.md decisions implemented?), overall phase goal alignment. Staleness by content fingerprint (docs/how-to/verify-and-ship.md): verifier records digest of every input its verdict covers (PLAN.md/SUMMARY.md files, mapped requirements, implementation files in change set); if any changes, disappears, or becomes unreadable after verification, gate recomputes digest, finds mismatch, reports stale. Plan-vs-codebase drift guard (docs/adr/22-plan-drift-guard.md, Accepted 2026-07-17): symbol resolver returning VERIFIED / MISSING / AMBIGUOUS / UNCHECKABLE, authority ladder (rung 0 ripgrep -> 4 SCIP), shipped on by default via plan_review.source_grounding. Rungs 0-1 produce needs-acknowledgement (not hard block); only rung >= 3 can hard-block. But coverage gate runs at plan time (nothing re-runs after code written and spec changes); VALIDATION.md is LLM-authored from research, not derived from test suite by a tool; fingerprint is a re-run gate not a surviving link; drift guard checks plan -> codebase symbols (different edge from requirement -> test).

## Interface surface

CLI (Node, npm @opengsd/gsd-core) plus slash commands / skills. Agent integrations: Claude Code, OpenCode, Antigravity CLI, Kimi CLI, Kilo, Codex, Copilot, Cursor, Windsurf, and more. No MCP server and no SDK documented (gsd-tools.cjs is internal runtime). Docs feature set: requirements-coverage-gate, nyquist-validation, work-verification, end-of-phase-human-verification-mode, context-drift-gate, context-reduction, context-window-monitoring, execution-context-profiles, persistent-context-threads, plan-drift-guard.

## Interactivity

Discuss step is interactive (human decisions captured in CONTEXT.md with D-NN IDs). Plan/Execute/Verify use fresh-context subagents (researcher -> RESEARCH.md, planner -> PLAN.md, plan-checker). /gsd-verify-work N is UAT: reads SUMMARY.md files, extracts user-observable deliverables, walks through them one at a time, presents what should happen, asks whether reality matches; severity inferred from words; results persist in <phase>-UAT.md. Human verification mode default workflow.human_verify_mode = "end-of-phase" embeds human checks in <verify><human-check> blocks; REQ-HUMAN-VERIFY-01 - checkpoint:decision and checkpoint:human-action MUST remain blocking regardless of mode. Code review explicitly NOT automatic: "/gsd-ship does not run a code review automatically." /gsd-ship runs preflight (verification status, clean working tree, branch, remote, gh CLI auth) and assembles PR body from artifacts.

## External verification

Automated plus human. Automated: Requirements Coverage Gate (blocking at plan time), Nyquist Validation (requirement -> test command mapping), verifier agent VERIFICATION.md, content-fingerprint staleness (stale verdict), plan-drift guard (symbol resolver). Human: UAT walkthrough, end-of-phase human verification mode, code review (manual). /gsd-ship preflight checks. Anti-gaming: ADR 1606 (docs/adr/1606-prohibition-enforcement-verify-seam.md) documents verify-time enforcement producer with vacuity guards isNonVacuousNodeTestRed and isNonVacuousNodeTestPass, and defaultProveFailFirst requiring a test to be shown to fail on a clean fixture before counting as green. Code exists and is well-tested (src/prohibition-enforcement.cts, src/probe-core.cts, tests/prohibition-enforcement.test.cjs, 1336 lines) but ADR Status still "Proposed" and explicitly "non-binding" until ADR-550's four addenda collapsed into a pointer (not happened). Content-fingerprint staleness prevents stale verdict read as fresh (drift detection, not gaming detection).

## License

MIT.

## Notes

Canonical repo is open-gsd/gsd-core (successor, not fork of archived glittercowboy/get-shit-done). Archived TACHES-era artifact set at v1.43.0-rc2 and phase model at v1.43.0-rc2 are UNREACHABLE (git/trees listing truncated by .changeset/ entries before reaching commands/, agents/, or .planning/ templates); artifact list and phase model above are gsd-core current, not TACHES-era. Neither GSD nor BMAD enforces durable requirement->test->artifact linkage surviving spec change; GSD has strongest partial (blocking coverage gate + Nyquist mapping + fingerprint staleness).
