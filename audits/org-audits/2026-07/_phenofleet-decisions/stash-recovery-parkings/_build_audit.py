#!/usr/bin/env python3
"""
Stash Recovery Audit Builder — 2026-07-15

Constructs wip/2026-07-15-stash-NNN-<slug> alias branches for every
prior-recovered stash that lives as legacy/stash-* on remote, then pushes
them and writes the audit JSON.

Strategy:
  1. Read `.research-dirty-work-2026-07-15.md` Section 3 for the canonical
     list of stashes per repo (the "expected" set).
  2. For every repo, find existing remote branches matching:
       - legacy/stash-N-...-2026-07-15  (per-stash capture branches)
       - legacy/<repo>-stashes-snapshot-2026-07-15  (full-snapshot branches)
  3. For each capture branch, create a local wip/ alias at the same SHA,
     then push it. Try origin first (read-only on some mirrors), then
     koosha-https (GH token-based HTTPS push to KooshaPari/<repo>).
  4. The OmniRoute 3-way mirror cluster all share the same content — apply
     to OmniRoute-superroot-recovery and skip the other two (next fetch
     will sync).
  5. phenotype-apps-L39-wt and phenotype-registry are forks/mirrors of
     phenotype-apps / phenotype-shared — skip them, document why.
  6. Write `.airlock-stash-recovery-2026-07-15.json`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---- Configuration --------------------------------------------------------

REPOS_DIR = Path("/Users/kooshapari/CodeProjects/Phenotype/repos")
DATE_TAG = "2026-07-15"
AUDIT_PATH = REPOS_DIR / f".airlock-stash-recovery-{DATE_TAG}.json"
PARKINGS_DIR = REPOS_DIR / "_phenofleet-decisions" / "stash-recovery-parkings"

# Mirror clusters: skip these to avoid three-way duplication.
# The "primary" is the one we run the recovery on.
MIRROR_CLUSTERS = {
    "omni": {
        "primary": "OmniRoute-superroot-recovery",
        "skipped": ["OmniRoute", "OmniRoute-frontend-svelte-2026-07-05"],
        "note": "Three-way mirror of same content per research report; only primary "
                "gets new wip/ branches (next git fetch will sync the others).",
    },
    "phenotype-apps-mirror": {
        "primary": "phenotype-apps",
        "skipped": ["phenotype-apps-L39-wt", "phenotype-apps-main"],
        "note": "phenotype-apps-L39-wt / -main are worktree copies of phenotype-apps. "
                "Push via primary only.",
    },
    "phenotype-shared-mirror": {
        "primary": "phenotype-shared",
        "skipped": ["phenotype-registry", "phenotype-shared-archive"],
        "note": "phenotype-registry is a fork of phenotype-shared. Mirror cluster — "
                "push via primary only.",
    },
    "pheno-tracing-mirror": {
        "primary": "pheno-tracing",
        "skipped": ["pheno-tracing-t24"],
        "note": "pheno-tracing-t24 is a snapshot mirror; primary pheno-tracing carries "
                "the canonical wip/ branches.",
    },
}

# Repo-name -> upstream push target mapping. Used when a checkout's
# local directory name doesn't match the canonical github repo (e.g.
# worktrees, mirrors). Keys are local repo names; values are the
# github <owner>/<repo> we should push the wip/ branches to.
KOOSHA_PUSH_TARGET_OVERRIDES = {
    "omniroute-upstream-work": "KooshaPari/OmniRoute",
    "OmniRoute-frontend-svelte-2026-07-05": "KooshaPari/OmniRoute",
}

SKIP_REPOS = {"phenotype-monorepo-state-archive"}  # not part of 17-repo scope


# ---- Utilities ------------------------------------------------------------


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def slugify(text: str, max_len: int = 50) -> str:
    """Convert stash message fragment to URL-safe slug (alnum + dash)."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    # Trim leading 'wip-' and 'auto-' and 'capture-' prefixes
    s = re.sub(r"^[-]+", "", s)
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "stash"


