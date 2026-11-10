#!/usr/bin/env python3
"""Gate sdk-catalog.json against the seam contract.

Reads only sdk-catalog.json, so it is fast and runs anywhere. Exit 0 = all checked rules
hold; exit 2 = at least one violation, printed as a table.

Rules (numbers match the remediation plan's seam contract):
  R1  standalone packaging : every `publish` crate can `cargo package --no-verify`
                             (opt-in: --rule1, it shells out once per publish crate)
  R2  layer discipline     : a runtime dependency edge never points UP a layer
                             (dev-dependencies are reported separately: they cannot reach a
                              published consumer, so they are not a layering defect)
  R3  no bulk-leaking feat : a `publish` crate may not enable an L3/L4 crate in any feature
  R4  declared stability   : every `publish` crate has stability != undeclared
  R5  catalog completeness : zero members with layer == unclassified

Usage:
    python3 tools/sdk-catalog/check.py              # R2-R5
    python3 tools/sdk-catalog/check.py --rule1      # adds R1 (slow)
    python3 tools/sdk-catalog/check.py --rule1-limit 5   # R1 on the first 5 publish crates
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CATALOG = os.path.join(ROOT, "sdk-catalog.json")
ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load():
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    cat = load()
    members = {m["name"]: m for m in cat["members"]}
    violations = {"R1": [], "R2": [], "R3": [], "R4": [], "R5": []}
    dev_only = []

    # R2 + R3: recompute local edges, because the catalog stores counts, not pairs
    raw = subprocess.run(["cargo", "metadata", "--no-deps", "--format-version", "1", "--offline"],
                         cwd=ROOT, capture_output=True, text=True)
    meta = json.loads(raw.stdout) if raw.returncode == 0 else {"packages": []}
    path_of = {}
    for p in meta.get("packages", []):
        path_of[os.path.normpath(os.path.dirname(p["manifest_path"]))] = p["name"]
    feats = {p["name"]: p.get("features", {}) for p in meta.get("packages", [])}

    for p in meta.get("packages", []):
        src = p["name"]
        sm = members.get(src)
        if not sm or sm["layer"] == "unclassified":
            continue
        for dep in p.get("dependencies", []):
            if not dep.get("path"):
                continue
            tgt = path_of.get(os.path.normpath(dep["path"]))
            tm = members.get(tgt) if tgt else None
            if not tm or tm["layer"] == "unclassified":
                continue
            if ORDER[tm["layer"]] > ORDER[sm["layer"]]:
                edge = f"{src}({sm['layer']}) -> {tgt}({tm['layer']})"
                if dep.get("kind") == "dev":
                    dev_only.append(edge)
                else:
                    violations["R2"].append(edge)
        if sm["publication_class"] == "publish":
            for feat, deps in feats.get(src, {}).items():
                for d in deps:
                    dm = members.get(d) or members.get(d.split("/")[0])
                    if dm and dm["layer"] in ("L3", "L4"):
                        violations["R3"].append(f"{src}.{feat} enables {d}({dm['layer']})")

    # R4 + R5
    for m in cat["members"]:
        if m["layer"] == "unclassified":
            violations["R5"].append(m["name"])
        if m["publication_class"] == "publish" and m["stability"] == "undeclared":
            violations["R4"].append(m["name"])

    # R1 is opt-in: it runs cargo once per publish crate. --rule1-limit N bounds a probe run.
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--rule1-limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    if "--rule1" in sys.argv:
        checked = 0
        for m in cat["members"]:
            if limit is not None and checked >= limit:
                break
            if m["publication_class"] != "publish":
                continue
            checked += 1
            r = subprocess.run(["cargo", "package", "--no-verify", "--allow-dirty", "--list",
                                "-p", m["name"]], cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                first = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["unknown error"]
                violations["R1"].append(f"{m['name']}: {first[0][:120]}")

    titles = {
        "R1": "standalone packaging (cargo package --no-verify)",
        "R2": "layer discipline (no upward edges)",
        "R3": "no bulk-leaking features",
        "R4": "declared stability on publish crates",
        "R5": "catalog completeness (zero unclassified)",
    }
    total = 0
    print(f"catalog: {cat['member_count']} members, generated {cat['generated_at_utc']} at {cat['commit'][:9]}")
    for rule in ("R1", "R2", "R3", "R4", "R5"):
        if rule == "R1" and "--rule1" not in sys.argv:
            print(f"  {rule}  SKIPPED  {titles[rule]}  (pass --rule1)")
            continue
        hits = violations[rule]
        total += len(hits)
        state = "PASS" if not hits else f"FAIL({len(hits)})"
        print(f"  {rule}  {state:<9} {titles[rule]}")
        for h in hits[:12]:
            print(f"        - {h}")
        if len(hits) > 12:
            print(f"        ... and {len(hits) - 12} more")
    if dev_only:
        print(f"  note: {len(dev_only)} upward edge(s) are dev-only and do not ship, e.g. {dev_only[0]}")
    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {total} violation(s) across the checked rules")
    return 0 if total == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
