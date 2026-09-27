# PROVENANCE.md -- herdr-jcode Absorption

## Source Repository

- **Repository**: `KooshaPari/herdr-jcode`
- **URL**: `https://github.com/KooshaPari/herdr-jcode.git`
- **Commit**: `ab145f91d0786e54243a94fcf342bb9d5e120db1`
- **Commit message**: `feat: initial herdr-jcode plugin (manifest + scripts + docs)`
- **Commit date**: 2026-09-20
- **Absorbed**: 2026-09-27

## What Was Absorbed

A Herdr plugin that reports lifecycle and session presence from the stock
[Jcode](https://github.com/KooshaPari/KCode) CLI to the Herdr daemon. No fork of
Jcode is required — the plugin wraps the stock `jcode` binary and emits
`pane.report_agent` / `pane.report_agent_session` calls over the Herdr socket.

Files:

- `herdr-plugin.toml` -- canonical Herdr v1 plugin manifest (`kooshapari.herdr-jcode`)
- `agent-detection/jcode.toml` -- screen-rule fallback detection for stock builds
- `bin/herdr-jcode-report` -- wrapper/doctor/session reporting entrypoint
- `install.sh` / `uninstall.sh` -- local install companions (relocatable, `SCRIPT_DIR`-relative)
- `README.md`, `docs/HERDR_VS_ACP.md` -- docs

## Relationship to Existing Code

Jcode itself reports natively through its in-tree `jcode-herdr` crate (socket
`pane.report_agent`). This plugin covers stock upstream builds and manual
lifecycle driving, and registers `jcode` in Herdr's agent-detection rules.

## Notes

- Absorbed as a plain copy (no `.git` history), matching the existing
  `absorption/*` pattern in this workspace.
- Scripts are fully relocatable: they resolve paths via `SCRIPT_DIR` and Herdr
  env vars (`HERDR_CONFIG_DIR`, `HERDR_DATA_DIR`), with no hardcoded paths.
- The live local Herdr plugin link was re-pointed from `~/wt-herdr-jcode` to
  `absorption/herdr-jcode/` as part of this consolidation.
- Runtime `state/` artifacts (if any) were deliberately excluded.

## Source Repo Status

- Standalone repo retained (archived/deletion is a separate, approval-gated step).
