# Traceability and autograder direction: closure ledger

Status: OPEN. Activity, agent reports and file existence alone do not establish completion.

## Intent

Develop an ecosystem direction for an assignment-style specification and autograder informed by SCTBDD and related methods: refine intent, requirements and behavior with the human, freeze approved expectations, and enable downstream agents to implement and test against them. Avoid duplicating AgilePlus.

## User direction (2026-11-11)

- SCTBDD is an umbrella spanning specification, contract, test, behavior and other relevant DD methodologies. Research the wider methodology landscape; do not invent an expansion.
- Frozen expectations retain immutable revisions with supersession and change-management escalation. The retroactive regrading policy remains unresolved.
- Agents resolve routine details; material ambiguities and contradictions escalate instead of silently changing canonical expectations.
- Cover all work types and both task and broader quality levels. Include the full assignment packet and public/private testing where appropriate.
- Use strict full runs and coverage. Requirements-bound tests carry most of the score; regressions against the overall baseline can make the grade negative. New-feature defects beyond mapped requirements or baseline prevent 100%.
- Always involve PhenoRegistry and the work repository (PhenoShared here). Apply dagrun and AgilePlus stage gates to this work; assess actual availability before asserting they ran.
- Research AgilePlus history for one, multiple or no defensible peaks. Compare actual usable CLI, MCP and SDK surfaces and regressions against latest.

## Deliverables and acceptance checks

- [ ] **Intent and methodology:** Document the intended conversation, assumptions, unresolved terminology, decision authority, and human approval. Preserve raw intent without claiming approval.
- [ ] **AgilePlus assessment:** Identify latest release and defensible peak or least-regressive candidate, including source revisions. Test CLI, MCP and SDK where feasible. Distinguish observed behavior, source-only capability, missing dependencies and untested paths. Capture reproducible commands, exit codes and limitations.
- [ ] **Comparison:** Compare OpenSpec, SpecKitty, BMAD and GSD, plus GitHub spec-kit, Kiro, Tessl, Agent OS, cc-sdd, Task Master, PRP, Conductor, Aider conventions and Claude Code skills/subagents. For each cite primary sources and identify artifact model, traceability, interaction, interfaces and verification. Mark unknowns explicitly.
- [ ] **Epic direction:** Define assignment packet contents, stable identifiers, approval and freeze, versioning and change impact, test ownership, scope and starter files, and requirements-to-scenario-to-test-to-evidence links. Provide example and measurable acceptance criteria.
- [ ] **Verification and safety:** Specify independent execution, isolation, negative controls, integrity and provenance, missing evidence, nondeterminism, failure handling and grade interpretation. Avoid equating a hash or a passing test with proof of semantic correctness.
- [ ] **Ownership boundaries:** Define the source of truth and integration contracts for AgilePlus, dagrun and traceability consumers. Do not create a parallel feature lifecycle, work-package system or governance platform. Resolve ownership before implementation.
- [ ] **Review and delivery:** Independently review evidence and contradictions, verify paths and reproducibility, preserve unrelated changes, and deliver the artifacts. Record any blocked or unvalidated criterion; obtain human acceptance where required.

## Known observations and open questions

- The installed AgilePlus CLI reported 0.2.4 and supported specify, research, plan and list in a smoke test. Its validation returned exit 1 for missing evidence after the test feature entered implementing. These observations do not establish a working full delivery cycle.
- The MCP and SDK surfaces and least-regressive version remain unverified end to end. The larger MCP source tree and the absorbed copy differ; source presence is not a working deployment.
- Dagrun verifies declared artifact and kind checks, but the desired human-led freeze and independent grading flow have not been demonstrated.
- A prior implement smoke test dispatched an agent and created a temporary worktree. Its final process and worktree state must be inspected safely before declaring the experiment closed.
- Partial tool profiles exist under `docs/research/tools/`. Reports under `~/CodeProjects/temp/proresearch-20261110/` are volatile and are not durable deliverables.

## Checkpoint protocol

For each item record PASS, FAIL, NOT_RUN, UNKNOWN or BLOCKED with source, revision, timestamp and concrete next step. Never mark the overall intent closed while a required item is unresolved or evidence is missing.
