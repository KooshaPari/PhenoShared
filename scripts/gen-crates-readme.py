#!/usr/bin/env python3
"""Regenerates crates/README.md's crate index from the workspace manifests.

The previous file was hand-maintained and had drifted: it named far fewer crates
than the workspace publishes. This derives the list from `cargo metadata
--no-deps` so the index cannot silently fall behind again. A crate is
"publishable" when [package].publish is not false.
"""
import json, subprocess, sys, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
out = subprocess.run(
    ["cargo", "metadata", "--no-deps", "--format-version", "1"],
    cwd=root, capture_output=True, text=True,
)
if out.returncode != 0:
    sys.exit("cargo metadata failed: " + out.stderr[-800:])
md = json.loads(out.stdout)
pkgs = []
for p in md["packages"]:
    if p.get("publish") == []:
        continue
    rel = pathlib.Path(p["manifest_path"]).parent.relative_to(root)
    pkgs.append((p["name"], str(rel)))
pkgs.sort()
lines = [
    "# Crates",
    "",
    "Generated index of every publishable crate in this workspace.",
    "Do not hand-edit: regenerate with `python3 scripts/gen-crates-readme.py`.",
    "",
    f"Total publishable crates: **{len(pkgs)}**",
    "",
    "| Crate | Path |",
    "|---|---|",
]
lines += [f"| `{n}` | `{path}` |" for n, path in pkgs]
(root / "crates" / "README.md").write_text("\n".join(lines) + "\n")
print(f"wrote crates/README.md with {len(pkgs)} crates")
