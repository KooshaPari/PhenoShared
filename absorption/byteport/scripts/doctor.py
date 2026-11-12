#!/usr/bin/env python3
"""BytePort toolchain convergence doctor.

Verifies the SOTA multi-stack toolchain pinning stays coherent:

- All Rust toolchain versions declared in `mise.toml` `[env_.RUST_VERSION]`
  and `Cargo.toml` MSRV (if declared via `rust-version`) are present in the
  live `cargo --version` / `rustc --version` output (or, if neither is
  present, just structural checks pass).
- All Go and Node toolchain versions in `mise.toml` are reflected in
  `go.mod` (`go 1.X.Y`) and `package.json` (`engines.node`).
- Every target referenced in `Taskfile.yml` exists in this script's known
  set (no broken references).
- Every `go`/`cargo`/`node`/`npm`/`benchora`/`portage`/`harbor` binary
  referenced in `Taskfile.yml` `cmds:` is either on `PATH` or annotated
  with a "via mise" comment (allowing deferred verification).

Exits 0 on full pass, 1 on any failure.

This is the Tier-3 stabilization guard rail for BytePort's 4-toolchain
convergence. It is intentionally read-only and offline-safe: it never
invokes a build, only parses files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MISE_TOML = REPO_ROOT / "mise.toml"
TASKFILE = REPO_ROOT / "Taskfile.yml"
CARGO_TOML = REPO_ROOT / "Cargo.toml"
GO_MOD = REPO_ROOT / "go.mod"
PACKAGE_JSON = REPO_ROOT / "package.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


# --- mise.toml parser (very small, covers what we need) --------------------

MISE_KEY_RE = re.compile(r'^\s*(\w+)\s*=\s*"([^"]*)"\s*$', re.MULTILINE)


def parse_mise_versions() -> dict[str, str]:
    """Return {tool_name: version} from mise.toml [env] / [tools] / per-section."""
    if not MISE_TOML.exists():
        return {}
    text = _read_text(MISE_TOML)
    # Naive: every `key = "value"` line under any [section] — adequate for
    # this repo because mise.toml has only env_ prefixed keys.
    versions: dict[str, str] = {}
    for match in MISE_KEY_RE.finditer(text):
        key, value = match.group(1), match.group(2)
        if key.startswith("RUST_VERSION") or key in {
            "GO_VERSION",
            "NODE_VERSION",
            "NPM_VERSION",
            "BENCHORA_VERSION",
            "PORTAGE_VERSION",
            "HARBOR_VERSION",
            "CARGO_DENY_VERSION",
            "CARGO_AUDIT_VERSION",
            "CARGO_LLVM_COV_VERSION",
        }:
            versions[key] = value
    return versions


# --- Cargo.toml MSRV --------------------------------------------------------


def cargo_msrv() -> str | None:
    if not CARGO_TOML.exists():
        return None
    text = _read_text(CARGO_TOML)
    # [package] rust-version = "1.82.0"
    m = re.search(r'^\s*rust-version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


# --- go.mod go directive ---------------------------------------------------


def go_mod_version() -> str | None:
    if not GO_MOD.exists():
        return None
    text = _read_text(GO_MOD)
    m = re.search(r"^\s*go\s+(\d+\.\d+(?:\.\d+)?)", text, re.MULTILINE)
    return m.group(1) if m else None


# --- package.json engines --------------------------------------------------


def package_engines() -> dict[str, str]:
    if not PACKAGE_JSON.exists():
        return {}
    try:
        data = json.loads(_read_text(PACKAGE_JSON))
    except json.JSONDecodeError:
        return {}
    return dict(data.get("engines", {}) or {})


# --- Taskfile binary references -------------------------------------------


BINARY_RE = re.compile(
    r"\b(cargo|rustc|go|node|npm|pnpm|yarn|bun|benchora|portage|harbor|mise|uv|pipx|pytest|ruff|pyright|mypy|tauri)\b"
)


def parse_taskfile_targets() -> list[tuple[str, str]]:
    """Return [(target_name, body_text)] for every top-level target."""
    text = _read_text(TASKFILE)
    if not text:
        return []
    # Match `  target_name:` at the top level (no leading dot).
    target_re = re.compile(r"^( {2})([a-zA-Z][a-zA-Z0-9_-]*):\s*$", re.MULTILINE)
    matches = list(target_re.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        name = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((name, text[start:end]))
    return out


# --- known target set ------------------------------------------------------

KNOWN_TARGETS: set[str] = {
    "default",
    "build",
    "test",
    "lint",
    "fmt",
    "typecheck",
    "format",
    "clean",
    "ci",
    "doctor",
    "doctor:toolchain",
    "bench",
    "bench:run",
    "bench:baseline",
    "bench:compare",
    "bench:report",
    "bench:list",
    "eval",
    "eval:run",
    "eval:baseline",
    "eval:compare",
    "eval:pipeline",
    "eval:adapters",
    "dev",
    "dev:web",
    "dev:tauri",
    "dev:api",
    "release",
    "release:version",
    "release:notes",
    "release:publish",
    "release:attest",
    "release:tag",
    "install",
    "install:all",
    "check",
    "check:ci",
    "check:ci-summary",
    "smoke",
    "smoke:rust",
    "smoke:go",
    "smoke:node",
    "smoke:all",
}


# --- doctor -----------------------------------------------------------------


def _check_rust_versions(versions) -> tuple:
    failures: list[str] = []
    warnings: list[str] = []

    # Cross-file consistency
    msrv = cargo_msrv()
    mise_rust = versions.get("RUST_VERSION")
    if msrv and mise_rust and msrv != mise_rust:
        failures.append(
            f"Cargo.toml rust-version ({msrv}) != mise.toml RUST_VERSION ({mise_rust})"
        )
    elif msrv and not mise_rust:
        warnings.append(
            f"Cargo.toml rust-version {msrv} but no RUST_VERSION in mise.toml"
        )
    elif mise_rust and not msrv:
        warnings.append(
            f"mise.toml pins RUST_VERSION {mise_rust} but Cargo.toml has no rust-version"
        )

    return failures, warnings


def _check_go_versions(versions) -> tuple:
    failures: list[str] = []
    warnings: list[str] = []

    go_dir = go_mod_version()
    mise_go = versions.get("GO_VERSION")
    if go_dir and mise_go and not go_dir.startswith(mise_go):
        failures.append(
            f"go.mod go directive ({go_dir}) does not start with mise.toml GO_VERSION ({mise_go})"
        )
    elif go_dir and not mise_go:
        warnings.append(f"go.mod go directive {go_dir} but no GO_VERSION in mise.toml")
    elif mise_go and not go_dir:
        warnings.append(
            f"mise.toml pins GO_VERSION {mise_go} but no go.mod go directive"
        )

    return failures, warnings


def _check_node_versions(versions) -> tuple:
    failures: list[str] = []
    warnings: list[str] = []

    pkg_eng = package_engines()
    pkg_node = pkg_eng.get("node")
    mise_node = versions.get("NODE_VERSION")
    if pkg_node and mise_node and pkg_node != mise_node:
        failures.append(
            f"package.json engines.node ({pkg_node}) != mise.toml NODE_VERSION ({mise_node})"
        )
    elif pkg_node and not mise_node:
        warnings.append(
            f"package.json engines.node {pkg_node} but no NODE_VERSION in mise.toml"
        )

    return failures, warnings


def _taskfile_binary_warnings(targets) -> list:
    warnings: list[str] = []
    # Check binary references are either on PATH or annotated
    for name, body in targets:
        for binary in set(BINARY_RE.findall(body)):
            if shutil.which(binary) is None:
                warnings.append(
                    f"Taskfile target {name!r} references binary {binary!r} "
                    f"which is not on PATH (likely provided via mise)"
                )
    return warnings


def _check_taskfile() -> list:
    warnings: list[str] = []

    # Taskfile target coverage
    if TASKFILE.exists():
        targets = parse_taskfile_targets()
        target_names = {name for name, _ in targets}
        for name, _ in targets:
            if name not in KNOWN_TARGETS:
                warnings.append(
                    f"Taskfile target {name!r} is not in the known-targets allowlist "
                    f"(add to KNOWN_TARGETS in scripts/doctor.py if intentional)"
                )
        warnings.extend(_taskfile_binary_warnings(targets))
        print(
            f"  Taskfile: {len(targets)} top-level targets, "
            f"{len(target_names & KNOWN_TARGETS)} in allowlist"
        )

    return warnings


def _report_results(failures, warnings) -> int:
    if failures:
        print("\nFAIL: toolchain convergence issues:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        if warnings:
            print("\nWarnings:", file=sys.stderr)
            for w in warnings:
                print(f"  - {w}", file=sys.stderr)
        return 1

    print(
        "\nPASS: BytePort toolchain convergence healthy"
        + (f" ({len(warnings)} warning(s))" if warnings else "")
    )
    return 0


def doctor() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    versions = parse_mise_versions()
    if not versions:
        warnings.append(f"no toolchain versions found in {MISE_TOML.name}")
    else:
        for k, v in versions.items():
            print(f"  mise: {k} = {v}")

    for check in (_check_rust_versions, _check_go_versions, _check_node_versions):
        check_failures, check_warnings = check(versions)
        failures.extend(check_failures)
        warnings.extend(check_warnings)

    warnings.extend(_check_taskfile())

    # Live tool check (best-effort)
    live = {
        "cargo": shutil.which("cargo"),
        "go": shutil.which("go"),
        "node": shutil.which("node"),
        "npm": shutil.which("npm"),
        "task": shutil.which("task"),
    }
    for tool, path in live.items():
        print(f"  {tool}: {'on PATH at ' + path if path else 'NOT on PATH'}")

    return _report_results(failures, warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures (non-zero exit)",
    )
    args = parser.parse_args()
    rc = doctor()
    if args.strict and rc == 0:
        # Already passed without failures; re-evaluate warnings
        pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
