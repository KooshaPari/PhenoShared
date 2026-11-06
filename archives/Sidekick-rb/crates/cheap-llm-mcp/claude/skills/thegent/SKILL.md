---
name: thegent
description: |
  Dispatch a prompt to any external coding-agent CLI (Forge, Codex, Gemini,
  Copilot, Cursor, Droid) with a unified arg schema. Use for: running a one-shot
  prompt on another agent, launching a background owner-tagged session, choosing
  a model across providers, wiring agent work into the Phenotype work stream.
  Drop down to a provider-specific skill (codex-agent, gemini-agent, etc.) only
  when the provider exposes a capability not in this contract.
---

# thegent — Unified Agent Dispatcher

Default entry point for any "run this prompt on an external agent" request.
Takes a `provider` enum and translates to the native CLI invocation.

## Args

| arg | type | notes |
|---|---|---|
| `provider` | `forge \| codex \| gemini \| copilot \| cursor \| droid \| minimax \| claude` | required; default `forge` |
| `prompt` | string | required unless `mode=interactive` |
| `cwd` | path | default `$PWD` |
| `model` | string | optional; **hard-rejected** for `copilot` (Haiku-locked) |
| `mode` | `agent \| quick-edit \| research \| plan \| background \| read-only \| write \| autopilot` | mapped per provider (see table) |
| `reasoning` | `low \| medium \| high` | forwarded to `codex` only; warning elsewhere |
| `session` | `oneshot \| bg \| interactive` | `bg` implies owner-tag flow |
| `owner` | string | auto from `$THGENT_OWNER_TAG`; required when `session=bg` |
| `routing` | `prefer_direct \| prefer_proxy \| failover \| round_robin \| cheapest \| cost_quality \| pareto \| roi` | thegent policy; ignored by raw `forge` |
| `timeout_s` | int | passthrough |
| `sandbox`, `restricted` | bool | passthrough where supported |
| `extra_flags` | string[] | escape hatch |

## Mode → provider-native mapping

| mode | forge | codex | copilot | cursor | gemini | droid |
|---|---|---|---|---|---|---|
| agent | `-p` | `workspace-write` | `autopilot` | agent | `/agent` | default |
| quick-edit | `-p` small model | `read-only` | `programmatic` | interactive | inline | n/a |
| research | `-p --restricted` | `read-only low` | `programmatic` | `/plan` | chat | n/a |
| plan | `--agent planner` | `read-only high` | n/a | `/plan` | chat | n/a |
| background | `thegent bg` | bg via wrapper | `autopilot --cd` | background-VM | n/a | wrapper |

## Dispatch

1. Validate arg compatibility (reject `model` when `provider=copilot`).
2. Map `mode` → provider-native mode.
3. Build argv per provider.
4. If `session=bg`, wrap in `thegent bg --owner "$THGENT_OWNER_TAG" --format json ...`.
5. Log the equivalent raw command for auditability.

## When NOT to use `thegent`

Reach for a provider-specific skill when you need:
- **codex-agent** — explicit `--reasoning` + sandbox tri-state control
- **copilot-agent** — guaranteed Claude Haiku 4.5 model lock
- **cursor-agent** — Composer slash commands, background-VM, IDE-only flows
- **gemini-agent** — multi-modal input, 1M-context repo-index, `/review`
- **forge-agent** — `--conversation` threading, native multi-provider routing

## Install

Copy to `~/.claude/skills/thegent/SKILL.md`. Requires `thegent` CLI on PATH
(see `thegent-skills` umbrella for orchestration semantics).

## Status

Draft v0. Implementation of the `thegent dispatch` CLI entrypoint pending
(Rust per Phenotype scripting policy). See `claude/thegent-unified-design.md`.
