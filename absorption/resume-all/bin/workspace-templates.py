#!/opt/homebrew/bin/python3
"""
workspace-templates.py — Phase E hardening item E14.

Defines named workspace templates that group panes by purpose (e.g.,
"rust-dev" = cargo + neovim + ripgrep panes), and provides commands to
apply templates to the current snapshot.

Templates live in `~/.config/resume-all/workspace-templates.toml`:

    [templates.rust-dev]
    description = "Rust development environment"
    panes = ["cargo", "neovim", "ripgrep", "rust-analyzer"]
    cwd = "~/CodeProjects/..."
    harnesses = ["codex", "droid"]

    [templates.data-eng]
    description = "Data engineering stack"
    panes = ["jupyter", "duckdb", "dbt"]

Usage:
    workspace-templates.py list
    workspace-templates.py show <name>
    workspace-templates.py apply <name> [--dry-run]
    workspace-templates.py current
    workspace-templates.py add <name> --panes "pane1,pane2" --cwd PATH
    workspace-templates.py remove <name>
    workspace-templates.py test
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "resume-all"
TEMPLATES_FILE = CONFIG_DIR / "workspace-templates.toml"
SNAPSHOT_DIR = HOME / ".local" / "share" / "resume-all"
CURRENT_FILE = SNAPSHOT_DIR / "current-workspace.json"
VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")

BUILTIN_TEMPLATES = {
    "default": {
        "description": "Default workspace — all panes",
        "panes": [],
        "cwd": None,
        "harnesses": [],
    },
    "rust-dev": {
        "description": "Rust development environment",
        "panes": ["cargo", "rustc", "neovim", "nvim", "ripgrep", "rg",
                  "rust-analyzer"],
        "cwd": None,
        "harnesses": ["codex", "droid", "cursor"],
    },
    "data-eng": {
        "description": "Data engineering stack",
        "panes": ["jupyter", "duckdb", "dbt", "pandas", "polars"],
        "cwd": None,
        "harnesses": [],
    },
    "web-dev": {
        "description": "Web development",
        "panes": ["vite", "node", "npm", "pnpm", "next", "deno"],
        "cwd": None,
        "harnesses": [],
    },
    "ai-ml": {
        "description": "AI/ML stack",
        "panes": ["python", "jupyter", "torch", "transformers", "ollama"],
        "cwd": None,
        "harnesses": ["droid", "codex"],
    },
}


# ---------------------------------------------------------------------------
# TOML parser (minimal)
# ---------------------------------------------------------------------------


def _toml_load(path: Path) -> dict:
    """Minimal TOML reader for [templates.<name>] sections."""
    if not path.exists():
        return {}
    templates = defaultdict(lambda: {"panes": [], "cwd": None, "harnesses": [],
                                     "description": ""})
    current_template = None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Section: [templates.name] or [templates.name.subkey]
        if stripped.startswith("["):
            inner = stripped.strip("[]").strip()
            if inner.startswith("templates."):
                current_template = inner[len("templates."):].split(".")[0]
                if current_template not in templates:
                    templates[current_template] = {
                        "panes": [], "cwd": None,
                        "harnesses": [], "description": "",
                    }
            continue
        if current_template is None or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip inline comments
        if value.startswith('"'):
            end = value.find('"', 1)
            if end > 0:
                value = value[1:end]
        elif "#" in value:
            value = value.split("#", 1)[0].strip()
        # Type coercion
        if value.startswith("[") and value.endswith("]"):
            # List literal: ["a", "b"]
            inner = value[1:-1].strip()
            items = []
            if inner:
                for part in _split_list(inner):
                    part = part.strip().strip('"').strip("'")
                    if part:
                        items.append(part)
            templates[current_template][key] = items
        elif value.startswith('"') and value.endswith('"'):
            templates[current_template][key] = value[1:-1]
        elif value.lower() == "true":
            templates[current_template][key] = True
        elif value.lower() == "false":
            templates[current_template][key] = False
        elif value.lower() == "none" or value == "":
            templates[current_template][key] = None
        else:
            templates[current_template][key] = value
    return dict(templates)


def _split_list(s: str) -> list[str]:
    """Split a TOML list body by comma, respecting quotes."""
    out = []
    buf = []
    in_quote = False
    quote_char = None
    for c in s:
        if c in ('"', "'") and (not buf or buf[-1] != "\\"):
            in_quote = not in_quote
            quote_char = c if in_quote else None
            buf.append(c)
        elif c == "," and not in_quote:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    if buf:
        out.append("".join(buf))
    return out


def _toml_dump(path: Path, templates: dict) -> str:
    """Write templates to a TOML file."""
    lines = []
    for name, t in sorted(templates.items()):
        lines.append(f"[templates.{name}]")
        if t.get("description"):
            escaped = t["description"].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'description = "{escaped}"')
        if t.get("panes"):
            items = ", ".join(f'"{p}"' for p in t["panes"])
            lines.append(f"panes = [{items}]")
        if t.get("harnesses"):
            items = ", ".join(f'"{h}"' for h in t["harnesses"])
            lines.append(f"harnesses = [{items}]")
        if t.get("cwd"):
            lines.append(f'cwd = "{t["cwd"]}"')
        lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.rename(path)


def _load_templates() -> dict:
    """Load templates: file overrides builtins."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATES_FILE.exists():
        return dict(BUILTIN_TEMPLATES)
    file_templates = _toml_load(TEMPLATES_FILE)
    merged = dict(BUILTIN_TEMPLATES)
    merged.update(file_templates)
    return merged


