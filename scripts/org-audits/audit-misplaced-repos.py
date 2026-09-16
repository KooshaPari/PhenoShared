#!/usr/bin/env python3
"""
Read-only audit script (parallelized, no fsck) for misplaced repos in ~.

For each candidate repo it gathers:
  - HEAD SHA + branch
  - origin/HEAD SHA + branch (if reachable)
  - ahead/behind counts vs origin/HEAD (if applicable)
  - dirty working-tree file count
  - stash count + first stash summary
  - local-only branches (branches without upstream)
  - remote URL(s)
  - on-disk size (du -sh, with a hard timeout)

Writes a single JSON to the path passed as argv[1].
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HOME = Path("/Users/kooshapari")
CODEPROJECTS = Path("/Users/kooshapari/CodeProjects")

# (label, absolute path, category)
CANDIDATES: list[tuple[str, str, str]] = [
    # Category A — live git repos in ~/
    ("CLIProxyAPI", str(HOME / "CLIProxyAPI"), "A-live-~"),
    ("router-rb-2c", str(HOME / "router-rb-2c"), "A-live-~"),
    ("forge/AgilePlus", str(HOME / "forge" / "AgilePlus"), "A-live-~"),
    ("work/forgecode-koosha", str(HOME / "work" / "forgecode-koosha"), "A-live-~"),
    ("work/forgecode-upstream", str(HOME / "work" / "forgecode-upstream"), "A-live-~"),
    # Category B — ~/Repos/* orphans
    ("Repos/civ", str(HOME / "Repos" / "civ"), "B-repos-orphan"),
    ("Repos/heliosCLI", str(HOME / "Repos" / "heliosCLI"), "B-repos-orphan"),
    ("Repos/phench", str(HOME / "Repos" / "phench"), "B-repos-orphan"),
    ("Repos/phenodocs", str(HOME / "Repos" / "phenodocs"), "B-repos-orphan"),
    ("Repos/phenotype-design", str(HOME / "Repos" / "phenotype-design"), "B-repos-orphan"),
    ("Repos/phenotype-go-kit", str(HOME / "Repos" / "phenotype-go-kit"), "B-repos-orphan"),
    ("Repos/phenotype-infrakit", str(HOME / "Repos" / "phenotype-infrakit"), "B-repos-orphan"),
    ("Repos/phenotype-shared", str(HOME / "Repos" / "phenotype-shared"), "B-repos-orphan"),
    ("Repos/phenotypeActions", str(HOME / "Repos" / "phenotypeActions"), "B-repos-orphan"),
    ("Repos/template-commons", str(HOME / "Repos" / "template-commons"), "B-repos-orphan"),
    ("Repos/znap", str(HOME / "Repos" / "znap"), "B-repos-orphan"),
    # Category E — Documents repo checkouts
    ("Documents/netweave-3", str(HOME / "Documents" / "netweave-3"), "E-documents-repo"),
    ("Documents/Project-Spyn", str(HOME / "Documents" / "Project-Spyn"), "E-documents-repo"),
]

DUPLICATE_HINTS: dict[str, list[str]] = {
    "CLIProxyAPI": ["CodeProjects/cliproxyapi-plusplus"],
    "Repos/civ": ["CodeProjects/Phenotype/repos/Civis"],
    "Repos/phench": ["CodeProjects/Phenotype/repos/phench"],
    "forge/AgilePlus": ["CodeProjects/Phenotype/repos/AgilePlus"],
}


def run(cmd: list[str], cwd: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    except Exception as exc:
        return 1, "", f"ERR: {exc}"


def is_git_repo(path: str) -> tuple[bool, str]:
    p = Path(path)
    if (p / ".git").is_dir():
        return True, "full-repo"
    if (p / ".git").is_file():
        try:
            content = (p / ".git").read_text().strip()
            return True, f"worktree-pointer({content[:120]})"
        except Exception:
            return True, "worktree-pointer(unreadable)"
    return False, "not-a-git-dir"


def git_value(path: str, *args: str, timeout: int = 15) -> str:
    rc, out, _ = run(["git", *args], cwd=path, timeout=timeout)
    return out if rc == 0 else ""


def size_human(path: str, timeout: int = 60) -> str:
    rc, out, _ = run(["du", "-sh", path], timeout=timeout)
    if rc == 0:
        return out.split()[0]
    return "size-timeout"


def count_lines(s: str) -> int:
    return 0 if not s else len(s.splitlines())


def first_n_lines(s: str, n: int = 5) -> str:
    if not s:
        return ""
    return "\n".join(s.splitlines()[:n])


def collect_unpushed_branches(path: str) -> tuple[int, list[str]]:
    rc, out, _ = run(
        ["git", "for-each-ref", "--format=%(refname:short) %(upstream:short)",
         "refs/heads/"],
        cwd=path, timeout=15,
    )
    if rc != 0:
        return 0, []
    unpushed: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) == 1:
            unpushed.append(f"{parts[0]} (NO-UPSTREAM)")
        else:
            rc2, ahead_out, _ = run(
                ["git", "rev-list", "--count", f"{parts[1]}..{parts[0]}"],
                cwd=path, timeout=10,
            )
            try:
                ahead = int(ahead_out) if ahead_out else 0
            except ValueError:
                ahead = -1
            if ahead > 0:
                unpushed.append(f"{parts[0]} (ahead {ahead} of {parts[1]})")
    return len(unpushed), unpushed[:5]


def audit_one(label: str, path: str, category: str) -> dict:
    info: dict = {
        "label": label,
        "path": path,
        "category": category,
        "exists": Path(path).exists(),
    }
    if not info["exists"]:
        return info
    info["size"] = size_human(path, timeout=60)

    is_repo, repo_type = is_git_repo(path)
    info["repo_type"] = repo_type
    if not is_repo:
        return info

    info["head_sha"] = git_value(path, "rev-parse", "HEAD")
    info["head_branch"] = git_value(path, "rev-parse", "--abbrev-ref", "HEAD")
    info["detached"] = info["head_branch"] == "HEAD"

    rc, origin_head, _ = run(
        ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
        cwd=path, timeout=10,
    )
    if rc == 0 and origin_head:
        info["origin_head_ref"] = origin_head
        info["origin_head_sha"] = git_value(path, "rev-parse", origin_head)
    else:
        info["origin_head_ref"] = None
        for guess in ("origin/main", "origin/master"):
            sha = git_value(path, "rev-parse", "--verify", guess)
            if sha:
                info["origin_head_ref"] = guess
                info["origin_head_sha"] = sha
                break
        else:
            info["origin_head_sha"] = None

    if info.get("origin_head_ref") and not info["detached"]:
        rc2, ab, _ = run(
            ["git", "rev-list", "--left-right", "--count",
             f"{info['origin_head_ref']}...HEAD"],
            cwd=path, timeout=30,
        )
        info["ahead_behind_origin"] = ab
    else:
        info["ahead_behind_origin"] = None

    rc3, dirty, _ = run(["git", "status", "--porcelain"], cwd=path, timeout=60)
    info["dirty_files_count"] = count_lines(dirty)
    info["dirty_sample"] = first_n_lines(dirty, 8)

    rc4, stashes, _ = run(["git", "stash", "list"], cwd=path, timeout=15)
    info["stash_count"] = count_lines(stashes)
    info["stash_sample"] = first_n_lines(stashes, 3)

    info["unpushed_branches_count"], info["unpushed_branches_sample"] = (
        collect_unpushed_branches(path)
    )

    rc5, remotes, _ = run(["git", "remote", "-v"], cwd=path, timeout=15)
    info["remotes_raw"] = remotes

    info["duplicate_hints"] = DUPLICATE_HINTS.get(label, [])
    info["duplicate_paths_exist"] = [
        p for p in info["duplicate_hints"]
        if Path(f"/Users/kooshapari/{p}").exists()
    ]

    return info


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        CODEPROJECTS / "Phenotype" / "repos" / "_phenofleet-decisions"
        / "migration-2026-07-14.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(audit_one, label, path, cat): label
            for label, path, cat in CANDIDATES
        }
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                result = fut.result(timeout=180)
                print(f"[done] {label} -> {result.get('repo_type','?')} "
                      f"dirty={result.get('dirty_files_count','?')} "
                      f"size={result.get('size','?')}",
                      flush=True)
            except Exception as exc:
                print(f"[err ] {label}: {exc}", flush=True)
                result = {"label": label, "error": str(exc)}
            results.append(result)

    label_to_result = {r["label"]: r for r in results}
    ordered = [label_to_result.get(label, {"label": label, "missing": True})
               for label, _, _ in CANDIDATES]

    payload = {
        "audit_date": "2026-07-14",
        "audit_type": "read-only-misplaced-repo-survey",
        "home": str(HOME),
        "codeprojects_root": str(CODEPROJECTS),
        "candidates_total": len(ordered),
        "repos_total": sum(
            1 for r in ordered
            if (r.get("repo_type") or "").startswith(("full-repo", "worktree-pointer"))
        ),
        "results": ordered,
    }

    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False))
    print(f"\n[ok] wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
