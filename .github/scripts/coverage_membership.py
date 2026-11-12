#!/usr/bin/env python3
"""Fail-closed accounting of every workspace member against the coverage gate.

The root coverage gate (`.github/workflows/coverage.yml`) measures the root
workspace in ten named crate groups. `.github/scripts/coverage_report.py
filter` narrows each group's tarpaulin report to the package directories that
group owns and DROPS every other file, so a workspace member that no group
owns contributes nothing to any report: its source is silently discarded and
it is measured by nothing at all.

The gate states the rule it cannot enforce: "When you add a workspace member,
add it to a group AND to the packages list in the same commit; `cargo
metadata --no-deps` is the source of truth for what is a member." `cmd_filter`
only checks that a LISTED package exists. Nothing ever checked that a MEMBER
was listed, so a member could enter the workspace and vanish from the gate
without a word. This script is that check: every workspace member must be
either owned by EXACTLY ONE coverage group, or present in the membership
ledger (`.coverage-baselines/membership.toml`) with a non-empty reason.

The check is fail-closed. Anything it cannot parse, cannot resolve, or
cannot account for is an error, never a pass: an unparseable workflow, a
missing ledger, a stale ledger entry, a package owned by two groups, a member
owned by no group and not excused, and an empty excuse reason all fail.

Nothing is hardcoded: membership comes from `cargo metadata --no-deps`, and
the packages owned by each group come from the `packages:` lists in the
coverage workflow itself, so this check cannot drift from the matrix it
guards.

Usage:
    python3 .github/scripts/coverage_membership.py [--root DIR] [--metadata FILE]
                                                    [--workflow FILE] [--ledger FILE]

Exit status is 0 when every workspace member is accounted for, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

DEFAULT_WORKFLOW = os.path.join(".github", "workflows", "coverage.yml")
DEFAULT_LEDGER = os.path.join(".coverage-baselines", "membership.toml")
GROUP_JOB = "coverage-root-group"
LEDGER_SECTIONS = ("meta", "excused")


class MembershipError(Exception):
    """An input could not be parsed or resolved. Always fatal."""


# --------------------------------------------------------------------------
# inputs


def load_metadata(root, metadata_path):
    """The cargo metadata document, from disk or from `cargo metadata`."""
    if metadata_path:
        try:
            with open(metadata_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError) as exc:
            raise MembershipError(f"{metadata_path}: cannot read metadata: {exc}")
    command = [
        "cargo",
        "metadata",
        "--no-deps",
        "--format-version",
        "1",
        "--manifest-path",
        os.path.join(root, "Cargo.toml"),
    ]
    # stdout and stderr must stay separate. cargo writes warnings and progress
    # to stderr, so merging the streams (stderr=STDOUT) prepends warning text to
    # the JSON document and turns a clean run into "Expecting value: line 1
    # column 1" - a parse error that says nothing about the real cause. Parse
    # stdout alone, and report stderr only when the run actually failed or the
    # document is unusable.
    try:
        completed = subprocess.run(command, capture_output=True)
    except OSError as exc:
        raise MembershipError(f"cannot run cargo metadata: {exc}")
    stderr = completed.stderr.decode("utf-8", "replace").strip()
    if completed.returncode != 0:
        detail = stderr or completed.stdout.decode("utf-8", "replace").strip()
        raise MembershipError(
            f"cargo metadata failed ({completed.returncode}): {detail or '<no output>'}"
        )
    try:
        return json.loads(completed.stdout)
    except ValueError as exc:
        raise MembershipError(
            "cargo metadata produced invalid JSON: "
            f"{exc}; stderr: {stderr or '<empty>'}"
        )


def workspace_members(meta):
    """package name -> repo-relative directory holding its Cargo.toml."""
    try:
        root = meta["workspace_root"].rstrip("/") + "/"
        member_ids = set(meta["workspace_members"])
        packages = meta["packages"]
    except (KeyError, TypeError) as exc:
        raise MembershipError(f"cargo metadata is missing {exc}")
    members = {}
    for pkg in packages:
        if pkg.get("id") not in member_ids:
            continue
        manifest, name = pkg.get("manifest_path"), pkg.get("name")
        if not manifest or not name:
            raise MembershipError("cargo metadata has a package without a name or path")
        relative = manifest[len(root) :] if manifest.startswith(root) else manifest
        members[name] = relative.rsplit("/Cargo.toml", 1)[0]
    if not members:
        raise MembershipError("cargo metadata reports no workspace members")
    return members


def load_groups(workflow_path):
    """group name -> list of package names, read from the workflow matrix."""
    try:
        import yaml
    except ImportError as exc:
        raise MembershipError(f"PyYAML is required to read {workflow_path}: {exc}")
    try:
        with open(workflow_path, encoding="utf-8") as fh:
            document = yaml.safe_load(fh)
    except OSError as exc:
        raise MembershipError(f"{workflow_path}: cannot read: {exc}")
    except yaml.YAMLError as exc:
        raise MembershipError(f"{workflow_path}: cannot parse YAML: {exc}")
    if not isinstance(document, dict):
        raise MembershipError(f"{workflow_path}: is not a YAML mapping")
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or GROUP_JOB not in jobs:
        raise MembershipError(f"{workflow_path}: has no '{GROUP_JOB}' job")
    job = jobs[GROUP_JOB]
    strategy = job.get("strategy") if isinstance(job, dict) else None
    matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
    include = matrix.get("include") if isinstance(matrix, dict) else None
    if not isinstance(include, list) or not include:
        raise MembershipError(
            f"{workflow_path}: job '{GROUP_JOB}' has no strategy.matrix.include list"
        )
    groups = {}
    for entry in include:
        if not isinstance(entry, dict):
            raise MembershipError(
                f"{workflow_path}: matrix entry is not a mapping: {entry!r}"
            )
        name, packages = entry.get("group"), entry.get("packages")
        if not isinstance(name, str) or not name.strip():
            raise MembershipError(
                f"{workflow_path}: matrix entry has no group name: {entry!r}"
            )
        if isinstance(packages, str):
            owned = packages.split()
        elif isinstance(packages, list) and all(isinstance(p, str) for p in packages):
            owned = list(packages)
        else:
            raise MembershipError(
                f"{workflow_path}: group '{name}' has an unreadable packages list: {packages!r}"
            )
        if not owned:
            raise MembershipError(f"{workflow_path}: group '{name}' owns no packages")
        if name in groups:
            raise MembershipError(f"{workflow_path}: duplicate group '{name}'")
        groups[name] = owned
    return groups


# --------------------------------------------------------------------------
# the membership ledger
#
# The ledger is a deliberate TOML subset, parsed here so that this check needs
# no TOML library and behaves identically on python 3.9 and 3.12: a `[meta]`
# section of `key = value` pairs, and an `[excused]` section mapping a package
# name to a quoted reason (one line, or a `"""` block). Anything outside the
# subset is an error: a ledger that cannot be parsed is a ledger that cannot
# be trusted, and this check is fail-closed.


def _read_quoted(value, path, lineno):
    """A single-line basic string. Only the escapes the ledger uses."""
    if len(value) < 2 or not value.endswith('"'):
        raise MembershipError(f"{path}:{lineno}: unterminated string: {value}")
    body = value[1:-1]
    if '"' in body.replace('\\"', ""):
        raise MembershipError(f"{path}:{lineno}: unsupported escape in string")
    return body.replace('\\"', '"')


def _read_multiline(lines, index, path):
    """A `key = \"\"\"` block, closed by a line ending in `\"\"\"`."""
    body = []
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.strip().endswith('"""'):
            body.append(line.strip()[:-3])
            break
        body.append(line)
    else:
        raise MembershipError(f"{path}:{index}: unterminated multi-line string")
    return "\n".join(body).strip(), index