def run(cmd: list, cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    """Run subprocess. Returns (rc, stdout, stderr).

    Always uses REPOS_DIR as the subprocess working directory. The git
    subcommands use `-C <path>` to target the right repo. This avoids
    'cannot change to' errors when the absolute path of cwd is some other
    location and the relative `-C` argument doesn't resolve.
    """
    try:
        p = subprocess.run(
            cmd, cwd=str(REPOS_DIR),
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def git_cmd(repo_path: Path, *args, timeout: int = 30) -> tuple[int, str, str]:
    """Run a git subcommand in repo_path with explicit -C. The shim `git -C <path>` works
    regardless of cwd."""
    full_cmd = ["git", "-C", str(repo_path), *args]
    return run(full_cmd, repo_path, timeout=timeout)


# ---- Branch discovery ------------------------------------------------------


def list_remote_branches(repo_path: Path) -> list[tuple[str, str]]:
    """Return [(remote, branch_name), ...] for all remote branches.

    Note: `git branch -r` indents lines with leading spaces AND emits ANSI
    color codes even with --no-color on some git versions. We strip both.

    Branch names may contain '/' (e.g. legacy/stash-0-foo). We split on the
    first '/' only — the remote is the prefix portion.
    """
    rc, out, _ = run(
        ["git", "-C", str(repo_path), "branch", "-r", "--no-color"],
        repo_path, timeout=15,
    )
    found = []
    if rc == 0:
        cleaned_all = strip_ansi(out)
        for line in cleaned_all.splitlines():
            line = line.strip()
            if line.startswith("remotes/"):
                line = line[len("remotes/"):]
            if not line:
                continue
            # Split on FIRST '/' only
            slash = line.find("/")
            if slash == -1:
                continue
            remote = line[:slash]
            branch = line[slash + 1:]
            if branch in ("HEAD",):
                continue
            found.append((remote, branch))
    return found


def find_recovery_branches(repo_path: Path) -> tuple[list[tuple[str, str, str, str]], Optional[str]]:
    """
    Find per-stash capture branches in the legacy/* namespace.

    Returns:
      (per_stash_branches, snapshot_branch_or_None)
        per_stash_branches: list of (stash_index_from_name, branch_name, sha, commit_msg)
        snapshot_branch: the legacy snapshot branch name (if any)
    """
    remotes = list_remote_branches(repo_path)

    per_stash = {}  # idx -> (branch, sha, msg)
    snapshot = None

    capture_re = re.compile(rf"^legacy/stash-(\d+)-([\w\-./]+)-{DATE_TAG}$")
    snapshot_re = re.compile(rf"^legacy/[\w\-.]*-stashes-snapshot-{DATE_TAG}$")

    for remote, branch in remotes:
        m = capture_re.match(branch)
        if m:
            idx = int(m.group(1))
            rc, sha_out, _ = run(
                ["git", "-C", str(repo_path), "rev-parse", f"{remote}/{branch}"],
                repo_path, timeout=10,
            )
            sha = sha_out.strip() if rc == 0 else ""
            rc2, msg_out, _ = run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%s", f"{remote}/{branch}"],
                repo_path, timeout=10,
            )
            msg = msg_out.strip() if rc2 == 0 else ""
            # First-remote-wins (prefer origin over koosha-https)
            if idx not in per_stash:
                per_stash[idx] = (branch, sha, msg)
            continue
        if snapshot_re.match(branch) and snapshot is None:
            snapshot = branch

    # Convert to sorted list
    per_stash_list = [
        (idx, branch, sha, msg)
        for idx, (branch, sha, msg) in sorted(per_stash.items())
    ]
    return per_stash_list, snapshot


def extract_stash_index_from_snapshot(repo_path: Path, snapshot_branch: str) -> list[tuple[int, str, str]]:
    """
    From a snapshot branch with multiple stash: capture commits, extract
    (idx, sha, msg) tuples by walking commit history.
    """
    rc, out, _ = run(
        ["git", "-C", str(repo_path), "log", "--reverse", "--no-color",
         "--format=%H%n%s%n---END---",
         f"origin/{snapshot_branch}"] if is_origin_present(repo_path) else
        ["git", "-C", str(repo_path), "log", "--reverse", "--no-color",
         "--format=%H%n%s%n---END---",
         snapshot_branch],
        repo_path, timeout=20,
    )
    if rc != 0 or not out:
        return []

    # Parse out commits whose subject starts with "stash: capture"
    entries = []
    capture_re = re.compile(r"^stash:\s*capture\s*(?:stash\s*)?(\d+)", re.IGNORECASE)
    commits = out.split("---END---")
    for block in commits:
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        sha = lines[0].strip()
        msg = lines[1].strip()
        m = capture_re.match(msg)
        if m:
            entries.append((int(m.group(1)), sha, msg))
    return entries


def is_origin_present(repo_path: Path) -> bool:
    rc, out, _ = run(
        ["git", "-C", str(repo_path), "remote"],
        repo_path, timeout=10,
    )
    if rc != 0:
        return False
    return "origin" in {line.strip() for line in out.splitlines()}


def get_existing_wip_remote(repo_path: Path, target_remotes: list[str]) -> dict[str, str]:
    """Return {branch_name: remote_name} for any wip/<date>-stash-* on any tracked remote."""
    remotes = list_remote_branches(repo_path)
    found = {}
    for remote, branch in remotes:
        if branch.startswith(f"wip/{DATE_TAG}-stash-"):
            if branch not in found:
                found[branch] = remote
    return found


def remote_sha(repo_path: Path, ref: str) -> str:
    rc, out, _ = run(
        ["git", "-C", str(repo_path), "rev-parse", ref],
        repo_path, timeout=10,
    )
    return out.strip() if rc == 0 else ""


# ---- Push with fallback ---------------------------------------------------
def ensure_koosha_https_remote(repo_path: Path, repo_name: str) -> Optional[str]:
    """Add a koosha-https remote if not present. Returns its name or None.

    Honors `KOOSHA_PUSH_TARGET_OVERRIDES` to map local repo names to canonical
    github repos (e.g. worktrees/mirrors where the dirname != the github repo).
    """
    rc, out, _ = run(
        ["git", "-C", str(repo_path), "remote"],
        repo_path, timeout=10,
    )
    if rc != 0:
        return None
    existing = {line.strip() for line in out.splitlines()}
    if "koosha-https" in existing:
        return "koosha-https"

    gh_token = os.environ.get("GH_TOKEN", "")
    if not gh_token:
        try:
            r2 = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, timeout=10,
            )
            gh_token = r2.stdout.strip() if r2.returncode == 0 else ""
        except Exception:
            pass
    if not gh_token:
        return None

    target_repo = KOOSHA_PUSH_TARGET_OVERRIDES.get(repo_name, f"KooshaPari/{repo_name}")
    auth_url = f"https://x-access-token:{gh_token}@github.com/{target_repo}.git"
    rc2, _, err = run(
        ["git", "-C", str(repo_path), "remote", "add", "koosha-https", auth_url],
        repo_path, timeout=10,
    )
    if rc2 != 0:
        return None
    return "koosha-https"


