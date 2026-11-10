#!/usr/bin/env python3
"""Generate sdk-catalog.json for the PhenoShared container.

Input is `cargo metadata --no-deps` (authoritative member graph, offline), plus
`annotations.json` (the only place a human/agent records a judgement).

Two axes per member, per the remediation plan:
  axis 1  publication_class : publish | internal | quarantine
  axis 2  layer             : L0 core | L1 port | L2 adapter | L3 engine | L4 app

Nothing here is hand-maintained. Re-run it after any manifest change.

Usage:
    python3 tools/sdk-catalog/generate.py            # write sdk-catalog.json
    python3 tools/sdk-catalog/generate.py --stdout   # print, write nothing
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "sdk-catalog.json")

# Non-Rust payloads are DISCOVERED, not assumed: a top-level directory becomes a payload when it
# holds at least PAYLOAD_MIN_LOC lines of Python/Go/TS/JS. Discovery keeps the inventory complete;
# PUBLISHABLE_ROOT then decides whether the discovered surface is a publication target at all.
PAYLOAD_MIN_LOC = 1000
LANG_CHANNEL = {"py": "pypi", "go": "gomod", "ts": "npm", "js": "npm"}
LANG_SUFFIX = {"py": (".py",), "go": (".go",), "ts": (".ts", ".tsx"), "js": (".js", ".jsx")}
SCAN_SKIP = {".git", "target", "node_modules", ".venv", ".vendor", "archives", "archive", "historical", "docs"}

# Roots that are meant to reach an external consumer. Anything discovered outside this set is real
# code but stays internal: test suites, benchmarks, scripts and archives are not packages.
PUBLISHABLE_ROOT = {
    "agents", "python", "servers", "apps", "packages", "sites", "web", "dashboard",
    "go-fabric", "cmd", "linux-client", "windows-client", "native", "pheno", "pheno-cli",
    "kernels", "platforms", "crates",
}

# Directories whose dominant non-Rust language understates what they are.
PAYLOAD_OVERRIDES = {
    "crates": ("mixed", "crates.io+pypi+gomod+npm",
               "the Rust workspace also carries Python and Go source; those cannot ship as Rust crates"),
}

# Name-based layer rules. Ordered: first match wins. Kept deliberately narrow so that
# an unmatched crate surfaces as `unclassified` instead of being silently binned.
# Ordered name rules: first match wins, so the narrowest pattern must come first. The patterns
# encode role, and they are corrected by evidence, not by taste: `driver-*`, `-web` and
# `-orchestrator` moved to L4 after the dependency graph showed them sitting above the engines they
# drive, and `-manifest`, `-quant`, `-conformance` dropped to L0/L1 after proving they are leaves.
LAYER_RULES = [
    ("L4", r"(^app-|-app$|-cli$|^cli-|-daemon$|^daemon-|-tui$|-gui$|-mcp-server$|-webhook-server$"
           r"|-server$|-ffi$|-bin$|^driver-|-driver$|-driver-|-sample$|-example$|-web$|-orchestrator)"),
    ("L1", r"(^port-|-port$|-port-|-ports$|^ports-|-api$|-traits?$|-contracts?$|-spec$|^spec-"
           r"|-quant$|-kernels?$)"),
    ("L2", r"(^adapter-|-adapter$|-store$|^store-|-http$|^http-|-mcp$|^mcp-|redis|postgres|sqlite"
           r"|^cloud-|-cloud$|-client$|-connector|-plugin$)"),
    ("L3", r"(^engine-|-engine$|-planner$|^planner-|-scheduler|-runtime$|^runtime-|-service$"
           r"|^service-|-kernel$|^kernel-)"),
    ("L0", r"(^core-|-core$|-types$|-schema$|^schema-|-primitives?$|-model$|^model-|-util$|^util-"
           r"|-utils$|-errors?$|-macros$|-config$|^config-|-manifest$)"),
]
LAYER_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load_annotations():
    path = os.path.join(HERE, "annotations.json")
    if not os.path.exists(path):
        return {"members": {}, "payloads": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cargo_metadata():
    raw = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1", "--offline"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if raw.returncode != 0:
        sys.stderr.write(raw.stderr)
        raise SystemExit("cargo metadata failed")
    return json.loads(raw.stdout)


# Why a layer was assigned, when it was not a plain name match.
REASON = {
    "annotation": "explicit annotation",
    "dag-leaf": "no internal dependencies: foundational by construction",
    "dag-deep": "depends through three or more internal layers: application altitude",
    "default": "no name rule and no decisive dependency depth; default L3 pending curation",
    "unclassified": "unreachable: layer always resolves",
}


def layers_from_dag(deps_by_name):
    """Return {name: depth} where depth is the longest chain of internal dependencies below it.

    The dependency graph is evidence about a crate's position; a crate with no internal deps can
    only be foundational, and a crate sitting under four layers of its own kind cannot be one.
    Cycles are tolerated by cutting the back-edge instead of recursing forever.
    """
    depth, stack = {}, set()

    def visit(name):
        if name in depth:
            return depth[name]
        if name in stack:
            return 0
        stack.add(name)
        deps = [d for d in deps_by_name.get(name, ()) if d in deps_by_name]
        best = 0
        for dep in deps:
            best = max(best, visit(dep) + 1)
        stack.discard(name)
        depth[name] = best
        return best

    for name in deps_by_name:
        visit(name)
    return depth


def derive_stability(version, override):
    """Semver already encodes the API promise, so read it instead of asking for a hand-written badge.

    0.x means the author reserved the right to break the API; 1.x and above means it did not.
    An annotation can still override this, and an override always wins.
    """
    if "stability" in override:
        return override["stability"], "annotation"
    try:
        major = int(str(version).split(".")[0])
    except (TypeError, ValueError):
        return "undeclared", "unparseable version"
    return ("stable", "version >= 1.0") if major >= 1 else ("experimental", "0.x version")


def derive_layer(name, bins):
    for layer, pattern in LAYER_RULES:
        if re.search(pattern, name):
            return layer
    return "unclassified"


def apply_bin_altitude(name, bins, layer):
    """A same-named binary is the convention for a shipped tool, so it outranks a name rule.

    `hwledger-mcp` matches `-mcp$` (client library) but ships `hwledger-mcp` and
    `hwledger-mcp-http`, which makes it a server. Probe/dev binaries (`*-smoke`, `dump-schema`)
    do not promote the library that owns them, so the bin must match the crate name exactly.
    """
    return "L4" if name in bins else layer


def loc_of_src(crate_dir):
    total = 0
    src = os.path.join(crate_dir, "src")
    if not os.path.isdir(src):
        return 0
    for base, _dirs, files in os.walk(src):
        for f in files:
            if f.endswith(".rs"):
                try:
                    with open(os.path.join(base, f), "rb") as fh:
                        total += fh.read().count(b"\n")
                except OSError:
                    pass
    return total


def walk_lang(abspath):
    """Return ({lang: loc}, file_count) for one tree, skipping generated and vendored dirs."""
    locs = {k: 0 for k in LANG_SUFFIX}
    files = 0
    for base, dirs, fnames in os.walk(abspath):
        dirs[:] = [d for d in dirs if d not in SCAN_SKIP]
        for f in fnames:
            for lang, suffixes in LANG_SUFFIX.items():
                if f.endswith(suffixes):
                    files += 1
                    try:
                        with open(os.path.join(base, f), "rb") as fh:
                            locs[lang] += fh.read().count(b"\n")
                    except OSError:
                        pass
                    break
    return locs, files


def discover_payloads(ann):
    """A top-level dir is a payload when it carries PAYLOAD_MIN_LOC+ lines of a non-Rust language."""
    payloads = []
    for entry in sorted(os.listdir(ROOT)):
        abs_path = os.path.join(ROOT, entry)
        if not os.path.isdir(abs_path) or entry in SCAN_SKIP or entry.startswith("."):
            continue
        locs, files = walk_lang(abs_path)
        total = sum(locs.values())
        if total < PAYLOAD_MIN_LOC:
            continue
        dominant = max(locs, key=lambda k: locs[k])
        if entry in PAYLOAD_OVERRIDES:
            kind, channel, note = PAYLOAD_OVERRIDES[entry]
        elif entry in PUBLISHABLE_ROOT:
            kind, channel = dominant, LANG_CHANNEL[dominant]
            note = f"dominant non-Rust language: {dominant}"
        else:
            kind, channel = dominant, "none"
            note = f"tooling/tests/archive surface, not a publication target ({dominant})"
        payloads.append({
            "kind": kind, "path": entry, "channel": channel, "loc": total, "files": files,
            "by_language": {k: v for k, v in locs.items() if v},
            "publication_class": ann["payloads"].get(entry, {}).get(
                "publication_class", "publish" if entry in PUBLISHABLE_ROOT else "internal"),
            "note": note,
        })

    tauri = os.path.join(ROOT, "crates", "fabric-gui", "src-tauri")
    if os.path.isdir(tauri):
        loc, files = 0, 0
        for base, dirs, fnames in os.walk(tauri):
            dirs[:] = [d for d in dirs if d not in SCAN_SKIP]
            for f in fnames:
                try:
                    with open(os.path.join(base, f), "rb") as fh:
                        loc += fh.read().count(b"\n")
                    files += 1
                except OSError:
                    pass
        payloads.append({
            "kind": "desktop", "path": "crates/fabric-gui/src-tauri", "channel": "desktop-artifact",
            "loc": loc, "files": files, "by_language": {},
            "publication_class": ann["payloads"].get("crates/fabric-gui/src-tauri", {}).get(
                "publication_class", "publish"),
            "note": "links GTK/WebKit; ships as a signed bundle, never as a crate",
        })
    gaps = sorted(r for r in PUBLISHABLE_ROOT
                  if os.path.isdir(os.path.join(ROOT, r)) and r not in {p["path"] for p in payloads})
    return sorted(payloads, key=lambda p: -p["loc"]), gaps


def main():
    meta = cargo_metadata()
    ann = load_annotations()
    members = set(meta["workspace_members"])
    by_id = {p["id"]: p for p in meta["packages"]}

    # inbound edges, split by dependency kind
    deps_of = {}
    dev_deps_of = {}
    inbound = {}
    for pid, pkg in by_id.items():
        if pid not in members:
            continue
        for dep in pkg.get("dependencies", []):
            if not dep.get("path"):
                continue
            target = None
            dep_path = os.path.normpath(dep["path"])
            for other_id, other in by_id.items():
                if os.path.normpath(os.path.dirname(other["manifest_path"])) == dep_path:
                    target = other_id
                    break
            if target is None or target == pid:
                continue
            kind = dep.get("kind") or "normal"
            if kind == "dev":
                dev_deps_of.setdefault(pkg["name"], set()).add(by_id[target]["name"])
            else:
                deps_of.setdefault(pkg["name"], set()).add(by_id[target]["name"])
            inbound.setdefault(target, []).append((pkg["name"], kind))

    dag_depth = layers_from_dag(deps_of)

    records = []
    for pid in sorted(members, key=lambda i: by_id[i]["name"]):
        pkg = by_id[pid]
        crate_dir = os.path.dirname(pkg["manifest_path"])
        rel = os.path.relpath(crate_dir, ROOT)
        bins = [t["name"] for t in pkg["targets"] if "bin" in t["kind"]]
        name = pkg["name"]
        layer = apply_bin_altitude(name, bins, derive_layer(name, bins))
        override = ann["members"].get(name, {})
        depth = dag_depth.get(name, 0)

        # Layer precedence: an explicit annotation wins, then the name rule, then dependency
        # position. Depth 0 is unambiguous (nothing internal to depend on). Depth >= 3 means the
        # crate already sits on top of three internal layers, which is application altitude. Every
        # assignment records which signal decided it, so a reader can audit the weak ones.
        layer_basis = "name" if layer != "unclassified" else "unclassified"
        if "layer" in override:
            layer, layer_basis = override["layer"], "annotation"
        elif depth == 0 and layer != "L4":
            layer_basis, layer = ("dag-leaf (name said L0)", "L0") if layer == "L0" else \
                                 (f"dag-leaf (name said {layer})", "L0")
        elif layer == "unclassified" and depth == 0:
            layer, layer_basis = "L0", "dag-leaf"
        elif layer == "unclassified" and depth >= 3:
            layer, layer_basis = "L4", "dag-deep"
        elif layer == "unclassified":
            layer, layer_basis = "L3", "default"
        elif layer in ("L0", "L1") and depth >= 3:
            layer_basis = "name (dag depth contradicts: %d)" % depth

        consumers = inbound.get(pid, [])
        normal_consumers = sum(1 for _n, k in consumers if k == "normal")

        # Packaging prerequisites. `cargo package` refuses a path dependency that carries no
        # version requirement, so an unresolvable-version path dep is a hard R1 blocker. This is
        # the measurable form of "a consumer cannot take one slice without the bulk".
        local_path_deps = [d for d in pkg.get("dependencies", []) if d.get("path")]
        unversioned_path_deps = [d["name"] for d in local_path_deps if d.get("req") == "*"]
        packaging_ready = bool(
            pkg.get("license")
            and pkg.get("publish") != []            # publish = false
            and not unversioned_path_deps
            and override.get("packaging_ready", None) is not False
        )

        if "publication_class" in override:
            pub = override["publication_class"]
        elif layer_basis.startswith("default"):
            pub = "quarantine"
        elif layer == "L4":
            pub = "internal"
        elif packaging_ready and layer in ("L0", "L1", "L2", "L3") and normal_consumers > 0:
            pub = "publish"
        else:
            pub = "internal"

        stability, stability_basis = derive_stability(pkg.get("version"), override)

        records.append({
            "name": name,
            "path": rel,
            "layer": layer,
            "layer_basis": layer_basis,
            "dag_depth": depth,
            "publication_class": pub,
            "channel": "crates.io" if pub == "publish" else "none",
            "version": pkg.get("version"),
            "stability": stability,
            "stability_basis": stability_basis,
            "deps": sorted(deps_of.get(name, ())),
            "dev_deps": sorted(dev_deps_of.get(name, ())),
            "reason": override.get("reason") or REASON.get(layer_basis.split(" (")[0]),
            "loc_src": loc_of_src(crate_dir),
            "bins": bins,
            "lib": any("lib" in t["kind"] for t in pkg["targets"]),
            "license": pkg.get("license"),
            "publish_false": pkg.get("publish") == [],
            "local_path_deps": len(local_path_deps),
            "unversioned_path_deps": len(unversioned_path_deps),
            "consumers": normal_consumers,
            "consumer_names": sorted({n for n, k in consumers if k == "normal"})[:12],
            "packaging_ready": packaging_ready,
        })

    payloads, payload_gaps = discover_payloads(ann)

    # Findings are facts the catalog can prove about itself, so the report never has to re-derive
    # them by hand. They are not judgements: a flat leaf is sometimes exactly right.
    flat = [r["name"] for r in records if r["dag_depth"] == 0]
    # A name rule that claims L1+ while the crate has no internal runtime dependency: the rule is
    # describing role, the graph is describing position, and they disagree. L0 agreements and
    # crates with no rule at all are not contradictions, so they are excluded.
    contradictions = [
        {"name": r["name"], "name_layer": r["layer_basis"].split("name said ")[1].rstrip(")"),
         "layer": r["layer"]}
        for r in records
        if r["layer_basis"].startswith("dag-leaf (name said")
        and r["layer_basis"].split("name said ")[1].rstrip(")") not in ("L0", "unclassified")
    ]
    order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
    layer_of = {r["name"]: r["layer"] for r in records}
    dev_up = []
    for name, deps in dev_deps_of.items():
        for dep in deps:
            if dep in layer_of and order[layer_of[dep]] > order[layer_of[name]]:
                dev_up.append(f"{name}({layer_of[name]}) -> {dep}({layer_of[dep]})")
    findings = {
        "flat_workspace_members": len(flat),
        "flat_workspace_note": "no internal runtime dependency at all: the workspace is flat, not layered",
        "name_rule_above_dag_leaf": sorted(contradictions, key=lambda c: c["name"]),
        "dev_only_upward_edges": sorted(dev_up),
        "publish_blocked_by_unversioned_path_dep": sum(
            1 for r in records if r["publication_class"] == "publish" and r["unversioned_path_deps"] > 0),
    }

    by_layer = {}
    by_class = {}
    for r in records:
        by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
        by_class[r["publication_class"]] = by_class.get(r["publication_class"], 0) + 1

    catalog = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "tools/sdk-catalog/generate.py",
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip(),
        "member_count": len(records),
        "coverage": {
            "classified": sum(v for k, v in by_layer.items() if k != "unclassified"),
            "unclassified": by_layer.get("unclassified", 0),
            "by_layer": by_layer,
            "by_class": by_class,
            "publish_ready": sum(1 for r in records if r["publication_class"] == "publish"),
            "blocked_by_unversioned_path_dep": sum(1 for r in records if r["unversioned_path_deps"] > 0),
            "unversioned_path_dep_edges": sum(r["unversioned_path_deps"] for r in records),
            "publishable_roots_with_no_measured_surface": payload_gaps,
        },
        "members": records,
        "payloads": payloads,
        "findings": findings,
    }

    text = json.dumps(catalog, indent=2, sort_keys=False) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
    else:
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(text)
        cov = catalog["coverage"]
        print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(records)} members, "
              f"{cov['classified']} classified / {cov['unclassified']} unclassified, "
              f"{len(payloads)} non-Rust payloads, {len(payload_gaps)} thin roots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
