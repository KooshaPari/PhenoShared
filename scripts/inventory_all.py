#!/usr/bin/env python3
"""Complete inventory: every live repository, with a proposed action and its basis.

The question this answers is "is there a plan for each one", so every row carries
four facts and one action:

  live repo          the name as GitHub reports it now
  hist               refs preserved under refs/preserved/<repo>/ (0 = none)
  content            where the files live locally, if anywhere
  category           what kind of thing it is
  action             what should happen to it next

Categories are not guesses: they come from the ledger's recorded dispositions
(canonical homes, recovery stores, live products, archives, destinations) and, for
anything unrecorded, from what the repository actually contains.

Usage:
    python inventory_all.py [--csv]
"""
import json
import os
import subprocess
import sys

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"
SHARED = "C:/Users/koosh/PhenoShared"

CANONICAL = {"PhenoShared", "PhenoRegistry"}

RECOVERY = {
    "AgilePlus-rb-archive-20261106", "Melosviz-rb-archive-20261106",
    "PhenoFastMCP-rb-archive-20261106", "PhenoProc-archive-20261106",
    "PhenoVCS-rb-archive-20261106", "Pine-rb-archive-20261106",
    "Quillr-rb-archive-20261106", "Sidekick-archive-20261106",
    "Sidekick-rb-archive-20261108", "Stashly-archive-20261106",
    "Stashly-rb-archive-20261106", "Stashly-rb-archive-20261106-exact",
    "Tasken-archive-20261106", "Tasken-archive-20261106-exact",
    "Tasken-rb-archive-20261108", "Tracera-rb-archive-20261106",
    "exports-temp-archive-20261108", "forgecode-rb-archive-20261106",
    "phenotype-archives-20261108",
    "phenotype-registry-rb-archive-20261106", "work-archive-20261105",
    "zz-Parpoura-rb-archive-20261106", "zz-QuadSGM-rb-archive-20261106",
    "zz-localbase-rb-archive-20261106",
    "zz-rich-cli-kit-archive-20261106",
}

# Ledger: live products, not absorb targets without a specific instruction.
LIVE_PRODUCTS = {
    "Civis", "OmniRoute", "PhenoMLX", "Tracera", "AgilePlus", "Dino", "KCode",
    "PhenoTooling", "ShareCLI", "WorldSphereMod", "KooshaPari", "Khostty",
    "Portage", "CivicWarfare", "PhenoBot", "Melosviz", "herdr", "PhenoDesign",
    "HeliosLab", "PhenoAI", "PhenoLab", "PhenoFabric", "kimaki",
    "claude-remember", "ratatui", "shopping-home", "heliosApp",
}

# Ledger: explicitly leave alone.
LEAVE_ALONE = {"cmux", "Substrate", "argis-extensions", "Pine"}

# Ledger: archives and evidence, the only copy of what they hold.
EVIDENCE = {
    "zz-archive-grapheon", "zz-archive-AgilePlus-recovery-evidence",
    "zz-archive-4sgm-archive", "zz-zz-agentcheck-PhenoInfra",
    "zz-pause-inc-AgsLag", "zz-pause-ref-AtomsTech",
    "zz-pause-inc-FocalPoint", "zz-pause-unk-Thegent",
    "zz-archive-agileplus-spec-harmonizer-tool", "zz-archive-pheno-drift-detector",
    "zz-archive-pheno-predict", "zz-archive-source-drops-2026-07",
    "zz-zz-agentcheck-PhenoGfx", "zz-zz-agentcheck-docs-5",
    "zz-zz-agentcheck-zz-pause-Agentora",
}

# Ledger: destinations the archives belong in, not absorb targets themselves.
DESTINATIONS = {"PhenoApps", "zz-pause-inc-QuadSGM", "zz-pause-inc-Parpoura",
                "zz-pause-localbase", "zz-pause-Localbase"}

# Repositories whose content is partly present in PhenoShared under a name that
# does not match the repository name. Found by searching the whole tree rather
# than the three conventional absorption locations; the byte-level coverage is
# measured in docs/absorption-ledger/REPO-INVENTORY-2026-11-15.md.
PARTIAL_CONTENT = {
    "hwledger": "crates/hwledger",
    "hexakit": "crates/hexa-kit",
}