def _save_templates(templates: dict) -> None:
    _atomic_write(TEMPLATES_FILE, _toml_dump(TEMPLATES_FILE, templates))


# ---------------------------------------------------------------------------
# Snapshot filtering
# ---------------------------------------------------------------------------


def filter_snapshot(snapshot_path: Path, template: dict) -> list[dict]:
    """Return rows from snapshot.jsonl matching the template."""
    if not snapshot_path.exists():
        return []
    pane_patterns = [p.lower() for p in template.get("panes", [])]
    harnesses = set(template.get("harnesses", []))
    cwd_filter = template.get("cwd")

    matched = []
    for line in snapshot_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue

        argv = (r.get("argv", "") or "").lower()
        cwd = r.get("cwd", "") or ""
        harness = r.get("harness", "")

        # Pane pattern match (any)
        pane_match = (not pane_patterns
                      or any(p in argv for p in pane_patterns))
        # Harness match
        harness_match = (not harnesses or harness in harnesses)
        # Cwd match
        cwd_match = (not cwd_filter or cwd_filter in cwd)

        if pane_match and harness_match and cwd_match:
            matched.append(r)
    return matched


def write_current(name: str, matches: list[dict]) -> None:
    """Persist current workspace selection."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.write_text(json.dumps({
        "name": name,
        "applied_at": time.time(),
        "applied_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "row_count": len(matches),
        "row_ids": [r.get("pane_id", "?") for r in matches],
    }, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    templates = _load_templates()
    if not templates:
        print("No templates defined.")
        return 0
    print(f"{'NAME':20s} {'PANES':30s} {'HARNESSES':20s} DESCRIPTION")
    print(f"{'-'*20} {'-'*30} {'-'*20} -----------")
    for name, t in sorted(templates.items()):
        panes = ",".join(t.get("panes", []))[:30]
        harnesses = ",".join(t.get("harnesses", []))[:20]
        desc = t.get("description", "")
        print(f"{name:20s} {panes:30s} {harnesses:20s} {desc}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    templates = _load_templates()
    if args.name not in templates:
        print(f"unknown template: {args.name}")
        return 1
    t = templates[args.name]
    print(f"[{args.name}]")
    print(f"  description: {t.get('description', '')}")
    print(f"  panes:       {t.get('panes', [])}")
    print(f"  harnesses:   {t.get('harnesses', [])}")
    print(f"  cwd:         {t.get('cwd')}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    templates = _load_templates()
    if args.name not in templates:
        print(f"unknown template: {args.name}")
        return 1
    snapshot = Path(args.snapshot or str(SNAPSHOT_DIR / "snapshot.jsonl"))
    template = templates[args.name]
    matches = filter_snapshot(snapshot, template)
    if args.dry_run:
        print(f"[dry-run] would apply '{args.name}' -> {len(matches)} panes")
        return 0
    write_current(args.name, matches)
    print(f"Applied '{args.name}' -> {len(matches)} panes "
          f"(written to {CURRENT_FILE})")
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    if not CURRENT_FILE.exists():
        print("No workspace currently applied.")
        return 0
    data = json.loads(CURRENT_FILE.read_text())
    print(f"Current workspace: {data.get('name')}")
    print(f"  Applied at:   {data.get('applied_at_iso')}")
    print(f"  Row count:    {data.get('row_count')}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    if not VALID_NAME.match(args.name):
        print(f"invalid name: {args.name} (must match [a-z][a-z0-9_-]*)")
        return 1
    templates = _load_templates()
    panes = [p.strip() for p in args.panes.split(",") if p.strip()]
    harnesses = [h.strip() for h in (args.harnesses or "").split(",") if h.strip()]
    templates[args.name] = {
        "description": args.description or f"Custom: {args.name}",
        "panes": panes,
        "cwd": args.cwd or None,
        "harnesses": harnesses,
    }
    _save_templates(templates)
    print(f"Added template: {args.name}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    templates = _load_templates()
    if args.name not in templates:
        print(f"unknown template: {args.name}")
        return 1
    if args.name in BUILTIN_TEMPLATES:
        print(f"cannot remove builtin template: {args.name}")
        print("(rename or override in TOML instead)")
        return 1
    del templates[args.name]
    _save_templates(templates)
    print(f"Removed: {args.name}")
    return 0


def _self_test() -> tuple[int, int]:
    passed = 0
    total = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}")

    print("=== workspace-templates.py self-tests ===")

    # Test 1: builtin templates loaded
    templates = _load_templates()
    check("default template loaded", "default" in templates)
    check("rust-dev template loaded", "rust-dev" in templates)
    check("data-eng template loaded", "data-eng" in templates)

    # Test 2: name validation
    check("valid name 'foo-bar'", VALID_NAME.match("foo-bar") is not None)
    check("valid name 'rust_dev'", VALID_NAME.match("rust_dev") is not None)
    check("invalid 'Foo'", VALID_NAME.match("Foo") is None)
    check("invalid 'foo;bar'", VALID_NAME.match("foo;bar") is None)

    # Test 3: TOML round-trip
    tmp = SNAPSHOT_DIR / ".workspace-test.toml"
    try:
        test_data = {
            "my-template": {
                "description": "Test template",
                "panes": ["cargo", "neovim"],
                "harnesses": ["codex"],
                "cwd": "/tmp",
            },
        }
        content = _toml_dump(tmp, test_data)
        tmp.write_text(content)
        loaded = _toml_load(tmp)
        check("TOML round-trip description",
              loaded.get("my-template", {}).get("description") == "Test template")
        check("TOML round-trip panes",
              loaded.get("my-template", {}).get("panes") == ["cargo", "neovim"])
        check("TOML round-trip harnesses",
              loaded.get("my-template", {}).get("harnesses") == ["codex"])
    finally:
        if tmp.exists():
            tmp.unlink()

    # Test 4: snapshot filter
    sample_snapshot = SNAPSHOT_DIR / ".workspace-test.jsonl"
    try:
        sample_snapshot.write_text(
            json.dumps({"argv": "cargo build", "harness": "codex",
                        "cwd": "/proj", "pane_id": "p1"}) + "\n"
            + json.dumps({"argv": "ls", "harness": "shell",
                          "cwd": "/", "pane_id": "p2"}) + "\n"
            + json.dumps({"argv": "neovim", "harness": "droid",
                          "cwd": "/proj/src", "pane_id": "p3"}) + "\n"
        )
        rust_matches = filter_snapshot(
            sample_snapshot,
            {"panes": ["cargo", "neovim"], "harnesses": [], "cwd": None},
        )
        check("filter matches cargo + neovim", len(rust_matches) == 2)

        shell_matches = filter_snapshot(
            sample_snapshot,
            {"panes": [], "harnesses": ["shell"], "cwd": None},
        )
        check("filter matches harness=shell only", len(shell_matches) == 1)

        cwd_matches = filter_snapshot(
            sample_snapshot,
            {"panes": [], "harnesses": [], "cwd": "/proj"},
        )
        check("filter matches cwd=/proj", len(cwd_matches) == 2)
    finally:
        if sample_snapshot.exists():
            sample_snapshot.unlink()

    # Test 5: builtin template structure
    rust = templates.get("rust-dev", {})
    check("rust-dev has panes", len(rust.get("panes", [])) > 0)
    check("rust-dev has harnesses", len(rust.get("harnesses", [])) > 0)
    check("rust-dev has description", bool(rust.get("description")))

    # Test 6: empty filter returns all
    default_matches = filter_snapshot(
        Path("/tmp/nonexistent.jsonl"),
        {"panes": [], "harnesses": [], "cwd": None},
    )
    check("empty filter on missing file = 0", default_matches == [])

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list").set_defaults(func=cmd_list)

    p_show = sub.add_parser("show")
    p_show.add_argument("name")
    p_show.set_defaults(func=cmd_show)

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("name")
    p_apply.add_argument("--snapshot", help="Override snapshot path")
    p_apply.add_argument("--dry-run", action="store_true")
    p_apply.set_defaults(func=cmd_apply)

    sub.add_parser("current").set_defaults(func=cmd_current)

    p_add = sub.add_parser("add")
    p_add.add_argument("name")
    p_add.add_argument("--panes", required=True,
                       help="Comma-separated pane patterns")
    p_add.add_argument("--harnesses", default="",
                       help="Comma-separated harness names")
    p_add.add_argument("--cwd", help="Filter by CWD substring")
    p_add.add_argument("--description", help="Human description")
    p_add.set_defaults(func=cmd_add)

    p_remove = sub.add_parser("remove")
    p_remove.add_argument("name")
    p_remove.set_defaults(func=cmd_remove)

    sub.add_parser("test").set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv[1:])
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