def parse_ledger(path):
    """Return (meta, excused) from the membership ledger."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise MembershipError(f"{path}: cannot read: {exc}")
    meta, excused = {}, {}
    section = None
    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            if not line.endswith("]"):
                raise MembershipError(
                    f"{path}:{index}: malformed section header: {raw}"
                )
            section = line[1:-1].strip()
            if section not in LEDGER_SECTIONS:
                raise MembershipError(f"{path}:{index}: unknown section [{section}]")
            continue
        if section is None:
            raise MembershipError(f"{path}:{index}: key outside any section: {raw}")
        if "=" not in line:
            raise MembershipError(f"{path}:{index}: expected 'key = value': {raw}")
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
            key = key[1:-1]
        if not key:
            raise MembershipError(f"{path}:{index}: empty key")
        if value.startswith('"""'):
            if value != '"""':
                raise MembershipError(
                    f"{path}:{index}: multi-line string must open on its own line"
                )
            text, index = _read_multiline(lines, index, path)
        elif value.startswith('"'):
            text = _read_quoted(value, path, index)
        else:
            text = value.split("#", 1)[0].strip()
        if section == "meta":
            if key in meta:
                raise MembershipError(f"{path}:{index}: duplicate meta key '{key}'")
            meta[key] = text
        else:
            if key in excused:
                raise MembershipError(f"{path}:{index}: duplicate excuse for '{key}'")
            excused[key] = text
    return meta, excused


