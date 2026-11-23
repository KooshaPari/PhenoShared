# Provenance: herdr-revive-hc

Patched fork of [`cantona/herdr-revive`](https://github.com/cantona/herdr-revive),
vendored into PhenoShared so Heardr-core (HC) layouts can restore exact
`jcode`/`kcode` conversations and so the crate builds on native Windows.

| Field | Value |
|---|---|
| Upstream | `https://github.com/cantona/herdr-revive` |
| Upstream tag | `v0.3.1` |
| Upstream commit | `9854631bb6bbea1b64b951a0b6396b50ad42c5a5` |
| Upstream author | Su Kang Yin <paradyse@gmail.com> |
| Upstream license | Apache-2.0 (see `LICENSE`, `THIRD_PARTY_NOTICES.md`) |
| Fork version | `0.3.1-hc.1` |
| Package name | `herdr-revive-hc` |
| Binary name | `herdr-revive` (unchanged: upstream's shell hook and docs resolve it by this name) |

The vendored files are the upstream tag verbatim except for the changes below.
Every upstream `SPDX-FileCopyrightText` / `SPDX-License-Identifier` header is
kept. Apache-2.0 permits redistribution and modification provided the license,
notices and any modified-file statements are preserved; `LICENSE`,
`THIRD_PARTY_NOTICES.md` and the repository `NOTICE` cover that obligation.

## Changes against upstream v0.3.1

1. **Package identity** (`Cargo.toml`): package renamed to `herdr-revive-hc`,
   version `0.3.1-hc.1`, explicit `[[bin]] name = "herdr-revive"` and
   `[lib] name = "herdr_revive"`, plus a `[package.metadata.fork]` block naming
   the upstream repository, tag and commit. The upstream `repository` field and
   `authors` are untouched.

2. **jcode / kcode agent kinds** (`src/model.rs`): `AgentKind::{Jcode, Kcode}`
   added to the enum, `ALL`, `name()`, `executable()`, `agent_launcher()` and the
   `agent_extra_args` key allowlist. Resume argv falls through to the existing
   `--resume <id>` arm, which is the real syntax on both harnesses:

   ```
   jcode v1.0.3   --resume [<RESUME>] Resume a session by ID, or list sessions if no ID provided
   kcode v0.93.458-k0.1.0-dev  --resume [<RESUME>]  (no `resume` subcommand exists)
   ```

3. **Native Windows platform module** (`src/platform/windows.rs` plus the
   `#[cfg(windows)]` re-export in `src/platform.rs`). Upstream re-exported only
   `linux` and `macos`, so the crate did not compile for Windows at all. The new
   module makes the crate build and run the commands that never inspect another
   process (`status`, `config`, `init`, `uninstall`, snapshot listing). Capture
   and restore need another process's argv, cwd, environment and stdio, which
   needs NT APIs this fork does not implement; those entry points refuse with an
   explicit reason instead of capturing a wrong snapshot. No Windows restore
   parity is claimed.

No upstream behaviour for `claude`, `codex`, `gemini`, `copilot` or `cursor` is
changed.

## Re-syncing from upstream

Re-fetch the tag, re-apply the three changes above, refresh
`upstream_rev`/`upstream_tag` in `Cargo.toml`, and re-run
`cargo test -p herdr-revive-hc`.
