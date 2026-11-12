# kiro (AWS, kiro.dev)

Source: /Users/kooshapari/CodeProjects/temp/proresearch-20261110/kiro-conductor-cc.md (primary: https://kiro.dev/docs/specs/, https://kiro.dev/docs/specs/correctness/, https://kiro.dev/docs/hooks/)

## What it is

Kiro is an AWS IDE (kiro.dev) with a spec-driven flow. Every spec generates three artifacts under .kiro/specs/: requirements.md (or bugfix.md) - user stories + acceptance criteria, or bug analysis; design.md - architecture, sequence diagrams, implementation considerations; tasks.md - discrete, trackable implementation tasks. Three-phase workflow: Requirements (or Bug Analysis) -> Design -> Tasks. Two Feature Spec workflow variants: Requirements-First (Requirements -> Design -> Tasks) and Design-First (Design -> Requirements -> Tasks). Quick Spec auto-generates all three in one pass with no approval gates between phases. Bugfix Specs follow the same three phases but with bugfix.md instead of requirements.md.

## Artifact model (exact paths/filenames it writes)

- .kiro/specs/<name>/requirements.md (or bugfix.md) - user stories + acceptance criteria, or bug analysis
- .kiro/specs/<name>/design.md - architecture, sequence diagrams, implementation considerations
- .kiro/specs/<name>/tasks.md - discrete, trackable implementation tasks
- .kiro/hooks/<id>.json - standalone JSON hook files (schema version: "v1"), plus global hooks at ~/.kiro/hooks/ in Kiro CLI V3, activate automatically at session start.
- Hook action types: {"type": "command", ...} (shell command, session context delivered as JSON on STDIN) and {"type": "agent", ...} (injects a prompt into the current conversation). Command hooks support timeout (default 60s, 0 disables) and confirm blocks with static or dynamic (confirmCommand) options.
- Hook trigger types: Prompt Submit, Agent Stop, Session Start, Session End, Pre/Post Tool Use, File Create/Save/Delete, Pre/Post Task Execution, Pre/Post Compaction. IDE/CLI V3/Web support varies (table in source).
- Kiro builds a dependency graph of tasks.md items and groups independent tasks into waves; waves run sequentially, tasks within a wave run concurrently ("Run all Tasks"). "Sync Files" on tasks.md creates new tasks that map to updated requirements.

## Traceability enforcement

YES (strongest), with documented limits. Property-based testing page: Kiro extracts properties from EARS-formatted requirements, determines which are logically testable, and generates randomized test cases. "Hovering over a property reveals its connection to the original requirement and linked task." Docs state this "maintains a clear, traceable link between your requirements and the tests that validate them." Bugfix Specs: "Implementation tasks are generated with property-based tests (PBTs) that validate: the bug is reproducible; the bug is fixed; no regressions are introduced." Limits: PBT "provides evidence of correctness, not a proof"; "not every requirement maps cleanly to a property" (external services and non-deterministic behavior may need mocking or example-based tests); PBT is optional by default so you can focus on core implementation first. Specs capability table lists property-based testing as IDE-only (CLI, Web, Mobile: not supported). Acceptance criteria live in requirements.md, not tasks.md. EARS notation: WHEN [condition/event] THE SYSTEM SHALL [expected behavior]; bugfix specs use three-part EARS variant (Current Behavior Defect / Expected Behavior Correct / Unchanged Behavior Regression Prevention).

## Interface surface

Kiro IDE (1.x no longer presents Vibe-vs-Spec picker at session start; sessions start with default agent, free-flow chat or built-in workflow agent (Spec, Plan, Bug Fix, Quick Spec); switch agents mid-session). Quick Spec FAQ: "Vibe mode is conversational and unstructured - there are no artifacts saved to .kiro/specs/. Quick Spec still produces the full Spec artifacts (requirements, design, tasks), just without approval gates between phases." Vibe conversation can be promoted ("Generate spec"). Kiro CLI V3 (hooks). No MCP server and no SDK documented.

## Interactivity

Multi-turn structured. Requirements-First or Design-First variants; Quick Spec one-pass no gates. Bugfix Specs same three phases with bugfix.md.

## External verification

Property-based testing (IDE-only, optional by default) generates randomized test cases from EARS requirements with documented link to originating requirement and linked task. "Analyze Requirements" cross-requirement analysis (static, IDE-only). Task dependency waves for parallel execution. Caveats: PBT evidence not proof; not every requirement maps to a property; optional by default.

## License

UNKNOWN (not stated in draft).

## Notes

Kiro is the only one of the three (Kiro, Conductor, Claude Code) with a documented requirement -> executable-check path, by making requirements machine-interpretable (EARS) then generating properties. Property-based testing is IDE-only and optional by default. Conductor and Claude Code operate upstream (task/plan exists) with git/CI-shaped verification, not requirement-shaped.
