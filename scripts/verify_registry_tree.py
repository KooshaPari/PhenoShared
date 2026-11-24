#!/usr/bin/env python3
"""Verify a PhenoRegistry absorbed tree against a source repository git tree.

This compares git tree entries over the GitHub API only. It does not clone or
read local repositories. Paths are compared relative to --path: the registry
prefix is stripped before comparison.

Usage:
    python verify_registry_tree.py \
        --source-repo AgilePlus-rb-archive-20261106 \
        --source-ref 699f61aa \
        --registry-ref refs/heads/recover/agileplus-699f61aa
"""
import argparse
import base64
import binascii
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_OWNER = "KooshaPari"
DEFAULT_REGISTRY = "KooshaPari/PhenoRegistry"
LFS_PREFIX = "version https://git-lfs.github.com/spec/v1"
LFS_SIZE_CUTOFF = 300
RESIDUAL_PRINT_CAP = 50
TLS_MARKERS = (
    "tls handshake timeout",
    "tls handshake",
    "i/o timeout",
    "connection reset by peer",
    "eof",
)


class ApiFailure(RuntimeError):
    """A gh api call failed after the allowed retry."""


def run_gh(args):
    """Run one gh command, retrying once when the failure looks like TLS.

    Returns (code, stdout, stderr, retries). Never uses a shell.
    """
    cmd = ["gh", "api"] + args
    for attempt in range(2):
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        lowered = proc.stderr.lower()
        tls = proc.returncode != 0 and any(marker in lowered for marker in TLS_MARKERS)
        if not tls or attempt == 1:
            return proc.returncode, proc.stdout, proc.stderr, attempt
        print("TLS failure in gh api; retrying once: %s" % " ".join(args[:3]))
        time.sleep(1)
    return 1, "", "unreachable", 1


def gh_api(args, label):
    code, out, err, retries = run_gh(args)
    if code != 0:
        raise ApiFailure("%s failed (exit=%d, retries=%d): %s" % (label, code, retries, err.strip()))
    return out


def normalize_repo(repo, default_owner=DEFAULT_OWNER):
    repo = repo.strip().strip("/")
    if "/" in repo:
        parts = repo.split("/", 1)
        return parts[0], parts[1], parts[1]
    return default_owner, repo, repo


def resolve_ref(repo_slug, ref):
    """Return the full commit SHA for a branch, tag, or SHA via gh api."""
    endpoint = "repos/%s/commits/%s" % (repo_slug, ref)
    out = gh_api([endpoint, "--jq=.sha"], "resolve %s @ %s" % (repo_slug, ref))
    sha = out.strip().splitlines()[0].strip() if out.strip() else ""
    if not sha:
        raise ApiFailure("empty SHA resolving %s @ %s" % (repo_slug, ref))
    return sha


def parse_tree_rows(raw):
    """Parse --jq TSV rows: path, mode, type, sha, optional size."""
    rows = []
    for line in raw.splitlines():
        fields = line.split("\t")
        if len(fields) < 4:
            continue
        path, mode, obj_type, sha = fields[:4]
        size = None
        if len(fields) >= 5 and fields[4] != "":
            try:
                size = int(fields[4])
            except ValueError:
                size = None
        rows.append({"path": path, "mode": mode, "type": obj_type, "sha": sha, "size": size})
    return rows


def fetch_tree(repo_slug, tree_sha, subtree_path=None):
    """Fetch one tree. Returns (rows, truncated).

    Uses the compact no-space --jq filter required by this host. When
    subtree_path is set, paths returned by the API are prefixed with that path
    so callers get repository-root-relative paths.
    """
    endpoint = "repos/%s/git/trees/%s?recursive=1" % (repo_slug, tree_sha)
    raw = gh_api([endpoint, "--jq=.tree[]|[.path,.mode,.type,.sha,.size]|@tsv"],
                 "tree %s @ %s" % (repo_slug, tree_sha))
    trunc_raw = gh_api([endpoint, "--jq=.truncated"],
                       "truncated flag %s @ %s" % (repo_slug, tree_sha))
    truncated = trunc_raw.strip().lower() == "true"
    rows = parse_tree_rows(raw)
    if subtree_path:
        prefix = subtree_path.strip("/")
        for row in rows:
            row["path"] = prefix + "/" + row["path"]
    return rows, truncated


