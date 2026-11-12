#!/usr/bin/env python3
"""Regenerates crates/README.md's crate index from the workspace manifests.

The previous file was hand-maintained and had drifted: it named far fewer crates
than the workspace publishes. This derives the list from the manifests directly
so the index cannot silently fall behind again.

It reads the manifests with the standard library instead of shelling out to
`cargo metadata`. Spawning a process bought nothing that `tomllib` cannot do -
members, exclude and publish are plain TOML - and it cost three Bandit findings
(B404/B603/B607) on a repo-wide lint gate. Reading files keeps that gate
meaningful instead of silenced.

Which crates are listed: the workspace members, plus the path dependencies they
reach transitively (inline `{ path = ... }` entries and `{ workspace = true }`
entries resolved through [workspace.dependencies]). Anything under
[workspace.exclude] is skipped, because cargo skips it too.

A crate is "publishable" when [package].publish is absent, or present and not
false and not the empty list. An inherited `publish.workspace = true` resolves
to [workspace.package].publish.

The table is emitted already padded to its column widths, which is the layout
Prettier produces for Markdown tables, so the file this writes is also the file
the formatter gate expects and regenerating never shows up as a format diff.

Requires Python 3.11+ for `tomllib`.
"""

import pathlib
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - depends on the interpreter
    sys.exit("crates/README.md generation needs Python 3.11+ (tomllib)")

root = pathlib.Path(__file__).resolve().parent.parent
SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")


def load(directory):
    with open(directory / "Cargo.toml", "rb") as fh:
        return tomllib.load(fh)


def expand(patterns):
    """Expand workspace member/exclude entries, which may be globs."""
    found = []
    for pattern in patterns:
        matches = sorted(root.glob(pattern)) if "*" in pattern else [root / pattern]
        found.extend(p.resolve() for p in matches if (p / "Cargo.toml").is_file())
    return found


def dep_tables(manifest):
    for section in SECTIONS:
        yield manifest.get(section) or {}
    for target in (manifest.get("target") or {}).values():
        for section in SECTIONS:
            yield target.get(section) or {}


def path_deps(manifest, base, workspace_deps):
    """Directories this manifest pulls in as path dependencies."""
    for table in dep_tables(manifest):
        for name, spec in table.items():
            if not isinstance(spec, dict):
                continue
            if "path" in spec:
                yield (base / spec["path"]).resolve()
            elif spec.get("workspace"):
                inherited = workspace_deps.get(name)
                if isinstance(inherited, dict) and "path" in inherited:
                    yield (root / inherited["path"]).resolve()


def publishable(package, workspace_publish):
    publish = package.get("publish")
    if isinstance(publish, dict):
        if not publish.get("workspace"):
            return True
        publish = workspace_publish
    if publish is None:
        return True
    if publish is False:
        return False
    return not (isinstance(publish, list) and not publish)


workspace = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]
workspace_deps = workspace.get("dependencies") or {}
workspace_publish = workspace.get("package", {}).get("publish")
excluded = set(expand(workspace.get("exclude", [])))

crates = {}
queue = expand(workspace.get("members", []))
while queue:
    directory = queue.pop()
    if (
        directory in crates
        or directory in excluded
        or not (directory / "Cargo.toml").is_file()
    ):
        continue
    manifest = load(directory)
    crates[directory] = manifest
    queue.extend(
        p for p in path_deps(manifest, directory, workspace_deps) if root in p.parents
    )

rows = []
for directory, manifest in crates.items():
    package = manifest.get("package") or {}
    if not package.get("name") or not publishable(package, workspace_publish):
        continue
    rows.append((package["name"], str(directory.relative_to(root))))
rows.sort()

table = [("Crate", "Path")] + [(f"`{n}`", f"`{p}`") for n, p in rows]
widths = [max(len(cell[i]) for cell in table) for i in range(2)]


def render(cells, fill=None):
    padded = [
        fill * widths[i] if fill else c.ljust(widths[i]) for i, c in enumerate(cells)
    ]
    return "| " + " | ".join(padded) + " |"


lines = [
    "# Crates",
    "",
    "Generated index of every publishable crate in this workspace.",
    "Do not hand-edit: regenerate with `python3 scripts/gen-crates-readme.py`.",
    "",
    f"Total publishable crates: **{len(rows)}**",
    "",
    render(table[0]),
    render(table[0], fill="-"),
]
lines.extend(render(cells) for cells in table[1:])
(root / "crates" / "README.md").write_text("\n".join(lines) + "\n")
print(f"wrote crates/README.md with {len(rows)} crates")
