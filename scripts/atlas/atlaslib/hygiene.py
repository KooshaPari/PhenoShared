"""Rule-violation and debris detection.

Each check corresponds to a rule the repository states about itself, or to a
class of absorbed/archived material that should not be silently accumulating.
Nothing here fixes anything; the report only records what it finds so the
findings can be triaged deliberately.
"""

from __future__ import annotations

import hashlib
import os
from collections import Counter, defaultdict

from .definitions import (
    ARBITRARY_NUMBER,
    ARCHIVE_TREES,
    BAD_NAME_TOKENS,
    BAD_TEST_SUFFIX,
    BUILD_EXT,
    DEBRIS_RE,
    CODE_EXT,
    LIMIT_HARD,
    LIMIT_TARGET,
    ROOT_DOC_ALLOW,
    STANDARD_DOC_NAMES,
    STRAY_DOC_NOISE,
)

TEST_EXT = ("py", "ts", "tsx", "js", "jsx", "go", "rb")


def _ext(rel: str) -> str:
    return os.path.splitext(rel)[1].lstrip(".").lower()


def size_breaches(files: dict[str, dict]):
    """Line-count breaches, split by whether the rule actually applies.

    The repository's rule targets source modules. Committed patches, binary
    blobs, generated JSON plans, and vendored reference dumps can have huge
    newline counts without being "modules", so they are reported separately
    rather than inflating every headline number.
    """
    over_target = sorted(
        ((rel, rec["loc"]) for rel, rec in files.items() if rec["loc"] > LIMIT_TARGET),
        key=lambda item: (-item[1], item[0]),
    )
    over_hard = [item for item in over_target if item[1] > LIMIT_HARD]

    def is_source(rel, rec):
        return rec["kind"] == "reg" and not rec["binary"] and _ext(rel) in CODE_EXT

    src_target = [(rel, loc) for rel, loc in over_target if is_source(rel, files[rel])]
    src_hard = [(rel, loc) for rel, loc in over_hard if is_source(rel, files[rel])]

    def area(rel):
        return rel.split("/", 1)[0] if "/" in rel else "(repo root)"

    areas = sorted(
        ((a, sum(1 for p, _ in src_target if area(p) == a),
          sum(1 for p, _ in src_hard if area(p) == a))
         for a in {area(p) for p, _ in src_target}),
        key=lambda row: (-row[1], row[0]),
    )
    return {
        "over_target": over_target,
        "over_hard": over_hard,
        "src_target": src_target,
        "src_hard": src_hard,
        "src_areas": areas,
    }


def filename_violations(files: dict[str, dict]):
    """Non-canonical test names and temporal-suffix names."""
    bad_tests, bad_names = [], []
    for rel, rec in sorted(files.items()):
        base = os.path.basename(rel)
        stem, ext = os.path.splitext(base)
        low = stem.lower()
        if ext not in (".rs", *("." + e for e in TEST_EXT)):
            continue
        testish = base.startswith("test_") or "/tests/" in rel or low.endswith("_test")
        if testish:
            hit = next((t for t in BAD_TEST_SUFFIX if low.endswith(t)), None)
            if hit:
                bad_tests.append((rel, f"test-variant suffix `{hit}` — variants belong "
                                       "in fixtures and markers, not file names"))
            elif ARBITRARY_NUMBER.search(low):
                bad_tests.append((rel, "arbitrary numbering in test filename"))
        for token in BAD_NAME_TOKENS:
            if low.endswith(token):
                bad_names.append((rel, f"temporal suffix `{token}` — versioning belongs in git"))
                break
    # A Rust integration test must be named test_<concern>.rs. Helper modules
    # that define no tests (common/mod.rs, helpers.rs) are not test files and
    # are deliberately not flagged.
    noncanonical = sorted(
        rel for rel, rec in files.items()
        if "/tests/" in rel and rel.endswith(".rs")
        and rec["tests"] > 0
        and not os.path.basename(rel).startswith("test_")
    )
    return sorted(set(bad_tests)), sorted(set(bad_names)), noncanonical


def stray_docs(files: dict[str, dict]):
    """Classify markdown outside `docs/`.

    A component's own README/CHANGELOG sitting beside its manifest is normal
    repository content, so it is counted separately rather than reported as a
    violation. What remains is docs living somewhere with no owning component
    and no `docs/` home: the case the repository's doc rule actually targets.
    """
    root_docs, component_docs, stray_nested = [], [], []
    for rel in sorted(files):
        if not rel.endswith((".md", ".mdx")):
            continue
        if rel.startswith("docs/"):
            continue
        base = os.path.basename(rel)
        if "/" not in rel:
            if rel not in ROOT_DOC_ALLOW:
                root_docs.append(rel)
            continue
        if base in STANDARD_DOC_NAMES:
            component_docs.append(rel)
        else:
            stray_nested.append(rel)
    noisy = [rel for rel in root_docs if STRAY_DOC_NOISE.search(rel)]
    return root_docs, component_docs, stray_nested, noisy