# --------------------------------------------------------------------------
# the check


def ownership(groups):
    """package name -> the groups that own it."""
    owner = {}
    for name in sorted(groups):
        for package in groups[name]:
            owner.setdefault(package, []).append(name)
    return owner


def check(members, groups, meta, excused, owner=None):
    """Return every problem found. An empty list means everything is covered."""
    problems = []
    owner = ownership(groups) if owner is None else owner
    for package, names in sorted(owner.items()):
        if package not in members:
            problems.append(
                f"group(s) {', '.join(names)} list '{package}', which is not a workspace member"
            )
        if len(names) > 1:
            problems.append(
                f"'{package}' is owned by {len(names)} groups ({', '.join(names)}); it would be counted twice"
            )
    for package in sorted(members):
        if owner.get(package):
            continue
        if package not in excused:
            problems.append(
                f"member '{package}' ({members[package]}) is owned by no group and is not excused"
            )
        elif not excused[package].strip():
            problems.append(f"member '{package}' is excused with an empty reason")
    for package in sorted(excused):
        if package not in members:
            problems.append(
                f"the ledger excuses '{package}', which is not a workspace member (stale)"
            )
    measured = sum(1 for p in members if len(owner.get(p, [])) == 1)
    excused_count = sum(1 for p in members if not owner.get(p) and p in excused)
    for key, actual in (
        ("total_members", len(members)),
        ("measured_members", measured),
        ("excused_members", excused_count),
    ):
        if key not in meta:
            problems.append(f"the membership ledger [meta] is missing '{key}'")
            continue
        try:
            recorded = int(str(meta[key]).strip())
        except ValueError:
            problems.append(
                f"the membership ledger [meta] '{key}' is not an integer: {meta[key]!r}"
            )
            continue
        if recorded != actual:
            problems.append(
                f"the membership ledger [meta] '{key}' says {recorded}, but the workspace has {actual}"
            )
    return problems


def source_lines(root, package_dir):
    """Rust source lines under a member's own package directory."""
    base = os.path.join(root, package_dir)
    if not os.path.isdir(base):
        return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "target"]
        for name in filenames:
            if not name.endswith(".rs"):
                continue
            try:
                with open(
                    os.path.join(dirpath, name), encoding="utf-8", errors="replace"
                ) as fh:
                    total += sum(1 for _ in fh)
            except OSError:
                continue
    return total


# --------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("GITHUB_WORKSPACE", "."),
        help="repository root (default: GITHUB_WORKSPACE or .)",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="cargo metadata JSON to read instead of running cargo "
        "metadata (default: run cargo metadata --no-deps)",
    )
    parser.add_argument(
        "--workflow",
        default=None,
        help="coverage workflow holding the group package lists "
        f"(default: <root>/{DEFAULT_WORKFLOW})",
    )
    parser.add_argument(
        "--ledger",
        default=None,
        help="membership ledger " f"(default: <root>/{DEFAULT_LEDGER})",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    workflow = args.workflow or os.path.join(root, DEFAULT_WORKFLOW)
    ledger = args.ledger or os.path.join(root, DEFAULT_LEDGER)
    try:
        meta = load_metadata(root, args.metadata)
        members = workspace_members(meta)
        groups = load_groups(workflow)
        ledger_meta, excused = parse_ledger(ledger)
    except MembershipError as exc:
        print(f"::error::the coverage membership check could not run: {exc}")
        print(f"error: {exc}", file=sys.stderr)
        return 1

    owner = ownership(groups)
    problems = check(members, groups, ledger_meta, excused, owner)
    measured = [p for p in sorted(members) if len(owner.get(p, [])) == 1]
    excused_members = [p for p in sorted(members) if not owner.get(p)]
    measured_lines = sum(source_lines(root, members[p]) for p in measured)
    excused_lines = sum(source_lines(root, members[p]) for p in excused_members)

    print(f"workspace members:  {len(members)}")
    print(
        f"coverage groups:     {len(groups)} "
        f"({sum(len(g) for g in groups.values())} package entries)"
    )
    print(f"measured:            {len(measured)} members owned by exactly one group")
    print(f"excused:             {len(excused_members)} members listed in {ledger}")
    print(
        f"rust source lines:   {measured_lines} measured / {excused_lines} "
        "excused (under each member's own package directory)"
    )
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        print(f"\n{len(problems)} coverage membership problem(s).", file=sys.stderr)
        return 1
    print(
        "OK: every workspace member is measured by exactly one coverage group "
        "or is excused with a reason."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
