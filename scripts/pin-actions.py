#!/usr/bin/env python3
"""Pin all third-party GitHub Actions references to full commit SHAs.

Two modes:
  - Default: replace FLOATING refs (e.g., @v4) with current SHA.
  - With --re-verify: also try to verify EXISTING SHA-pinned refs by
    HEAD-requesting them at the upstream repo. If the SHA is gone,
    replace with the current SHA for the same version comment.

Local refs (`./...`, `../...`) and docker refs are left untouched per
the secret-guard policy (scripts/workflow-action-guard.py).

Does NOT push. Run `python scripts/workflow-action-guard.py` after.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

WORKFLOW_DIR = Path(".github/workflows")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
USES_RE = re.compile(
    r"""^\s*-\s*uses:\s+(?P<value>['"]?)(?P<ref>[^'"\s#]+)(?P=value)\s*(?:#\s*(?P<comment>.*))?$"""
)
PLAIN_USES_RE = re.compile(
    r"""^\s*uses:\s+(?P<value>['"]?)(?P<ref>[^'"\s#]+)(?P=value)\s*(?:#\s*(?P<comment>.*))?$"""
)


def is_local(ref: str) -> bool:
    return ref.startswith(("./", "../", "docker://"))


def is_sha_pinned(ref: str) -> bool:
    if "@" not in ref:
        return False
    _, tag = ref.rsplit("@", 1)
    return bool(SHA_RE.match(tag))


def extract_action_refs() -> dict[str, str]:
    """Map action name -> current SHA (for re-verify mode)."""
    out = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", "query=query{viewer{login}}}",
        ],
        capture_output=True, text=True,
    )
    return {}