def fetch_commit_tree_sha(repo_slug, commit_sha):
    out = gh_api(["repos/%s/commits/%s" % (repo_slug, commit_sha), "--jq=.commit.tree.sha"],
                 "commit tree %s @ %s" % (repo_slug, commit_sha))
    tree_sha = out.strip()
    if not tree_sha:
        raise ApiFailure("empty tree SHA for %s @ %s" % (repo_slug, commit_sha))
    return tree_sha


def enumerate_tree(repo_slug, tree_sha, root_path=None, stats=None):
    """Enumerate a tree with recursive API calls and per-subtree fallback.

    Returns a list of rows with root-relative paths. If a response is marked
    truncated, that subtree is enumerated one level at a time and each child
    tree is fetched separately.
    """
    if stats is None:
        stats = {"truncated": 0}
    rows, truncated = fetch_tree(repo_slug, tree_sha, root_path)
    if not truncated:
        return rows

    stats["truncated"] += 1
    print("WARNING: tree response truncated for %s @ %s%s; "
          "falling back to per-subtree enumeration"
          % (repo_slug, tree_sha, (" at " + root_path) if root_path else ""))

    # The recursive response may be incomplete; discard it and walk explicitly.
    endpoint = "repos/%s/git/trees/%s" % (repo_slug, tree_sha)
    raw = gh_api([endpoint, "--jq=.tree[]|[.path,.mode,.type,.sha]|@tsv"],
                 "shallow tree %s @ %s" % (repo_slug, tree_sha))
    result = []
    for fields in (line.split("\t") for line in raw.splitlines()):
        if len(fields) < 4:
            continue
        path, mode, obj_type, sha = fields[:4]
        full_path = (root_path.strip("/") + "/" + path) if root_path else path
        if obj_type == "tree":
            child = enumerate_tree(repo_slug, sha, full_path, stats)
            result.extend(child)
        elif obj_type in ("blob", "commit"):
            result.append({"path": full_path, "mode": mode, "type": obj_type,
                           "sha": sha, "size": None})
    return result


def locate_registry_prefix(registry_slug, commit_sha, path):
    """Return (tree_sha, normalized_prefix) for the absorbed tree path.

    Path traversal uses non-recursive tree API calls so no local disk or git
    work is involved. The prefix must resolve to a tree object.
    """
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        raise ApiFailure("--path must name a registry tree, not the repository root")
    current_sha = fetch_commit_tree_sha(registry_slug, commit_sha)
    for part in parts:
        endpoint = "repos/%s/git/trees/%s" % (registry_slug, current_sha)
        raw = gh_api([endpoint, "--jq=.tree[]|[.path,.mode,.type,.sha]|@tsv"],
                     "path lookup %s/%s" % (registry_slug, part))
        match = None
        for fields in (line.split("\t") for line in raw.splitlines()):
            if len(fields) >= 4 and fields[0] == part and fields[2] == "tree":
                match = fields[3]
                break
        if match is None:
            raise ApiFailure("registry path not found or not a tree: %s (at %s)" % (path, part))
        current_sha = match
    return current_sha, "/".join(parts)


def split_entries(rows):
    """Split rows into blobs and gitlinks. Trees are intentionally ignored."""
    blobs = {}
    gitlinks = {}
    for row in rows:
        if row["mode"] in ("100644", "100755") and row["type"] == "blob":
            blobs[row["path"]] = row
        elif row["mode"] == "160000" or (row["type"] == "commit" and row["mode"] == "160000"):
            gitlinks[row["path"]] = row
    return blobs, gitlinks


def is_lfs_pointer(blob):
    """Check a registry blob via gh api; missing size is always a candidate."""
    if blob.get("size") is not None and blob["size"] >= LFS_SIZE_CUTOFF:
        return False
    repo_slug = blob["_repo"]
    raw = gh_api(["repos/%s/git/blobs/%s" % (repo_slug, blob["sha"]), "--jq=.content"],
                 "blob %s" % blob["sha"])
    try:
        decoded = base64.b64decode("".join(raw.split()), validate=True).decode("utf-8", "replace")
    except (binascii.Error, ValueError) as exc:
        print("WARNING: could not decode blob %s for LFS check: %s" % (blob["sha"], exc))
        return False
    first_line = decoded.splitlines()[0].strip() if decoded.splitlines() else ""
    return first_line == LFS_PREFIX


