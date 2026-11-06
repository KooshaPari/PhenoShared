# thegent Unified Skill — Design Doc

Draft design for Task C (absorption of single-provider agent skills into
`thegent` meta-dispatcher). Hybrid recommendation: keep provider skills as thin
specialization files; promote `thegent` to default trigger.

## Arg schema (proposed)

- `provider: enum{forge, codex, gemini, copilot, cursor, droid, minimax, claude}` — required; default `forge`.
- `prompt: string` — required unless `mode=interactive`.
- `cwd: path` — default `$PWD`.
- `model: string` — optional; rejected for copilot (locked).
- `mode: enum{agent, quick-edit, research, plan, background, read-only, write, autopilot}` — mapped per provider.
- `reasoning: enum{low, medium, high}` — forwarded to codex only.
- `session: enum{oneshot, bg, interactive}` — `bg` implies owner-tag flow.
- `owner: string` — auto-set from `THGENT_OWNER_TAG`; required for `session=bg`.
- `routing: enum{prefer_direct, prefer_proxy, failover, round_robin, cheapest, cost_quality, pareto, roi}` — thegent policy.
- `timeout_s: int`, `sandbox: bool`, `restricted: bool`, `conversation_id: string` — passthrough.
- `extra_flags: string[]` — escape hatch.

## Mode → provider-native mode mapping

| mode | forge | codex | copilot | cursor | gemini | droid |
|---|---|---|---|---|---|---|
| agent | `-p` | `workspace-write` | `autopilot` | agent | `/agent` | default |
| quick-edit | `-p` small model | `read-only` | `programmatic` | interactive | inline | n/a |
| research | `-p --restricted` | `read-only low` | `programmatic` | `/plan` | chat | n/a |
| plan | `--agent planner` | `read-only high` | n/a | `/plan` | chat | n/a |
| background | `thegent bg` | bg via wrapper | `autopilot+--cd` | background-VM | n/a | wrapper |

## Dispatch strategy

1. Validate arg compatibility (reject `model` when `provider=copilot`).
2. Map `mode` → provider-native mode (table above).
3. Build argv per provider.
4. If `session=bg`, wrap in `thegent bg --owner --format json`.
5. Log the equivalent raw command for auditability.

## Trigger discipline

- `thegent` broad trigger: "dispatch prompt to any agent CLI."
- Provider skills trigger only on explicit provider mention.
- No deletions; add a "Relationship → thegent" section to each provider skill.

## Capability-preservation notes

Provider-unique capabilities that MUST stay in specialized skills:
- **codex**: `--reasoning {low|medium|high}` + sandbox tri-state
- **copilot**: Claude Haiku 4.5 model lock (must be hard-rejected, not silently dropped, in unified API)
- **cursor**: Composer 2.0 slash commands, background-VM, IDE-only workflows
- **gemini**: multi-modal input, 1M-ctx repo-index, `/review` mode
- **forge**: `--conversation` threading, `--agent` flag, native multi-provider routing

## Implementation Requirements

1. Write `~/.claude/skills/thegent/SKILL.md` with the unified API, provider
   matrix, and dispatch rules described above.
2. Add a `Relationship: default to \`thegent\` unless ...` note to each provider
   skill so trigger precedence is explicit.
3. Create a `thegent dispatch <argv>` CLI entrypoint in Rust, following the
   scripting policy used elsewhere in thegent tooling.
4. Add an argument-validation layer that hard-rejects provider and flag
   mismatches instead of silently dropping unsupported options.
5. Validate the implementation by running 20 representative prompts through the
   existing single-provider skills and the new dispatcher, then compare argv
   parity.

## References

- Existing skills inventoried: forge-agent, codex-agent, gemini-agent,
  copilot-agent, cursor-agent, droid-agent (missing SKILL.md), thegent-skills.