def lookup_sha(repo: str, ref: str) -> Optional[str]:
    """Return the commit SHA for `repo@ref`, peeling tag objects.

    Tries `ref` and `v{...}` for tag-style refs (most actions use v-prefix).
    For sub-action paths (`owner/repo/subdir`), tags/heads live in the
    top-level repo.
    """
    repo_for_lookup = top_level_repo(repo)
    candidates = [ref]
    if not ref.startswith("v") and re.match(r"^\d", ref):
        candidates.append(f"v{ref}")
    for cand in candidates:
        for kind in ("tags", "heads"):
            proc = subprocess.run(
                [
                    "gh", "api", f"repos/{repo_for_lookup}/git/ref/{kind}/{cand}",
                    "--jq", ".object.sha",
                ],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                continue
            out = proc.stdout.strip()
            if not out or "Not Found" in out or "no commit" in out.lower():
                continue
            sha = out.split()[0]
            if not SHA_RE.match(sha):
                continue
            peel = subprocess.run(
                [
                    "gh", "api", f"repos/{repo_for_lookup}/git/tags/{sha}",
                    "--jq", ".object.type + \":\" + .object.sha",
                ],
                capture_output=True, text=True,
            )
            if peel.returncode == 0 and peel.stdout.strip().startswith("commit:"):
                return peel.stdout.strip().split(":", 1)[1]
            return sha
    return None


def get_latest_release_sha(repo: str) -> Optional[str]:
    proc = subprocess.run(
        [
            "gh", "api", f"repos/{top_level_repo(repo)}/releases/latest",
            "--jq", ".target_commitish",
        ],
        capture_output=True, text=True,
    )
    if proc.returncode == 0 and SHA_RE.match(proc.stdout.strip()):
        return proc.stdout.strip()
    return None


def resolve_ref(repo: str, ref: str) -> Optional[str]:
    sha = lookup_sha(repo, ref)
    if sha:
        return sha
    return get_latest_release_sha(repo)


def top_level_repo(repo: str) -> str:
    """For sub-action paths like `github/codeql-action/upload-sarif`,
    return the top-level `github/codeql-action`. Otherwise return as-is.
    """
    parts = repo.split("/")
    if len(parts) > 2:
        return "/".join(parts[:2])
    return repo


def verify_sha(repo: str, sha: str) -> bool:
    """Return True if `sha` is reachable in `repo`.

    `gh api` returns exit 0 even on HTTP errors, so we must inspect
    the response body. A successful response includes the SHA back as
    the `.sha` field; an error response includes a `message` field.

    For sub-action paths (`owner/repo/subdir`), the SHA lives in the
    top-level repo. We always verify against the top-level repo.
    """
    proc = subprocess.run(
        [
            "gh", "api", f"repos/{top_level_repo(repo)}/commits/{sha}",
            "--jq", ".sha // empty",
        ],
        capture_output=True, text=True,
    )
    out = proc.stdout.strip()
    return out == sha


def process_file(path: Path, re_verify: bool) -> tuple[int, list[tuple[str, str, Optional[str]]]]:
    text = path.read_text(encoding="utf-8")
    new_lines: list[str] = []
    changes: list[tuple[str, str, Optional[str]]] = []
    count = 0
    for line in text.splitlines():
        m = USES_RE.match(line) or PLAIN_USES_RE.match(line)
        if not m:
            new_lines.append(line)
            continue
        ref = m.group("ref")
        comment = m.group("comment") or ""
        if is_local(ref):
            new_lines.append(line)
            continue
        if "@" not in ref:
            new_lines.append(line)
            continue
        repo, version = ref.rsplit("@", 1)
        if "/" not in repo:
            new_lines.append(line)
            continue
        if is_sha_pinned(ref):
            if not re_verify:
                new_lines.append(line)
                continue
            # Verify the pinned SHA is reachable
            if verify_sha(repo, version):
                new_lines.append(line)
                continue
            # Pinned SHA is unreachable — re-resolve using comment as version hint
            # Extract version from comment, e.g. "# v1.0.4" or "# v4.2.2"
            version_hint = ""
            cm = re.search(r"v?\d+(?:\.\d+)*(?:[._-]\w+)*", comment)
            if cm:
                version_hint = cm.group(0).lstrip("v")
            target = version_hint or "latest"
            sha = lookup_sha(repo, target) or get_latest_release_sha(repo)
            if not sha:
                changes.append((ref, "", "broken SHA + cannot resolve"))
                new_lines.append(line)
                continue
            new_line = rebuild_line(line, m, repo, sha, comment)
            changes.append((ref, f"{repo}@{sha}", "broken-SHA replaced"))
            new_lines.append(new_line)
            count += 1
            continue
        # Floating ref — pin it
        sha = resolve_ref(repo, version) or get_latest_release_sha(repo)
        if not sha:
            changes.append((ref, "", "could not resolve"))
            new_lines.append(line)
            continue
        new_line = rebuild_line(line, m, repo, sha, comment)
        changes.append((ref, f"{repo}@{sha}", None))
        new_lines.append(new_line)
        count += 1
    if count:
        path.write_text(
            "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""),
            encoding="utf-8",
        )
    return count, changes


def rebuild_line(line: str, m: re.Match, repo: str, sha: str, comment: str) -> str:
    leading_ws = line[: len(line) - len(line.lstrip())]
    prefix = "- " if line.lstrip().startswith("- ") else ""
    if comment:
        return f"{leading_ws}{prefix}uses: {repo}@{sha}  # {comment}"
    return f"{leading_ws}{prefix}uses: {repo}@{sha}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--re-verify", action="store_true",
                   help="Also verify existing SHA-pinned refs are reachable.")
    p.add_argument("--files", nargs="*", type=Path, default=None,
                   help="Restrict to specific files (default: all workflows).")
    args = p.parse_args()

    if not WORKFLOW_DIR.is_dir():
        print(f"error: {WORKFLOW_DIR} not found (run from repo root)", file=sys.stderr)
        return 1

    if args.files:
        files = [f if f.is_absolute() else Path.cwd() / f for f in args.files]
    else:
        files = sorted(
            list(WORKFLOW_DIR.rglob("*.yml")) + list(WORKFLOW_DIR.rglob("*.yaml"))
        )

    total = 0
    all_changes: list[tuple[Path, str, str, Optional[str]]] = []
    for path in files:
        if not path.exists():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        n, changes = process_file(path, args.re_verify)
        total += n
        for old, new, err in changes:
            all_changes.append((path, old, new, err))

    print(f"changed {total} refs")
    if all_changes:
        print()
        try:
            cwd = Path.cwd()
        except Exception:
            cwd = None
        for path, old, new, err in changes:
            tag = f" [{err}]" if err else ""
            try:
                rel = path.relative_to(cwd) if cwd else path
            except ValueError:
                rel = path
            print(f"  {rel}: {old} -> {new}{tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
