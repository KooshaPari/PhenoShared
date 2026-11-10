#!/usr/bin/env python3
"""Per-crate-group coverage reporting for the root workspace gate.

The root workspace is split into named crate groups (see the matrix in
`.github/workflows/coverage.yml`). Each group is measured by its own
`cargo tarpaulin` run in its own job; this script is the only place that

  * narrows a tarpaulin report down to the files a group actually owns,
  * compares a group (or the whole workspace) against a committed floor,
  * merges the per-group results into the aggregate figure that the required
    branch-protection check enforces.

Why the narrowing happens here and not in tarpaulin: tarpaulin builds its
denominator by walking the repository for `*.rs`, not by asking what the build
compiled, so a single-package run still reports every source file in the tree.
Filtering by the group's own package directories is what makes the per-group
numbers add up to the aggregate without double counting.

Modes:
  filter     narrow one tarpaulin JSON report to one group
  verify     enforce one group's floor from the baseline file
  aggregate  merge all group reports and enforce the aggregate floor
  write      (re)generate a baseline file from a directory of group reports

Baseline file format (`.coverage-baselines/root-workspace.toml`):

    [meta]
    aggregate_floor = 36.0

    [groups]
    substrate = 55.0
    ...

Every value is a percentage of coverable lines, compared with `<` so a value
exactly on the floor passes. Comments and blank lines are ignored.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

try:  # Python 3.11+ ships a real TOML reader
    import tomllib as _toml  # type: ignore  # noqa: F401
    assert _toml is not None
except ModuleNotFoundError:  # Python 3.9/3.10: the subset parser below is used
    _toml = None


# --------------------------------------------------------------------------
# baseline file


def read_baseline(path):
    """Parse the tiny subset of TOML this file uses: [section] and key = number."""
    meta, groups = {}, {}
    section = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if "=" not in line:
                raise SystemExit(f"{path}: cannot parse line: {raw.rstrip()}")
            key, value = line.split("=", 1)
            key, value = key.strip().strip('"'), value.strip()
            target = meta if section == "meta" else groups
            if target is meta and key == "aggregate_floor":
                meta[key] = float(value)
            elif section == "groups":
                groups[key] = float(value)
            else:
                raise SystemExit(f"{path}: unexpected key {key!r} in [{section}]")
    if "aggregate_floor" not in meta:
        raise SystemExit(f"{path}: [meta] aggregate_floor is required")
    return meta, groups


# --------------------------------------------------------------------------
# workspace / package plumbing


def workspace_metadata(root):
    out = subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--format-version", "1",
         "--manifest-path", os.path.join(root, "Cargo.toml")])
    return json.loads(out)


def package_dirs(meta):
    """package name -> repo-relative directory containing its Cargo.toml."""
    root = meta["workspace_root"].rstrip("/") + "/"
    dirs = {}
    for pkg in meta["packages"]:
        mp = pkg["manifest_path"]
        rel = mp[len(root):] if mp.startswith(root) else mp
        dirs[pkg["name"]] = rel.rsplit("/Cargo.toml", 1)[0]
    return dirs


def join_path(entry):
    """Flatten tarpaulin's path representation (a component list or a string)."""
    raw = entry.get("path")
    if isinstance(raw, list):
        parts = [str(p).strip("/") for p in raw if str(p).strip("/")]
        return "/" + "/".join(parts)
    return str(raw)


def relpath(abs_path, workspace_root):
    """Repo-relative form of a report path, or the path itself if already relative."""
    if not abs_path.startswith("/"):
        return abs_path
    root = workspace_root.rstrip("/") + "/"
    if abs_path.startswith(root):
        return abs_path[len(root):]
    return None


# --------------------------------------------------------------------------
# filter