def print_residual(label, paths):
    if not paths:
        return
    print("%s (%d):" % (label, len(paths)))
    for path in paths[:RESIDUAL_PRINT_CAP]:
        print("  %s" % path)
    extra = len(paths) - RESIDUAL_PRINT_CAP
    if extra > 0:
        print("  ... and %d more" % extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--registry-repo", default=DEFAULT_REGISTRY)
    parser.add_argument("--registry-ref", required=True)
    parser.add_argument("--path", default=None,
                        help="absorbed tree path (default repos/<source-repo>/tree)")
    parser.add_argument("--source-owner", default=DEFAULT_OWNER,
                        help="owner used when --source-repo is a bare name")
    args = parser.parse_args()

    src_owner, src_name, src_basename = normalize_repo(args.source_repo, args.source_owner)
    source_slug = "%s/%s" % (src_owner, src_name)
    registry_slug = args.registry_repo
    path = args.path or "repos/%s/tree" % src_basename

    try:
        source_sha = resolve_ref(source_slug, args.source_ref)
        registry_sha = resolve_ref(registry_slug, args.registry_ref)

        src_stats = {"truncated": 0}
        src_rows = enumerate_tree(source_slug, fetch_commit_tree_sha(source_slug, source_sha),
                                  stats=src_stats)
        reg_root_sha, prefix = locate_registry_prefix(registry_slug, registry_sha, path)
        reg_stats = {"truncated": 0}
        reg_rows = enumerate_tree(registry_slug, reg_root_sha, prefix, stats=reg_stats)
        prefix_with_slash = prefix + "/"
        for row in reg_rows:
            if row["path"].startswith(prefix_with_slash):
                row["path"] = row["path"][len(prefix_with_slash):]
            elif row["path"] == prefix:
                row["path"] = ""

        source_blobs, source_gitlinks = split_entries(src_rows)
        reg_blobs, reg_gitlinks = split_entries(reg_rows)
        for blob in reg_blobs.values():
            blob["_repo"] = registry_slug

        source_keys = set(source_blobs) | set(source_gitlinks)
        registry_keys = set(reg_blobs) | set(reg_gitlinks)
        source_only = sorted(source_keys - registry_keys)
        registry_only = sorted(registry_keys - source_keys)
        matched = sorted(source_keys & registry_keys)
        residual = len(source_only) + len(registry_only)
        source_gitlink_pairs = {name: row["sha"] for name, row in source_gitlinks.items()}
        registry_gitlink_pairs = {name: row["sha"] for name, row in reg_gitlinks.items()}

        pointer_count = 0
        pointers_reported = True
        candidates = [b for b in reg_blobs.values()
                      if b.get("size") is None or b["size"] < LFS_SIZE_CUTOFF]
        print("LFS candidates=%d" % len(candidates))
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(is_lfs_pointer, blob): blob for blob in candidates}
            for completed in as_completed(futures):
                try:
                    if completed.result():
                        pointer_count += 1
                except ApiFailure as exc:
                    pointers_reported = False
                    print("WARNING: LFS pointer check incomplete: %s" % exc)

        print("source=%s registry=%s prefix=%s matched=%d"
              % (source_sha, registry_sha, prefix, len(matched)))
        print("truncated_responses source=%d registry=%d"
              % (src_stats["truncated"], reg_stats["truncated"]))
        print_residual("SOURCE_ONLY", source_only)
        print_residual("REGISTRY_ONLY", registry_only)
        print("GITLINKS source=%s" % sorted(source_gitlinks.items()))
        print("GITLINKS registry=%s" % sorted(reg_gitlinks.items()))

        print("VERIFIED %s source=%s registry=%s blobs=%d/%d gitlinks=%d residual=%d pointers=%d"
              % (src_name, source_sha, registry_sha, len(source_blobs), len(reg_blobs),
                 len(reg_gitlinks), residual, pointer_count))

        gitlink_sha_diff = {name for name in source_gitlink_pairs.keys() & registry_gitlink_pairs.keys()
                            if source_gitlink_pairs[name] != registry_gitlink_pairs[name]}
        gitlink_mismatch = source_gitlink_pairs != registry_gitlink_pairs
        failed = []
        if residual != 0:
            failed.append("residual=%d" % residual)
        if gitlink_mismatch:
            failed.append("gitlink lists differ")
        if gitlink_sha_diff:
            failed.append("gitlink SHAs differ: %s" % ", ".join(sorted(gitlink_sha_diff)))
        if not pointers_reported:
            failed.append("pointer count not reported")
        if failed:
            print("FAILED: %s" % ", ".join(failed))
            return 1
        return 0
    except ApiFailure as exc:
        print("FAILED: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