def push_branch(repo_path: Path, branch: str, repo_name: str, primary_remote: str = "origin") -> tuple:
    """Push branch. Try origin then koosha-https. Returns (rc, used_remote, log)."""
    log_lines = []

    # Try origin
    if primary_remote:
        rc, out, err = run(
            ["git", "-C", str(repo_path), "remote"],
            repo_path, timeout=10,
        )
        if rc == 0 and primary_remote in {line.strip() for line in out.splitlines()}:
            log_lines.append(f"[origin] trying {primary_remote}")
            rc, out, err = run(
                ["git", "-C", str(repo_path), "push", "--no-verify", "-u", primary_remote, branch],
                repo_path, timeout=75,
            )
            log_lines.append(f"[origin] rc={rc}")
            if rc == 0:
                return (0, primary_remote, "\n".join(log_lines))
            log_lines.append(f"[origin] stderr: {err.strip()[:300]}")

    # Try koosha-https
    kremote = ensure_koosha_https_remote(repo_path, repo_name)
    if kremote:
        rc2, out2, err2 = run(
            ["git", "-C", str(repo_path), "push", "--no-verify", "-u", kremote, branch],
            repo_path, timeout=90,
        )
        log_lines.append(f"[{kremote}] rc={rc2}")
        if rc2 == 0:
            return (0, kremote, "\n".join(log_lines))
        log_lines.append(f"[{kremote}] stderr: {err2.strip()[:300]}")

    return (1, "", "\n".join(log_lines))
