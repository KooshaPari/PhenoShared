# zz-merge-unk — destination TBD

This repo is pending merge into a target (TBD) after full forensic SSOT finalization and regression fixes.
All code is preserved. No new development here.

---

# zz-pause — Crash-recovery tool

This repo is on permanent pause. Code preserved for reference. No active development.
# Resume All source

Canonical source for the local `resume-all` crash-recovery, cross-host
session, telemetry, and operational-response toolkit.

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/resume-all/total)](https://github.com/KooshaPari/resume-all/releases)

The initial preservation commit imports only executable text sources plus the
matching LaunchAgent and non-secret configuration inputs. Runtime snapshots,
logs, credentials, cache state, rendered dashboards, and generated session
data are deliberately ignored.

## Layout

- `bin/`: command and wrapper sources.
- `launchd/`: `com.kooshapari.resume-all-*` job definitions.
- `config/`: declarative, non-secret runtime configuration.

This repository is preservation evidence, not a release claim. A future
promotion must validate each active entry point before replacing any live
local script with a tracked-source link.
