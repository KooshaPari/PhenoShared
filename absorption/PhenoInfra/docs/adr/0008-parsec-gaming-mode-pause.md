# ADR 0008 — Parsec Gaming-Mode Pause

- **Status:** Proposed (stub)
- **Date:** 2026-04-24

## Context (outline)

- Home Mac is a Woodpecker heavy runner (ADR 0003).
- Parsec gaming sessions need full CPU + GPU; CI jobs must yield.

## Decision (outline)

launchd-managed watcher:

1. Poll `pgrep -f Parsec.app` every 5 s.
2. If present, send `SIGSTOP` to the Woodpecker agent process.
3. On Parsec exit, send `SIGCONT`.
4. Expose a CLI flag `--force-pause` for manual override.

## Consequences (outline)

- Parsec sessions uninterrupted.
- Heavy jobs may queue for hours during long gaming; acceptable given solo-dev model.

## Alternatives (outline)

- `renice`-based soft yield — rejected: macOS scheduler doesn't respect nice values strongly enough for GPU contention.
- Cgroup-equivalent resource limits — rejected: macOS lacks cgroups.

## Related

- ADR 0003, `docs/runbooks/day1-home-runner-setup.md`

> **TODO:** Write the watcher (Rust preferred per scripting policy), define force-pause CLI.