# Repositories whose content was searched for across the whole tree and found
# nowhere. Verified 2026-11-16, not merely absent from the usual directories.
CONFIRMED_UNABSORBED = {
    "argis-extensions-preserved-20261114", "claude-plugins-official",
    "cliproxyapi-plusplus", "slipstream", "HarnessDesk", "StealthStartup",
    "chatta", "phenoreg-browser-audit", "zz-ref-HeliosCLI", "zz-ref-HeliosLite",
}

# Repositories recreated or imported on 2026-11-14.
RESTORED = {
    "BytePort", "dagrun", "harness-ops", "rule30-research",
    "zz-aa-dep-AirLock", "audit-system", "PhenoVCS", "cvp-fixture",
    "phenotype-landing", "Personal",
}
SNAPSHOTS = set()  # filled at runtime for names starting with audit-snapshot-


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def live_repos():
    code, out, err = sh(["gh", "repo", "list", OWNER, "--limit", "400",
                         "--json", "name,isPrivate,diskUsage"])
    if code != 0:
        raise SystemExit("gh repo list failed: %s" % err[:200])
    return {x["name"]: x for x in json.loads(out)}


def normalize_name(name):
    return "".join(ch for ch in name.lower() if ch.isalnum())


def build_local_index(base=SHARED, max_depth=4):
    """Map normalised directory names to matching relative paths under base.

    Walks to a bounded depth so content present anywhere in the conventional
    layout (or in renamed locations such as crates/*) is found by content/name,
    not by a fixed directory probe.
    """
    index = {}
    base = os.path.normpath(base)
    base_depth = base.count(os.sep)
    for root, dirs, _ in os.walk(base, topdown=True):
        depth = os.path.normpath(root).count(os.sep) - base_depth
        if depth >= max_depth:
            dirs[:] = []
            continue
        for d in dirs:
            key = normalize_name(d)
            if not key:
                continue
            rel = os.path.relpath(os.path.join(root, d), base).replace("\\", "/")
            index.setdefault(key, []).append(rel)
    return index


def preserved_counts():
    code, out, err = sh(["git", "ls-remote", "--refs",
                         "https://github.com/%s/%s.git" % (OWNER, REGISTRY)])
    if code != 0:
        raise SystemExit("registry ls-remote failed: %s" % err[:200])
    counts = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        _, _, name = line.partition("\t")
        parts = name.split("/")
        if len(parts) >= 5 and parts[1] == "preserved":
            counts[parts[2]] = counts.get(parts[2], 0) + 1
    return counts


def registry_trees():
    """Repositories that have an absorbed *content* tree, not just an entry.

    `repos/<name>/` exists for two different reasons: a `tree/` subdirectory
    holding the files, or only a `history/` subdirectory holding a bundle. Treating
    presence of the parent as evidence of content classified
    phenotype-canonicalization as delete-eligible when the registry holds only its
    history, and its files were in PhenoShared all along.
    """
    code, out, _ = sh(["gh", "api", "repos/%s/%s/contents/repos" % (OWNER, REGISTRY),
                       "--jq", ".[].name"])
    if code != 0:
        return set()
    names = [l.strip() for l in out.splitlines() if l.strip()]
    with_tree = set()
    for name in names:
        code, out, _ = sh(["gh", "api",
                           "repos/%s/%s/contents/repos/%s" % (OWNER, REGISTRY, name),
                           "--jq", '.[].name'])
        if code == 0 and "tree" in {l.strip() for l in out.splitlines()}:
            with_tree.add(name)
    return with_tree


def local_roots(name, index=None):
    """Directories whose content matches the repository name.

    Always keeps the three fixed absorption locations when present, then adds any
    bounded-depth matches found by normalised name (including hyphen/underscore
    transforms via non-alphanumeric stripping). Any match counts as content
    present and is recorded so the row shows which path matched.
    """
    hits = []
    seen = set()

    def add(path):
        rel = (os.path.relpath(path, SHARED).replace("\\", "/")
               if os.path.isabs(path) else path.replace("\\", "/"))
        if rel not in seen:
            seen.add(rel)
            hits.append(rel)

    for cand in (os.path.join(SHARED, "absorption", name),
                 os.path.join(SHARED, "_archived", name),
                 os.path.join(SHARED, "absorption-residue-" + name)):
        if os.path.isdir(cand):
            add(cand)
    if index is not None:
        for rel in index.get(normalize_name(name), []):
            add(os.path.join(SHARED, rel))
    return hits


