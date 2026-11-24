# Tool comparison matrix (15 tools)

Source: durable profiles in this directory; volatile drafts in /Users/kooshapari/CodeProjects/temp/proresearch-20261110/. No percentages. Negative/unknown cells use NONE / PARTIAL / UNKNOWN.

| Tool | Artifact model | Requirement->test->artifact linkage | Survives spec change | Interface (CLI/MCP/SDK) | Interactive refine | External verification | Anti-gaming | Runtime vs prompt-pack | License | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| agileplus | Spec + WP + receipt | PARTIAL (governance/audit; acceptance upstream) | NONE (receipts report history) | CLI + MCP (deploy UNKNOWN) | PARTIAL (elicit tools) | PARTIAL (validate + upstream tests) | PARTIAL (preflight not token) | Runtime (Rust) | UNKNOWN | Atomic acceptance upstream @ 8699676; absent from PhenoShared by snapshot age |
| openspec | Change dir + deltas | NONE (grammar only) | NONE (voluntary archive) | CLI (no MCP/SDK) | PARTIAL (no freeze) | NONE (structure only) | NONE | Runtime (CLI) | MIT | Validation is spec grammar; checkboxes are gaming surface |
| speckitty | kitty-specs + worktrees | NONE (AC stored, not checked) | NONE | CLI (MCP UNKNOWN) | PARTIAL (lane gates) | PARTIAL (git ops only) | NONE | Runtime (Python) | MIT | Worktree-per-WP conflicts host worktree policy; 4.0.0rc |
| bmad | Brief/PRD/arch/epics/stories | NONE (static AC annotations) | NONE (not re-derived) | CLI/skills (no MCP) | PARTIAL (human gates) | PARTIAL (lint_spine, shard check) | PARTIAL (placeholder lint) | Prompt-pack (+Python helpers) | MIT | No SM/QA personas in core; bmad-loop is separate repo |
| gsd | REQUIREMENTS + VALIDATION + VERIFICATION | PARTIAL (coverage gate + Nyquist) | PARTIAL (fingerprint stale) | CLI (no MCP/SDK) | PARTIAL (Discuss + UAT) | PARTIAL (gates + UAT) | PARTIAL (vacuity guards Proposed) | Hybrid (Node runtime) | MIT | ADR 1606 vacuity guards Proposed/non-binding; TACHES-era artifacts UNREACHABLE |
| spec-kit | spec/plan/tasks/contracts | NONE (advisory templates) | NONE | CLI (no MCP/SDK) | PARTIAL (human review) | PARTIAL (bug verdicts) | NONE | Prompt-pack (templates) | MIT | Constitution test-first is prompt-level; grader is same model |
| kiro | requirements/design/tasks | YES (EARS -> PBT) | PARTIAL (Sync Files) | IDE + CLI V3 (no MCP) | PARTIAL (phase variants) | PARTIAL (PBT IDE-only) | NONE | Runtime (IDE) | UNKNOWN | PBT IDE-only, optional by default, evidence not proof |
| tessl | Spec + tests (closed beta) | PARTIAL (framework closed beta) | UNKNOWN | CLI + MCP (tool list UNKNOWN) | PARTIAL (plan review/edit) | PARTIAL (evals for skills) | PARTIAL (governance scoring) | Runtime (platform) | NOASSERTION (GitHub) | Framework closed beta; public CLI small, no releases |
| agent-os | Standards + shaped spec | NONE | NONE | Slash commands + shell | PARTIAL (shaping) | NONE | NONE | Prompt-pack (standards) | MIT | Standards are prose; no machine-readable rule format |
| cc-sdd | requirements/design/tasks (EARS) | PARTIAL (TDD per task, reviewer) | NONE (code is source of truth) | CLI installer (no MCP) | PARTIAL (phase gates) | PARTIAL (TDD + review) | PARTIAL (reviewer model) | Prompt-pack (skills) | MIT | Reviewer is same harness model; no machine-checkable trace |
| task-master | Task graph + subtasks | NONE (PRD->task only) | NONE | MCP (36 tools) + CLI | NONE (one-shot) | NONE (presence only) | NONE | Runtime (MCP server) | MIT WITH Commons-Clause | Dependency graph integrity only; no test/code link |
| prp | PRD + context + validation cmds | PARTIAL (validation in packet) | NONE | Skills + slash commands | PARTIAL (PRD + loop) | PARTIAL (CI + PR review) | NONE | Prompt-pack (skills) | MIT (helper 0.1.0) | Runtime state in ~/.prp (not version controlled); no releases/tags |
| conductor | Workspace/branch (no spec) | NONE | NONE | Mac app (no CLI/MCP/SDK) | PARTIAL (Plan Mode) | PARTIAL (Checks tab) | NONE | Runtime (Mac app) | UNKNOWN | Todos/specs tasks pages UNREACHABLE (404) |
| aider | Conventions (Markdown) | NONE | NONE | CLI (no MCP/SDK) | PARTIAL (REPL) | PARTIAL (lint/test loop) | NONE | Runtime (CLI) | Apache-2.0 | Conventions are soft prose; last push 2026-05-22 |
| claude-code | Subagent/skill files | NONE | NONE | CLI + skills (no MCP server) | PARTIAL (chat) | NONE (format lint only) | NONE | Runtime (harness) | UNKNOWN | allowed-tools is permission, not verification; /verify user-invoked |