def archive_trees(files: dict[str, dict]):
    counts, sizes = Counter(), Counter()
    for rel, rec in files.items():
        for tree in ARCHIVE_TREES:
            if rel.startswith(tree):
                counts[tree] += 1
                sizes[tree] += rec["size"]
                break
    return counts, sizes


# The generator and its own output legitimately contain the marker as a search
# needle, so they are excluded from the redaction finding rather than reported
# as offenders.
SELF_EXCLUDE = ("scripts/atlas/", "docs/atlas/codebase/")


def redaction_markers(files: dict[str, dict]):
    hits = [
        (rel, rec["redacted"]) for rel, rec in files.items()
        if rec["redacted"] and not rel.startswith(SELF_EXCLUDE)
    ]
    hits.sort(key=lambda item: (-item[1], item[0]))
    return hits


def committed_artifacts(files: dict[str, dict]):
    found = []
    for rel, rec in sorted(files.items()):
        base = os.path.basename(rel)
        ext = _ext(rel)
        if ext in BUILD_EXT:
            reason = f"build/artifact extension `.{ext}`"
        elif "/.zig-cache/" in rel or "/target/" in rel or "/node_modules/" in rel:
            reason = "build cache or vendored dependency tree"
        elif rec["binary"]:
            reason = "committed executable (ELF/Mach-O/PE magic)"
        elif rec["kind"] == "link":
            continue
        else:
            continue
        found.append((rel, reason, rec["size"]))
    found.sort(key=lambda item: (-item[2], item[0]))
    return found


def duplicate_content(root: str, files: dict[str, dict], min_size: int = 16):
    """Exact-content duplicates: size prefilter, then MD5 over full content."""
    by_size: dict[int, list[str]] = defaultdict(list)
    for rel, rec in files.items():
        if rec["kind"] == "reg" and rec["readable"] and rec["size"] >= min_size:
            by_size[rec["size"]].append(rel)
    digests: dict[str, list[str]] = defaultdict(list)
    for group in by_size.values():
        if len(group) < 2:
            continue
        for rel in group:
            try:
                with open(os.path.join(root, rel), "rb") as handle:
                    digests[hashlib.md5(handle.read()).hexdigest()].append(rel)
            except OSError:
                continue
    groups = [
        (sorted(members), files[members[0]]["size"])
        for members in digests.values() if len(members) > 1
    ]
    groups.sort(key=lambda item: (-(item[1] * (len(item[0]) - 1)), item[0][0]))
    wasted = sum(size * (len(members) - 1) for members, size in groups)
    return groups, wasted


def debris(files: dict[str, dict]):
    paths = sorted(rel for rel in files if DEBRIS_RE.search(rel))
    buckets = Counter()
    for rel in paths:
        if "zz-archive" in rel or "zz_archive" in rel:
            buckets["zz-archive tree"] += 1
        elif "absorbed" in rel:
            buckets["absorbed-* path"] += 1
        elif "/wt-" in rel:
            buckets["/wt- worktree snapshot"] += 1
        elif "_archived" in rel:
            buckets["_archived tree"] += 1
        else:
            buckets[".orig leftover"] += 1
    return paths, buckets


def collect(root: str, files: dict[str, dict], packages: dict[str, dict]) -> dict:
    breaches = size_breaches(files)
    bad_tests, bad_names, noncanonical = filename_violations(files)
    root_docs, component_docs, stray_nested, noisy_docs = stray_docs(files)
    archives, archive_bytes = archive_trees(files)
    duplicates, wasted = duplicate_content(root, files)
    debris_paths, debris_buckets = debris(files)

    links = sorted(rel for rel, rec in files.items() if rec["kind"] == "link")
    unreadable = sorted(rel for rel, rec in files.items()
                        if rec["kind"] in ("missing", "other"))
    zero = sorted(rel for rel, rec in files.items()
                  if rec["kind"] == "reg" and rec["size"] == 0)

    return {
        **breaches,
        "bad_test_names": bad_tests,
        "bad_names": bad_names,
        "noncanon_test_files": noncanonical,
        "stray_docs_root": root_docs,
        "component_docs": component_docs,
        "stray_docs_nested": stray_nested,
        "stray_docs_noise": noisy_docs,
        "archive_trees": archives,
        "archive_bytes": archive_bytes,
        "redacted": redaction_markers(files),
        "artifacts": committed_artifacts(files),
        "big_files": sorted(
            ((rel, rec["size"]) for rel, rec in files.items() if rec["size"] > 1 << 20),
            key=lambda item: (-item[1], item[0]),
        ),
        "duplicate_groups": duplicates,
        "duplicate_wasted": wasted,
        "no_trailing_nl": sorted(
            rel for rel, rec in files.items()
            if rec["kind"] == "reg" and rec["size"] and not rec["nl_end"] and not rec["binary"]
        ),
        "no_desc": sorted(
            directory for directory, package in packages.items()
            if package["kind"] == "member" and not package["desc"]
        ),
        "symlinks": links,
        "unreadable": unreadable,
        "zero_byte": zero,
        "debris_paths": debris_paths,
        "debris_buckets": debris_buckets,
    }
