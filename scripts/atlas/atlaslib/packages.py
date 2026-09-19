"""Cargo package discovery, ownership, and per-package aggregation.

A "package" is any directory containing a tracked `Cargo.toml`. Each file
belongs to the *deepest* such directory containing it, so a nested package's
files are never counted twice and a wrapper crate is not credited with its
children's code.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

from .definitions import DOC_EXT


def toml_tables(text: str) -> dict[str, str]:
    """Split a manifest into {table: body}.

    A minimal splitter, not a TOML parser: enough for `[package]`, `[lib]`,
    `[[bin]]`, and `[workspace]`. Inline tables and dotted keys are not
    interpreted, which the artifacts disclose as a known limit.
    """
    tables: dict[str, str] = defaultdict(str)
    current = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped.strip("[]").strip().strip('"')
            tables.setdefault(current, "")
            tables[current] += "\n"
            continue
        if current:
            tables[current] += line + "\n"
    return tables


def toml_str(body: str, key: str):
    match = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*"([^"]*)"', body, re.M)
    return match.group(1) if match else None


def toml_array(text: str, key: str) -> list[str]:
    """Extract a multi-line, comment-bearing array of quoted strings."""
    match = re.search(r"^\s*" + re.escape(key) + r"\s*=\s*\[", text, re.M)
    if not match:
        return []
    i, depth, items = match.end(), 1, []
    while i < len(text) and depth > 0:
        char = text[i]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == '"':
            end = text.find('"', i + 1)
            if end < 0:
                break
            items.append(text[i + 1:end])
            i = end
        elif char == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        i += 1
    return items


def workspace_tables(text: str) -> tuple[list[str], list[str]]:
    """(members, exclude) declared in the root `[workspace]` table."""
    match = re.search(r"^\[workspace\]\s*$", text, re.M)
    if not match:
        return [], []
    following = re.search(r"^\[", text[match.end():], re.M)
    body = text[match.end(): match.end() + (following.start() if following else len(text))]
    return toml_array(body, "members"), toml_array(body, "exclude")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def build_packages(root: str, paths: list[str]) -> tuple[dict[str, dict], dict[str, str]]:
    """Discover every tracked package directory and classify its workspace kind."""
    root_text = _read(os.path.join(root, "Cargo.toml"))
    members, excludes = workspace_tables(root_text)
    member_set = {m.strip("/") for m in members}
    exclude_set = {e.strip("/") for e in excludes}

    packages: dict[str, dict] = {}
    for rel in paths:
        if os.path.basename(rel) != "Cargo.toml":
            continue
        directory = os.path.dirname(rel)
        text = _read(os.path.join(root, rel))
        tables = toml_tables(text)
        package_body = tables.get("package", "")
        name = toml_str(package_body, "name") or os.path.basename(directory) or "(root)"

        if directory == "":
            kind = "workspace-root"
        elif directory in member_set:
            kind = "member"
        elif directory in exclude_set:
            kind = "excluded"
        elif "workspace" in tables:
            kind = "sub-workspace"
        elif package_body.strip():
            kind = "non-member"
        else:
            kind = "manifest-only"

        packages[directory] = {
            "dir": directory,
            "name": name,
            "kind": kind,
            "desc": toml_str(package_body, "description"),
            "lib": "lib" in tables,
            "bins": len(re.findall(r"^\[\[bin\]\]", text, re.M)),
            "targets": len(re.findall(r"^\[\[(?:bin|example|bench|test)\]\]", text, re.M)),
        }
    return packages, member_set


def deepen(packages: dict[str, dict]) -> list[str]:
    """Package directories ordered deepest-first, for longest-prefix lookup."""
    return sorted(packages, key=len, reverse=True)


def owner_of(directory_order: list[str], rel: str) -> str:
    for directory in directory_order:
        if directory and rel.startswith(directory + "/"):
            return directory
    return ""


ROLE_HINTS = (
    (r"^engine-", "engine adapter / integration surface"),
    (r"^driver-", "driver / transport entry layer"),
    (r"^store-", "persistence store backend"),
    (r"^cloud-", "hosted cloud provider adapter"),
    (r"^fabric-", "PhenoFabric crate (absorbed 2026-09-16)"),
    (r"^substrate", "substrate foundation layer"),
    (r"^phenotype-", "phenotype platform crate"),
    (r"^pheno-", "phenotype platform crate"),
    (r"^argis-", "argis extension crate"),
    (r"^port-", "port / platform surface crate"),
    (r"^agileplus|^agile-plus", "AgilePlus planning crate"),
    (r"^hexa-kit", "hexa-kit polyglot template kit"),
    (r"^template", "template scaffold"),
)


def role_for(root: str, package: dict) -> str:
    """One-line role: declared description, else README prose, else inferred."""
    if package["desc"]:
        return " ".join(package["desc"].split())
    readme = os.path.join(root, package["dir"], "README.md")
    try:
        with open(readme, encoding="utf-8", errors="replace") as handle:
            heading_seen = False
            for raw in handle:
                line = " ".join(raw.split())
                if not line:
                    continue
                if line.startswith("#"):
                    heading_seen = True
                    continue
                if heading_seen:
                    return line[:160]
    except OSError:
        pass
    for pattern, label in ROLE_HINTS:
        if re.search(pattern, package["name"]):
            return "~ " + label
    return "~ (no description declared)"


def aggregate(root: str, packages: dict[str, dict], paths: list[str],
              files: dict[str, dict], dates: dict[str, str]):
    """Roll file records up to their owning package.

    `dates` maps path -> most recent author date; each package reports the
    newest date across its files.
    """
    directory_order = deepen(packages)
    stats = defaultdict(lambda: {
        "loc": 0, "rs": 0, "files": 0, "tests": 0, "docs": 0,
        "os": set(), "last": "", "link": 0,
    })
    unowned = {"files": 0, "loc": 0, "tests": 0}
    for rel in paths:
        rec = files[rel]
        owner = owner_of(directory_order, rel)
        bucket = stats[owner]
        bucket["loc"] += rec["loc"]
        bucket["files"] += 1
        bucket["tests"] += rec["tests"]
        if rec["kind"] == "link":
            bucket["link"] += 1
        if rel.endswith(".rs"):
            bucket["rs"] += 1
        if os.path.splitext(rel)[1].lstrip(".").lower() in DOC_EXT:
            bucket["docs"] += 1
        bucket["os"].update(rec["os_cfg"])
        stamped = dates.get(rel, "")
        if stamped > bucket["last"]:
            bucket["last"] = stamped
        if owner == "":
            unowned["files"] += 1
            unowned["loc"] += rec["loc"]
            unowned["tests"] += rec["tests"]

    rows = []
    for directory, package in packages.items():
        bucket = stats[directory]
        flavour = "lib+bin" if package["lib"] and package["bins"] else (
            "lib" if package["lib"] else ("bin" if package["bins"] else "meta"))
        rows.append({
            "dir": directory or "(workspace root)",
            "name": package["name"],
            "kind": package["kind"] + "/" + flavour,
            "loc": bucket["loc"],
            "rs": bucket["rs"],
            "files": bucket["files"],
            "tests": bucket["tests"],
            "docs": bucket["docs"],
            "os": ",".join(sorted(bucket["os"])) or "-",
            "last": bucket["last"] or "-",
            "role": role_for(root, package),
            "is_member": package["kind"] == "member",
        })
    rows.sort(key=lambda r: (-r["loc"], r["dir"]))
    return rows, unowned, stats