## Who actually links a requirement to an executable check

- Kiro: EARS requirements -> extracted properties -> generated property-based tests, with a documented link to the originating requirement and linked task (IDE-only, optional by default, "evidence not proof").
- GSD: Nyquist VALIDATION.md maps each requirement to a specific test command; Requirements Coverage Gate blocks planning when a requirement has no plan; verifier agent checks requirement coverage in VERIFICATION.md.
- PRP: validation (executable commands) is part of the requirement packet; /prp-implement and /prp-issue drive plan -> PR with green CI.
- cc-sdd: per-task TDD (RED -> GREEN) behind a feature flag plus an independent reviewer; boundary violations checked.
- Tessl: spec enriched with tests that verify code matches intent (Framework closed beta; details UNKNOWN).
- AgilePlus: atomic acceptance upstream (candidate -> immutable receipt with DB-level no_update/no_delete triggers) - acceptance, not requirement->test.

## Who survives a spec change

- GSD: content-fingerprint staleness flips a passing verdict to stale when any covered file changes, disappears, or becomes unreadable (then re-derived by the LLM verifier).
- Kiro: Sync Files on tasks.md creates new tasks mapping to updated requirements.
- Others: NONE documented; BMAD's FR Coverage Map is a template slot rendered once and never re-derived; openspec has no freeze; spec-kit/cc-sdd treat code as source of truth.

## What none of them do

Measured gap set (from the drafts, not inferred):
- No durable requirement -> test -> artifact linkage that survives a spec change (all re-derive or store statically).
- No machine-checkable requirement-coverage report over a learner's repository.
- No rubric, scoring, or submission envelope for coursework.
- No anti-gaming beyond placeholder lint (GSD vacuity guards exist but ADR 1606 is Proposed and non-binding).
- No independent verifier separate from the agent that wrote the code (reviewers are same-harness models).
- No freeze ceremony or immutable signed baseline (openspec explicitly rejects freeze gates).
- No requirement entity that a grader could query (task-master, openspec, spec-kit lack requirement IDs).

## Sources

- agileplus: https://github.com/KooshaPari/AgilePlus
- openspec: https://github.com/Fission-AI/OpenSpec
- speckitty: https://github.com/spec-kitty/spec-kitty
- bmad: https://github.com/bmad-code-org/BMAD-METHOD
- gsd: https://github.com/open-gsd/gsd-core
- spec-kit: https://github.com/github/spec-kit
- kiro: https://kiro.dev/docs/specs/
- tessl: https://github.com/tesslio/cli
- agent-os: https://github.com/buildermethods/agent-os
- cc-sdd: https://github.com/gotalab/cc-sdd
- task-master: https://github.com/eyaltoledano/claude-task-master
- prp: https://github.com/Wirasm/prp
- conductor: https://www.conductor.build/docs/
- aider: https://github.com/Aider-AI/aider
- claude-code: https://docs.claude.com/en/docs/claude-code/sub-agents