# ---- Per-repo processing --------------------------------------------------


def process_repo(
    repo_name: str,
    expected_stashes: int,
    skipped_mirror: bool,
    skip_reason: Optional[str] = None,
) -> dict:
    """Process one repo. Returns per_repo entry dict."""
    per_repo: dict = {
        "stashes_found": expected_stashes,
        "recovered": 0,
        "parked": 0,
        "skipped_mirror": 0,
        "already_remote": 0,
        "preserved_count": expected_stashes,
        "branches_pushed": [],
        "branches_already_remote": [],
        "branches_skipped": [],
    }
    if skip_reason:
        per_repo["skip_reason"] = skip_reason
    return per_repo


# ---- Research file parsing -----------------------------------------------


def parse_research_file() -> dict[str, int]:
    """Parse .research-dirty-work-2026-07-15.md Section 3 for per-repo stash counts.

    Section 3 table has rows like:
        | Repo | Stashes | Risk note |
        | OmniRoute | 9 | mirror of below |
    """
    path = REPOS_DIR / ".research-dirty-work-2026-07-15.md"
    if not path.exists():
        print(f"WARNING: research file not found at {path}", file=sys.stderr)
        return {}

    text = path.read_text()
    # Locate Section 3 (## 3. ...) and stop at next ## section
    sec_re = re.compile(r"^##\s*3\b[^\n]*\n", re.MULTILINE)
    next_sec_re = re.compile(r"^##\s*4\b", re.MULTILINE)
    sec_match = sec_re.search(text)
    if not sec_match:
        print("WARNING: Section 3 not found in research file", file=sys.stderr)
        return {}
    sec3_start = sec_match.end()
    # Stop at next ## section header
    end_match = next_sec_re.search(text, pos=sec3_start)
    sec3_end = end_match.start() if end_match else len(text)
    sec3 = text[sec3_start:sec3_end]

    counts: dict[str, int] = {}
    # Markdown table row: `| <repo> | <N> | <note> |`
    row_re = re.compile(
        r"^\|\s*([A-Za-z0-9_.\-]+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for m in row_re.finditer(sec3):
        repo = m.group(1).strip()
        n = int(m.group(2))
        # Skip header rows / separator rows / TOTAL row
        if repo.lower() in ("repo", "total"):
            continue
        counts[repo] = counts.get(repo, 0) + n

    return counts


# ---- Main -----------------------------------------------------------------


def main():
    PARKINGS_DIR.mkdir(parents=True, exist_ok=True)
    counts = parse_research_file()

    # The 17-repo scope (ordered alphabetically for stable output)
    repos = [
        "AgilePlus",
        "BytePort",
        "Grapheon",
        "HexaKit",
        "melosviz",
        "OmniRoute",
        "OmniRoute-frontend-svelte-2026-07-05",
        "OmniRoute-superroot-recovery",
        "omniroute-upstream-work",
        "phenotype-apps-L39-wt",
        "phenotype-registry",
        "PhenoObservability",
        "pheno-tracing",
        "pheno-tracing-t24",
        "forgecode",
        "sharecli",
        "cliproxyapi-plusplus",
    ]

    audit: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "stash-recovery",
        "policy": "aggressive-on-create-push-branch, conservative-on-stash-drop (no drops performed in this pass — all stashes already gone via prior recovery)",
        "stashes_total": sum(counts.values()),
        "stashes_recovered": 0,
        "stashes_already_remote": 0,
        "stashes_parked": 0,
        "stashes_dropped": 0,
        "stashes_preserved": 0,
        "stashes_skipped_mirror": 0,
        "per_repo": {},
        "per_stash_log": [],
    }

    # Build mirror skip set
    skipped_repo_set = set()
    mirror_notes = {}
    for cluster_name, cluster in MIRROR_CLUSTERS.items():
        for skipped in cluster["skipped"]:
            skipped_repo_set.add(skipped)
            mirror_notes[skipped] = cluster["note"]

    # If research file has 0 repos parsed, try a wider net
    if not counts:
        print("FALLBACK: research file empty; using direct stash-list probe on 17 repos...",
              file=sys.stderr)
        for repo in repos:
            repo_path = REPOS_DIR / repo
            if not (repo_path / ".git").exists():
                continue
            rc, out, _ = run(
                ["git", "-C", str(repo_path), "stash", "list"],
                repo_path, timeout=10,
            )
            if rc == 0:
                n = len([l for l in out.splitlines() if l.strip()])
                counts[repo] = n

    # Print baseline for reference
    print(f"[baseline] expected stashes per repo (from research file):")
    total = 0
    for repo in sorted(counts.keys()):
        print(f"  {repo:50s} {counts[repo]:3d}")
        total += counts[repo]
    print(f"  {'TOTAL':50s} {total:3d}")
    print()

    global_seq = 0

    for repo in repos:
        repo_path = REPOS_DIR / repo
        if not (repo_path / ".git").exists():
            print(f"[skip] {repo}: no .git directory")
            continue

        expected = counts.get(repo, 0)

        # Mirror-skip handling
        if repo in skipped_repo_set:
            per_repo = process_repo(repo, expected, skipped_mirror=True,
                                    skip_reason=mirror_notes.get(repo))
            audit["per_repo"][repo] = per_repo
            audit["stashes_skipped_mirror"] += expected
            for _ in range(expected):
                global_seq += 1
                audit["per_stash_log"].append({
                    "repo": repo,
                    "stash_index": None,
                    "global_seq": global_seq,
                    "stash_message": None,
                    "branch": None,
                    "sha": None,
                    "push_rc": None,
                    "drop_rc": None,
                    "status": "skipped_mirror",
                    "reason": mirror_notes.get(repo),
                })
            print(f"[skip-mirror] {repo} expected={expected}")
            continue
        # Discover prior-recovered branches
        per_stash_branches, snapshot_branch = find_recovery_branches(repo_path)
        # If there's a snapshot but no per-stash branches, try to extract
        if not per_stash_branches and snapshot_branch:
            extracted = extract_stash_index_from_snapshot(repo_path, snapshot_branch)
            per_stash_branches = [(idx, snapshot_branch, sha, msg) for idx, sha, msg in extracted]

        # If still no per-stash branches, check the current stash list directly
        rc, current_stash_out, _ = run(
            ["git", "-C", str(repo_path), "stash", "list"],
            repo_path, timeout=10,
        )
        current_stash_count = len([l for l in current_stash_out.splitlines() if l.strip()])

        if not per_stash_branches and current_stash_count == 0:
            per_repo = process_repo(repo, 0, skipped_mirror=False)
            per_repo["stashes_found"] = expected
            per_repo["preserved_count"] = 0
            per_repo["warning"] = "no stash@{N} found and no legacy/stash-* branches — already cleaned up?"
            audit["per_repo"][repo] = per_repo
            print(f"[empty] {repo} expected={expected} — empty state, recording warning")
            continue

        print(f"[process] {repo} expected={expected} legacy_branches={len(per_stash_branches)} current_stash={current_stash_count}")

        per_repo = process_repo(repo, expected, skipped_mirror=False)
        if current_stash_count > 0:
            per_repo["preserved_count"] = current_stash_count
            per_repo["warning"] = f"{current_stash_count} live stash(es) found in working repo — preserved"

        # Map existing wip/<date>-stash-* branches
        existing_wip = get_existing_wip_remote(repo_path, [])

        for stash_idx, legacy_branch, sha, msg in per_stash_branches:
            global_seq += 1

            # Slug extraction
            m = re.match(r"^legacy/stash-\d+-(.+)", legacy_branch)
            if m:
                slug_source = m.group(1).rsplit(f"-{DATE_TAG}", 1)[0]
            else:
                slug_source = f"capture-stash-{stash_idx}"

            slug = slugify(slug_source)
            wip_branch = f"wip/{DATE_TAG}-stash-{stash_idx:03d}-{slug}"

            # No-op fast path: check remote for matching branch
            if wip_branch in existing_wip:
                remote_name = existing_wip[wip_branch]
                remote_sha_val = remote_sha(repo_path, f"{remote_name}/{wip_branch}")
                if remote_sha_val == sha:
                    per_repo["already_remote"] += 1
                    per_repo["branches_already_remote"].append(wip_branch)
                    audit["stashes_already_remote"] += 1
                    audit["per_stash_log"].append({
                        "repo": repo,
                        "stash_index": stash_idx,
                        "global_seq": global_seq,
                        "stash_message": msg,
                        "branch": wip_branch,
                        "sha": sha,
                        "push_rc": 0,
                        "drop_rc": None,
                        "status": "already_on_remote",
                        "remote": remote_name,
                    })
                    continue

            # Recovery: create local wip/ alias and push
            rc_local, _, err = run(
                ["git", "-C", str(repo_path), "branch", wip_branch, sha],
                repo_path, timeout=10,
            )
            if rc_local != 0:
                # Branch may already exist locally; try force
                run(
                    ["git", "-C", str(repo_path), "branch", "-f", wip_branch, sha],
                    repo_path, timeout=10,
                )

            # Push
            push_rc, push_remote, push_log = push_branch(repo_path, wip_branch, repo_name)

            if push_rc == 0:
                per_repo["recovered"] += 1
                per_repo["branches_pushed"].append(wip_branch)
                audit["stashes_recovered"] += 1
                audit["per_stash_log"].append({
                    "repo": repo,
                    "stash_index": stash_idx,
                    "global_seq": global_seq,
                    "stash_message": msg,
                    "branch": wip_branch,
                    "sha": sha,
                    "push_rc": push_rc,
                    "drop_rc": None,
                    "status": "recovered",
                    "pushed_to": push_remote,
                })
            else:
                # Park locally
                patch_name = f"{repo}-stash-{stash_idx:03d}.patch"
                patch_path = PARKINGS_DIR / patch_name
                rc_diff, diff_out, _ = run(
                    ["git", "-C", str(repo_path), "show", sha],
                    repo_path, timeout=15,
                )
                patch_path.write_text(diff_out if rc_diff == 0 else push_log)
                per_repo["parked"] += 1
                audit["stashes_parked"] += 1
                audit["stashes_preserved"] += 1  # original stash preserved
                audit["per_stash_log"].append({
                    "repo": repo,
                    "stash_index": stash_idx,
                    "global_seq": global_seq,
                    "stash_message": msg,
                    "branch": wip_branch,
                    "sha": sha,
                    "push_rc": push_rc,
                    "drop_rc": None,
                    "status": "parked_push_failed",
                    "parking_file": str(patch_path),
                    "push_log": push_log,
                })

        # Record current live stashes as preserved
        if current_stash_count > 0:
            audit["stashes_preserved"] += current_stash_count

        audit["per_repo"][repo] = per_repo

    # Add mirror-skipped repos not in the explicit list (defensive)
    for repo, note in mirror_notes.items():
        if repo not in audit["per_repo"] and repo in repos:
            expected = counts.get(repo, 0)
            per_repo = process_repo(repo, expected, skipped_mirror=True, skip_reason=note)
            audit["per_repo"][repo] = per_repo
            audit["stashes_skipped_mirror"] += expected
            for _ in range(expected):
                global_seq += 1
                audit["per_stash_log"].append({
                    "repo": repo,
                    "stash_index": None,
                    "global_seq": global_seq,
                    "stash_message": None,
                    "branch": None,
                    "sha": None,
                    "push_rc": None,
                    "drop_rc": None,
                    "status": "skipped_mirror",
                    "reason": note,
                })

    # Final reconciliation checks
    audit["match"] = (
        audit["stashes_recovered"]
        + audit["stashes_already_remote"]
        + audit["stashes_parked"]
        + audit["stashes_skipped_mirror"]
    ) == audit["stashes_total"]
    audit["summary_totals_check"] = (
        audit["stashes_recovered"]
        + audit["stashes_already_remote"]
        + audit["stashes_parked"]
        + audit["stashes_skipped_mirror"]
    )

    # Write audit
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True))
    print(f"\n[audit] written to {AUDIT_PATH}")
    print(f"[totals] recovered={audit['stashes_recovered']} "
          f"already={audit['stashes_already_remote']} "
          f"parked={audit['stashes_parked']} "
          f"skip_mirror={audit['stashes_skipped_mirror']} "
          f"total_check={audit['summary_totals_check']}/68 "
          f"match={audit['match']}")


if __name__ == "__main__":
    main()
