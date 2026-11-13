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

Each row also carries a one-line description, taken from the crate's own
metadata and never invented: its [package].description (with an inherited
`description.workspace = true` resolved through [workspace.package]), else the
first prose line of the crate's own README, else a placeholder. A description
longer than MAX_DESCRIPTION characters is elided at a word boundary, so the
table stays readable. The text is normalised to the form Prettier keeps stable
- single-spaced, with `|` and `*` escaped - so regenerating never shows up as a
format diff.

The table is emitted already padded to its column widths, which is the layout
Prettier produces for Markdown tables, so the file this writes is also the file
the formatter gate expects.

Requires Python 3.11+ for `tomllib`.

Pass `--check` to verify without writing: it renders the index in memory and
compares it against the committed `crates/README.md`, exiting 1 when the file is
stale. That is what the `crates-index-regen` workflow runs, so the index cannot
fall behind the manifests again without a red gate.
"""

import pathlib
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - depends on the interpreter
    sys.exit(
        "crates/README.md generation needs Python 3.11+ (tomllib).\n"
        f"This interpreter is {sys.version.split()[0]}. Run the script with a "
        "newer one, for example:\n"
        "    python3.12 scripts/gen-crates-readme.py"
    )

root = pathlib.Path(__file__).resolve().parent.parent
SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")
README_NAMES = ("README.md", "README", "README.rst", "README.txt")
MISSING = "—"
MAX_DESCRIPTION = 140


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


def normalise(text):
    """Collapse whitespace and escape the characters Markdown tables need.

    `|` ends a table cell, `*` opens emphasis and `<` opens what a Markdown
    linter reads as inline HTML. Escaping all three keeps the row a row and
    keeps the linter and the formatter both quiet.
    """
    text = " ".join(text.split())
    return text.replace("|", r"\|").replace("*", r"\*").replace("<", r"\<")


def elide(text, limit=MAX_DESCRIPTION):
    """Cut a long description at a word boundary and mark it as cut."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.-") + "…"


def same_title(text, name):
    """True when a README title is just the crate's own name."""

    def key(value):
        return "".join(c for c in value.lower() if c.isalnum())

    return key(text) == key(name)


def readme_description(directory, name):
    """The first prose line of the crate's own README, or "" when it has none."""
    for filename in README_NAMES:
        readme = directory / filename
        if not readme.is_file():
            continue
        content = readme.read_text(encoding="utf-8", errors="replace")
        in_code = False
        for raw in content.splitlines():
            line = raw.strip()
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code or not line:
                continue
            if line.startswith(("![", "[", "<")):
                continue
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                if same_title(title, name):
                    continue
                return normalise(title)
            return normalise(line)
    return ""


def description_of(package, directory, workspace_description):
    """The crate's own one-line description. Never invented."""
    description = package.get("description")
    if isinstance(description, dict):
        description = workspace_description if description.get("workspace") else ""
    description = normalise(description or "")
    if description:
        return elide(description)
    return elide(readme_description(directory, package.get("name", ""))) or MISSING


workspace = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]
workspace_deps = workspace.get("dependencies") or {}
workspace_package = workspace.get("package", {})
workspace_publish = workspace_package.get("publish")
workspace_description = workspace_package.get("description")
excluded = set(expand(workspace.get("exclude", [])))

members = expand(workspace.get("members", []))
crates = {}
queue = list(members)
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
withheld = []
for directory, manifest in crates.items():
    package = manifest.get("package") or {}
    if not package.get("name"):
        continue
    if not publishable(package, workspace_publish):
        withheld.append((package["name"], str(directory.relative_to(root))))
        continue
    rows.append(
        (
            package["name"],
            str(directory.relative_to(root)),
            description_of(package, directory, workspace_description),
        )
    )
rows.sort()
withheld.sort()

table = [("Crate", "Path", "Description")] + [
    (f"`{n}`", f"`{p}`", d) for n, p, d in rows
]
widths = [max(len(cell[i]) for cell in table) for i in range(3)]


def render(cells, fill=None):
    padded = [
        fill * widths[i] if fill else c.ljust(widths[i]) for i, c in enumerate(cells)
    ]
    return "| " + " | ".join(padded) + " |"


lines = [
    "# Crates",
    "",
    "Generated index of the publishable crates in this workspace.",
    "",
    "Do not hand-edit. Regenerate with:",
    "",
    "```",
    "python3 scripts/gen-crates-readme.py",
    "```",
    "",
    "Requires Python 3.11 or newer. The index is derived from the workspace",
    "manifests: the `[workspace] members` of `Cargo.toml` plus the path",
    "dependencies they reach, minus anything under `[workspace] exclude`.",
    "A crate is listed when its `[package] publish` flag does not forbid it:",
    "`publish` absent, or present and neither `false` nor an empty list. An",
    "inherited `publish.workspace = true` resolves to `[workspace.package].",
    "publish`.",
    "",
    "Each description is the crate's own: its `[package] description` (an",
    "inherited `description.workspace = true` resolves to `[workspace.package]",
    "description`), else the first prose line of the crate's own README. A",
    f"description longer than {MAX_DESCRIPTION} characters is elided at a word",
    "boundary and marked with an ellipsis.",
    "",
    f"Publishable crates: **{len(rows)}**",
    "",
    render(table[0]),
    render(table[0], fill="-"),
]
lines.extend(render(cells) for cells in table[1:])
lines += [
    "",
    "## Not published",
    "",
    f"These {len(withheld)} workspace crates set `publish = false`, so cargo",
    "does not publish them and they are deliberately absent from the index",
    "above.",
    "",
]
withheld_table = [("Crate", "Path")] + [(f"`{n}`", f"`{p}`") for n, p in withheld]
withheld_widths = [max(len(cell[i]) for cell in withheld_table) for i in range(2)]


def render_withheld(cells, fill=None):
    padded = [
        fill * withheld_widths[i] if fill else c.ljust(withheld_widths[i])
        for i, c in enumerate(cells)
    ]
    return "| " + " | ".join(padded) + " |"


lines.append(render_withheld(withheld_table[0]))
lines.append(render_withheld(withheld_table[0], fill="-"))
lines.extend(render_withheld(cells) for cells in withheld_table[1:])

content = "\n".join(lines) + "\n"
target = root / "crates" / "README.md"

if "--check" in sys.argv[1:]:
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    if current != content:
        print(
            f"crates/README.md is stale: it should list {len(rows)} publishable "
            f"and {len(withheld)} withheld crates.\n"
            "Regenerate it with:\n"
            "    python3 scripts/gen-crates-readme.py",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"crates/README.md is up to date with {len(rows)} publishable "
        f"and {len(withheld)} withheld crates"
    )
    sys.exit(0)

target.write_text(content)
print(
    f"wrote crates/README.md with {len(rows)} publishable "
    f"and {len(withheld)} withheld crates"
)
