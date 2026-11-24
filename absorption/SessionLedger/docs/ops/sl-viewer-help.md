# sl-viewer CLI help (C01/C09 DX)

<!-- Blocking sl-viewer-help-hard CI workflow | **done** -->
<!-- Fluent i18n migration for help text | **unpaid** -->

Status: **C01/C09** — expands `sl-viewer --help` / `--version` beyond a one-line
usage stub and documents `SL_DAEMON_URL`, `FORGE_DB`, and in-viewer doc
cross-links.

Machine proof: `pwsh ./scripts/sl-viewer-help-check.ps1 -SelfCheck`.

Policy manifest: [`sl-viewer-help.json`](sl-viewer-help.json).

Related: [`crates/sl-viewer/src/cli_help.rs`](../../crates/sl-viewer/src/cli_help.rs),
[`crates/sl-viewer/src/main.rs`](../../crates/sl-viewer/src/main.rs),
[`docs/HELP.md`](../HELP.md),
[`.github/workflows/sl-viewer-help-hard.yml`](../../.github/workflows/sl-viewer-help-hard.yml).

## CLI

| Flag               | Output                                                       |
| ------------------ | ------------------------------------------------------------ |
| `--help` / `-h`    | Usage, environment variables, in-viewer shortcuts, doc links |
| `--version` / `-V` | Package version + resolved compile-time daemon URL           |

Implementation: [`cli_help.rs`](../../crates/sl-viewer/src/cli_help.rs).

## Environment variables

| Variable         | When         | Purpose                                           | Source                                                      |
| ---------------- | ------------ | ------------------------------------------------- | ----------------------------------------------------------- |
| `SL_DAEMON_URL`  | compile-time | Daemon HTTP base for Search / Live / Replay tabs  | [`daemon_url.rs`](../../crates/sl-viewer/src/daemon_url.rs) |
| `FORGE_DB`       | runtime      | Path to Forge SQLite corpus (`--features sqlite`) | [`app.rs`](../../crates/sl-viewer/src/app.rs)               |
| `SL_VIEWER_DEMO` | runtime      | Force in-memory demo data on desktop              | [`app.rs`](../../crates/sl-viewer/src/app.rs)               |

See also [`.env.example`](../../.env.example) (`FORGE_DB`, `SL_DAEMON_URL`).

## How to run

### SelfCheck (hermetic)

```powershell
pwsh ./scripts/sl-viewer-help-check.ps1 -SelfCheck
```

### Local CLI smoke

```bash
cargo run -p sl-viewer -- --help
cargo run -p sl-viewer -- --version
```

Unit tests: `cargo test -p sl-viewer cli_help --locked`.

## CI / scheduling

| Gate       | Workflow                  | Mode         | Evidence                                 |
| ---------- | ------------------------- | ------------ | ---------------------------------------- |
| SelfCheck  | `sl-viewer-help-hard.yml` | **blocking** | Docs + `cli_help.rs` / `main.rs` anchors |
| Unit tests | `sl-viewer-help-hard.yml` | **blocking** | `cargo test -p sl-viewer cli_help`       |

### Done / unpaid

| Item                                     | Status                        |
| ---------------------------------------- | ----------------------------- |
| Policy SSOT + JSON manifest              | **done**                      |
| Expanded `--help` / `--version`          | **done**                      |
| `SL_DAEMON_URL` + `FORGE_DB` documented  | **done**                      |
| Blocking sl-viewer-help-hard CI workflow | **done**                      |
| `tests/sl_viewer_help.rs` cargo wrapper  | **done**                      |
| Fluent i18n migration for help text      | **unpaid** — C01 L16 residual |