def cmd_filter(args):
    meta = workspace_metadata(args.root)
    dirs = package_dirs(meta)
    packages = args.packages.split()
    unknown = [p for p in packages if p not in dirs]
    if unknown:
        raise SystemExit(f"unknown package(s) for group {args.group}: {unknown}")
    owned = [dirs[p] + "/" for p in packages]

    report = json.load(open(args.report, encoding="utf-8"))
    files = []
    covered = coverable = outside = 0
    for entry in report.get("files", []):
        rel = relpath(join_path(entry), meta["workspace_root"])
        if rel is None or not any(rel.startswith(d) for d in owned):
            outside += entry.get("coverable", 0)
            continue
        files.append({"path": rel,
                      "covered": entry.get("covered", 0),
                      "coverable": entry.get("coverable", 0)})
        covered += entry.get("covered", 0)
        coverable += entry.get("coverable", 0)

    percent = (100.0 * covered / coverable) if coverable else 0.0
    payload = {
        "group": args.group,
        "packages": packages,
        "covered": covered,
        "coverable": coverable,
        "percent": round(percent, 4),
        "files": sorted(files, key=lambda f: f["path"]),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    print(f"{args.group}: {covered}/{coverable} = {percent:.2f}% "
          f"({len(files)} files, {outside} coverable lines outside the group "
          f"were dropped)")
    return 0


# --------------------------------------------------------------------------
# verify / aggregate


def load_group_reports(directory):
    reports = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        data = json.load(open(path, encoding="utf-8"))
        group = data.get("group") or name[:-5]
        reports[group] = data
    return reports


def table(rows):
    width = max(len(r[0]) for r in rows)
    lines = []
    for name, pct, floor, covered, coverable, verdict in rows:
        lines.append(
            f"{name:<{width}}  {pct:6.2f}%  floor {floor:6.2f}%  "
            f"{covered:>7}/{coverable:<7} {verdict}")
    return lines


def cmd_verify(args):
    meta, groups = read_baseline(args.baseline)
    data = json.load(open(args.report_file, encoding="utf-8"))
    group = data["group"]
    if group not in groups:
        raise SystemExit(f"{args.baseline}: no floor for group {group!r}; "
                         f"known groups: {sorted(groups)}")
    floor = groups[group]
    pct = data["percent"]
    ok = pct >= floor
    row = (group, pct, floor, data["covered"], data["coverable"],
           "PASS" if ok else "FAIL")
    for line in table([row]):
        print(line)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write(f"\n### Root coverage — {group}\n\n")
            fh.write("| group | coverage | floor | lines | verdict |\n")
            fh.write("|---|---|---|---|---|\n")
            fh.write(f"| {group} | {pct:.2f}% | {floor:.2f}% | "
                     f"{data['covered']}/{data['coverable']} | "
                     f"{'PASS' if ok else 'FAIL'} |\n")
    if not ok:
        print(f"::error::{group} coverage {pct:.2f}% is below its committed "
              f"floor {floor:.2f}% ({args.baseline})")
        return 1
    return 0


def cmd_aggregate(args):
    meta_floor_meta, groups = read_baseline(args.baseline)
    reports = load_group_reports(args.dir)
    missing = sorted(set(groups) - set(reports))
    extra = sorted(set(reports) - set(groups))
    rows = []
    failures = []
    for group in sorted(groups):
        if group not in reports:
            continue
        data = reports[group]
        floor = groups[group]
        pct = data["percent"]
        ok = pct >= floor
        if not ok:
            failures.append(
                f"{group} {pct:.2f}% < floor {floor:.2f}%")
        rows.append((group, pct, floor, data["covered"], data["coverable"],
                     "PASS" if ok else "FAIL"))

    covered = sum(r[3] for r in rows)
    coverable = sum(r[4] for r in rows)
    aggregate = (100.0 * covered / coverable) if coverable else 0.0
    floor = meta_floor_meta["aggregate_floor"]
    agg_ok = aggregate >= floor

    print("per-group coverage (each group owns its own crate directories):")
    for line in table(rows):
        print("  " + line)
    print(f"aggregate: {covered}/{coverable} = {aggregate:.2f}%  "
          f"floor {floor:.2f}%  {'PASS' if agg_ok else 'FAIL'}")

    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("\n### Root coverage — aggregate\n\n")
            fh.write("| group | coverage | floor | lines | verdict |\n")
            fh.write("|---|---|---|---|---|\n")
            for name, pct, fl, cov, cab, verdict in rows:
                fh.write(f"| {name} | {pct:.2f}% | {fl:.2f}% | {cov}/{cab} | "
                         f"{verdict} |\n")
            fh.write(f"| **aggregate** | **{aggregate:.2f}%** | "
                     f"**{floor:.2f}%** | **{covered}/{coverable}** | "
                     f"**{'PASS' if agg_ok else 'FAIL'}** |\n")

    if missing or extra:
        print("::error::group set does not match the baseline: "
              f"missing={missing} unexpected={extra}. If a group was renamed "
              "or added, update .coverage-baselines/root-workspace.toml in the "
              "same commit.")
        return 1
    if failures:
        for f in failures:
            print(f"::error::group below floor: {f}")
    if not agg_ok:
        print(f"::error::aggregate coverage {aggregate:.2f}% is below the "
              f"committed aggregate floor {floor:.2f}%")
    return 0 if agg_ok and not failures else 1


def floor2(percent):
    """Truncate to 2 decimals so the exact measured value passes its own floor.

    Rounding would round some measured values UP (59.9352 -> 59.94) and the
    freshly regenerated baseline would then fail against itself on the next run.
    """
    return math.floor(percent * 100.0) / 100.0


def cmd_write(args):
    reports = load_group_reports(args.dir)
    if not reports:
        raise SystemExit(f"no group reports under {args.dir}")
    covered = sum(r["covered"] for r in reports.values())
    coverable = sum(r["coverable"] for r in reports.values())
    aggregate = 100.0 * covered / coverable
    lines = [
        "# Root workspace coverage baselines.",
        "#",
        "# FORMAT: [meta] aggregate_floor = <percent>; [groups] <name> = <percent>.",
        "# Every value is a percentage of coverable lines. A measured value equal",
        "# to the floor passes (the comparison is `<`). Comments and blank lines",
        "# are ignored; the parser is deliberately a TOML subset.",
        "#",
        f"# Each group floor is the group's measured value minus a {args.allowance:.2f}-point",
        "# instrument allowance, truncated (never rounded) to two decimals. The",
        "# allowance exists because a group-only tarpaulin run does not inherit",
        "# coverage that another group's tests contributed to this group's files,",
        "# and because the answer must not depend on the order or tree state of a",
        "# single run. The measured value is kept next to each floor so the",
        "# allowance can be audited rather than guessed at.",
        "#",
        "# REGENERATE: measure every group (see the matrix in",
        "# .github/workflows/coverage.yml), then",
        "#",
        "#   python3 .github/scripts/coverage_report.py write \\",
        "#       --dir coverage-groups \\",
        "#       --baseline .coverage-baselines/root-workspace.toml \\",
        "#       --allowance 1.0 --aggregate-floor 36",
        "#",
        "",
        "[meta]",
        f"aggregate_floor = {args.aggregate_floor:.2f}",
        f"# measured aggregate on this run: {aggregate:.2f}% "
        f"({covered}/{coverable})",
        "",
        "[groups]",
    ]
    for name in sorted(reports):
        measured = reports[name]["percent"]
        lines.append(
            f"{name} = {floor2(measured - args.allowance):.2f}"
            f"  # measured {measured:.2f}")
    text = "\n".join(lines) + "\n"
    if args.baseline:
        with open(args.baseline, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.baseline}")
    else:
        print(text)
    return 0


# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=os.environ.get("GITHUB_WORKSPACE", "."),
                    help="repository root (default: GITHUB_WORKSPACE or .)")
    sub = ap.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("filter")
    p.add_argument("--group", required=True)
    p.add_argument("--packages", required=True,
                   help="space-separated package names owned by the group")
    p.add_argument("--report", required=True, help="tarpaulin JSON report")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_filter)

    p = sub.add_parser("verify")
    p.add_argument("--report-file", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--summary", default=None)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("aggregate")
    p.add_argument("--dir", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--summary", default=None)
    p.set_defaults(func=cmd_aggregate)

    p = sub.add_parser("write")
    p.add_argument("--dir", required=True)
    p.add_argument("--baseline", default=None)
    p.add_argument("--allowance", type=float, default=1.0,
                   help="points subtracted from each measured group value")
    p.add_argument("--aggregate-floor", type=float, default=36.0,
                   help="aggregate floor to commit (default keeps the "
                        "documented 36, which is not derived from the run)")
    p.set_defaults(func=cmd_write)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