# Measured coverage, repository -> (action, reason). These override the generic
# classification because they are the result of comparing actual content, not of
# looking for a directory. See docs/absorption-ledger/.
COVERAGE = {
    "host-credentials": ("delete-eligible",
                         "registry tree covers 5 of 5 files exactly"),
    "host-ops": ("absorb-remainder",
                 "registry tree lacks 172 live files and 48 differ"),
    "phenotype-canonicalization": ("delete-eligible",
                                   "absorption/ covers 43 of 44; only verification/unit-tests.log absent"),
}


def classify(name, has_hist, roots, reg_tree):
    if name in CANONICAL:
        return "canonical", "keep", "one of the two canonical homes"
    if name in RECOVERY:
        return "recovery store", "keep", "only surviving copy of a deleted upstream"
    if name in LEAVE_ALONE:
        return "leave alone", "keep", "recorded as out of scope"
    if name in LIVE_PRODUCTS:
        return "live product", "keep", "live product, declined as an absorb target"
    if name in EVIDENCE:
        return "evidence/archive", "keep", "holds the only copy of what it records"
    if name in DESTINATIONS:
        return "destination", "keep", "a home the archives belong in"
    if name in COVERAGE:
        action, reason = COVERAGE[name]
        return "measured coverage", action, reason
    if name.startswith("audit-snapshot-"):
        return "snapshot import", "decide", "content unique vs a live repo; review then absorb or keep"
    if name in RESTORED:
        return "restored 2026-11-14", "decide", "recreated from a local copy; content decision needed"
    if name in PARTIAL_CONTENT:
        where = ",".join(roots) if roots else PARTIAL_CONTENT[name]
        return ("partially absorbed", "absorb-remainder",
                "content partly lives in %s; the remainder is unabsorbed" % where)
    if has_hist and (roots or reg_tree):
        return "absorbed + preserved", "delete-eligible", "history preserved and content present locally"
    if has_hist:
        where = ("content confirmed nowhere in PhenoShared"
                 if name in CONFIRMED_UNABSORBED
                 else "history preserved, no absorbed content found")
        return "history only", "absorb-or-keep", where
    return "unpreserved", "preserve-first", "no preserved refs; preserve before any decision"


def main():
    as_csv = "--csv" in sys.argv
    live = live_repos()
    counts = preserved_counts()
    reg_trees = registry_trees()
    local_index = build_local_index()

    rows = []
    for name in sorted(live):
        has_hist = name in counts
        roots = local_roots(name, local_index)
        reg = name in reg_trees
        cat, action, reason = classify(name, has_hist, roots, reg)
        rows.append({
            "repo": name,
            "priv": "priv" if live[name]["isPrivate"] else "pub",
            "mb": round(live[name]["diskUsage"] / 1024.0, 1),
            "refs": counts.get(name, 0),
            "regtree": "yes" if reg else "",
            "local": ",".join(roots),
            "category": cat,
            "action": action,
            "reason": reason,
        })

    if as_csv:
        cols = ["repo", "priv", "mb", "refs", "regtree", "local", "category", "action"]
        print(",".join(cols))
        for r in rows:
            print(",".join('"%s"' % r[c] if isinstance(r[c], str) else str(r[c])
                           for c in cols))
        return 0

    print("live repositories: %d" % len(rows))
    print("preserved namespaces: %d" % len(counts))
    print("registry content trees: %d" % len(reg_trees))
    print()
    print("%-40s %-5s %8s %5s %-4s %-22s %s"
          % ("repo", "vis", "MB", "refs", "reg", "category", "action"))
    print("-" * 128)
    for r in rows:
        print("%-40s %-5s %8.1f %5d %-4s %-22s %s"
              % (r["repo"][:40], r["priv"], r["mb"], r["refs"],
                 r["regtree"], r["category"], r["action"]))
    print()
    actions = {}
    for r in rows:
        actions[r["action"]] = actions.get(r["action"], 0) + 1
    print("action summary:")
    for a in sorted(actions):
        print("  %-18s %d" % (a, actions[a]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
