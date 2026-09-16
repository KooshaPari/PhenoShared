#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG_PATH="${1:-$ROOT_DIR/pheno-agents-md.yaml}"
OUTPUT_PATH="${2:-$ROOT_DIR/AGENTS.md}"
DEFAULT_REPO_NAME="${3:-$(basename "$ROOT_DIR")}"

python3 - "$CONFIG_PATH" "$OUTPUT_PATH" "$DEFAULT_REPO_NAME" <<"PY"
from __future__ import annotations

import sys
from pathlib import Path

config_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
default_repo_name = sys.argv[3]

defaults = {
    "build": "cargo build",
    "test": "cargo test",
    "lint": "cargo clippy -- -D warnings",
    "audit": "cargo deny check",
    "sign": "cosign sign",
    "repo_name": default_repo_name,
    "extra_dont_touch": [],
}

if config_path.exists():
    current_list = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if current_list and line.startswith("  - "):
            defaults["extra_dont_touch"].append(line[4:].strip())
            continue
        current_list = None
        if line.startswith("extra_dont_touch:"):
            current_list = "extra_dont_touch"
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip(').strip(")
            if key in defaults and key != "extra_dont_touch" and value:
                defaults[key] = value

extra = ""
if defaults["extra_dont_touch"]:
    extra = "\nCustom zones:\n" + "\n".join(
        "- `" + zone + "` (custom)" for zone in defaults["extra_dont_touch"]
    )

body = (
    "# " + defaults["repo_name"] + " — AGENTS.md (Agent Constitution)\n\n"
    "## Build & test\n"
    "- Build:  `" + defaults["build"] + "`\n"
    "- Test:   `" + defaults["test"] + "`\n"
    "- Lint:   `" + defaults["lint"] + "`\n"
    "- Audit:  `" + defaults["audit"] + "`\n"
    "- Sign:   `" + defaults["sign"] + "`\n\n"
    "## Conventions\n"
    "- Commits: Conventional Commits (feat/fix/docs/style/refactor/perf/test/chore)\n"
    "- Branch:  `<layer>/<slug>-<YYYY-MM-DD>`\n"
    "- WORKLOG: append 1 row to `WORKLOG.md` per V4 DAG task ID\n"
    "- PRs:     reference V4 task ID in body\n\n"
    "## Do-not-touch zones\n"
    "- `<archive>/` (stale work, archived intentionally)\n"
    "- `<vendor>/`, `<node_modules>/` (third-party)\n"
    "- `**/.git`, `**/Cargo.lock` (unless explicitly updating deps)\n"
    "- files marked `# DO NOT EDIT` header" + extra + "\n\n"
    "## Ownership\n"
    "- See `CODEOWNERS` (GitHub) — agents should not self-approve PRs\n"
    "- Last 5 contributors: `git shortlog -sn | head -5`\n\n"
    "## References\n"
    "- DAG: `FLEET_100TASK_DAG_V4.md` (or V5/V6/... — pick the current one)\n"
    "- Worklog schema: `pheno-worklog-schema` (lib)\n"
    "- llms.txt: see `pheno-llms-txt`\n"
)

output_path.write_text(body, encoding="utf-8")
print("wrote " + str(output_path))
PY
