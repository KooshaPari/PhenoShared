# PROVENANCE.md -- herdr-helioslite Absorption

## Source Repository

- **Repository**: `KooshaPari/herdr-helioslite`
- **URL**: `https://github.com/KooshaPari/herdr-helioslite.git`
- **Commit**: `93b98a8cc96d694a1ab18294cb83cfca50d987bd`
- **Commit message**: `fix(herdr-helioslite): emit pane.report_agent via herdr pane subcommand`
- **Commit date**: 2026-09-19
- **Absorbed**: 2026-09-27

## What Was Absorbed

A Herdr plugin for [HeliosLite](https://github.com/KooshaPari/HeliosLite) —
presence and lifecycle reporting for the stock HeliosLite CLI, no fork required.

Files:

- `herdr-plugin.toml` -- canonical Herdr v1 plugin manifest (`kooshapari.herdr-helioslite`)
- `agent-detection/helioslite.toml` -- screen-rule fallback detection
- `bin/herdr-helioslite-report` -- wrapper/doctor entrypoint
- `install.sh` / `uninstall.sh` -- local install companions (relocatable)
- `README.md`, `docs/HERDR_VS_ACP.md` -- docs

## Relationship to Existing Code

Companion to `absorption/herdr-jcode` and `absorption/herdr-forgecode` — the
three share an identical layout and reporting approach across harnesses.

## Notes

- Absorbed as a plain copy (no `.git` history), matching the `absorption/*` pattern.
- The live local Herdr plugin link was re-pointed from `~/wt-herdr-helioslite` to
  `absorption/herdr-helioslite/` as part of this consolidation.
- Runtime `state/` artifacts (if any) were deliberately excluded.

## Source Repo Status

- Standalone repo retained (archived/deletion is a separate, approval-gated step).
