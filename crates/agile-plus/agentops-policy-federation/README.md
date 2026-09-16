Overview

This repository contains an early-stage "agentops policy federation" runtime manifest and a small set of wrapper scripts intended to act as policy enforcement hooks for Codex-style runtime agents. The project is intentionally lightweight: the current wrappers are simple pass-through guards. Use this repo as a scaffold for adding real policy checks (exec/write/network) and integrating them with the agent runtime.

Scripts

- scripts/runtime/codex_runtime_manifest.json
  - JSON manifest describing the runtime "wrappers" used by this project. Current mode: "fallback-pass-through".

- scripts/runtime/codex_exec_guard.sh
  - Exec wrapper. Presently a no-op guard that exits immediately when called without arguments, otherwise execs the given command. Marked executable.

- scripts/runtime/codex_write_guard.sh
  - Write-check wrapper. Currently a no-op pass-through with the same behavior as the exec guard. Intended to be replaced with write-permission checks.

- scripts/runtime/codex_network_guard.sh
  - Network-check wrapper. Currently a no-op pass-through. Intended to be replaced with network egress/ingress policy checks.

Development

- All new work must follow the AgilePlus workflow and be tracked in AgilePlus specs before implementing.
- Scripts are POSIX shell; keep changes small and test locally. To run a wrapper locally:
    sh scripts/runtime/codex_exec_guard.sh -- echo hello
  or make it executable and invoke directly.
- Update the manifest at scripts/runtime/codex_runtime_manifest.json to register new wrappers or change the mode.
- Follow the workspace's documentation and linting rules (UTF-8, Vale/markdown rules) when adding docs.

Status

- Early-stage / scaffold: wrappers are currently pass-through/no-op guards.
- No CI or tests in this repo yet. Consider adding basic shellcheck / CI job in a future PR.
- Files of interest (absolute paths):
  - /Users/<REDACTED>/CodeProjects/Phenotype/repos/agentops-policy-federation/scripts/runtime/codex_runtime_manifest.json
  - /Users/<REDACTED>/CodeProjects/Phenotype/repos/agentops-policy-federation/scripts/runtime/codex_exec_guard.sh
  - /Users/<REDACTED>/CodeProjects/Phenotype/repos/agentops-policy-federation/scripts/runtime/codex_write_guard.sh
  - /Users/<REDACTED>/CodeProjects/Phenotype/repos/agentops-policy-federation/scripts/runtime/codex_network_guard.sh

If you'd like, I can:
- Add simple shellcheck-driven tests and a lightweight GitHub Actions workflow (note: Actions billing constraints may apply),
- Expand one of the guards into a real policy (example: restrict network access to a whitelist), or
- Move documentation into docs/ with a quick development checklist.
