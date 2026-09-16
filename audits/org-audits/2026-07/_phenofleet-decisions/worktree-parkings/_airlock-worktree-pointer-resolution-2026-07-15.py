#!/usr/bin/env python3
"""
airlock-worktree-pointer-resolution-2026-07-15.py

Process every orphan/broken worktree pointer detected by the
2026-07-15 gitification audit, plus the outer ~/CodeProjects/**
artifacts, plus the airlock's superpowers/thegent worktrees.

Policy: aggressive-repair-snapshot-then-delete.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/kooshapari/CodeProjects/Phenotype/repos")
PARK = REPO_ROOT / "_phenofleet-decisions" / "worktree-parkings"
DATE = "2026-07-15"
AUDIT_JSON = REPO_ROOT / ".airlock-worktree-pointer-2026-07-15.json"

# ---------- CANDIDATES ----------

# 14 orphans from .research-repos-gitification-2026-07-15.md Section 4.3
# All are now physically absent (parent dirs pruned post-audit).
AUDIT_ORPHANS = [
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/l101-motion/.git",
        "expected_target": "Tracera/.git/worktrees/l101-motion",
        "note": "Target repo wrong (Grapheon has no worktree manager)",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/l104-readme-tracera/.git",
        "expected_target": "Tracera/.git/worktrees/l104-readme-tracera",
        "note": "Same",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/l105-docs-assets/.git",
        "expected_target": "Tracera/.git/worktrees/l105-docs-assets",
        "note": "Same",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/tracera-splash/.git",
        "expected_target": "Tracera/.git/worktrees/tracera-splash",
        "note": "Same",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/tracera-tokens/.git",
        "expected_target": "Tracera/.git/worktrees/tracera-tokens",
        "note": "Same",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "Grapheon/.claude/worktrees/v38-scorecards/.git",
        "expected_target": "Tracera/.git/worktrees/v38-scorecards",
        "note": "Same",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "OmniRoute/.claude/worktrees/docs-substrate-http-url/.git",
        "expected_target": "OmniRoute/.git/worktrees/docs-substrate-http-url",
        "note": "Target removed",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "OmniRoute/.claude/worktrees/feat-sveltekit-v2/.git",
        "expected_target": "OmniRoute/.git/worktrees/feat-sveltekit-v2",
        "note": "Target removed",
    },
    {
        "kind": "wt_shadow_clone",
        "path": "OmniRoute/.worktrees/rtk-pr6774/.git",
        "expected_target": "omniroute-upstream-work/.git/worktrees/rtk-pr6774",
        "note": "Shadow clone; physical dir had 800+ files; only git pointer was broken",
    },
    {
        "kind": "wt_shadow_clone",
        "path": "OmniRoute/.worktrees/rtk-pr6774/.build/next/standalone/.git",
        "expected_target": "(nested build artifact - inside the above)",
        "note": "Build artifact .git pointer inside rtk-pr6774",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "phenotype-org-audits-wtrees/home-recovery-2026-07/.git",
        "expected_target": "~/CodeProjects/poa-fresh/.git/worktrees/home-recovery-2026-07",
        "note": "poa-fresh does not exist",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "phenotype-org-audits-wtrees/home-recovery-2026-07-v2/.git",
        "expected_target": "phenotype-org-audits/.git/worktrees/home-recovery-2026-07-v2",
        "note": "phenotype-org-audits not in repos/",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "sharecli/.claude/worktrees/sharecli-l141-util/.git",
        "expected_target": "sharecli/.git/worktrees/sharecli-l141-util",
        "note": "Target removed",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "worktrees/PhenoCompose-audit-followups/.git",
        "expected_target": "PhenoCompose/.git/worktrees/PhenoCompose-audit-followups",
        "note": "PhenoCompose lives outside repos/",
    },
]

# 8 additional orphans in outer ~/CodeProjects/Phenotype/ (not in original 14)
OUTER_ORPHANS = [
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08/thegent-clean-wt-docs/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/thegent-clean/.git/worktrees/thegent-clean-wt-docs",
        "note": "thegent-clean repo is absent from repos/; archived worktree on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08",
        "snapshot_dirname": "thegent-clean-wt-docs",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08/thegent-clean-wt-ruff/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/thegent-clean/.git/worktrees/thegent-clean-wt-ruff",
        "note": "Same; archived worktree on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08",
        "snapshot_dirname": "thegent-clean-wt-ruff",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08/thegent-clean-wt-policy/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/thegent-clean/.git/worktrees/thegent-clean-wt-policy",
        "note": "Same; archived worktree on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08",
        "snapshot_dirname": "thegent-clean-wt-policy",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08/thegent-clean-wt-parallel/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/thegent-clean/.git/worktrees/thegent-clean-wt-parallel",
        "note": "Same; archived worktree on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08",
        "snapshot_dirname": "thegent-clean-wt-parallel",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08/thegent-clean-wt-idea/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/thegent-clean/.git/worktrees/thegent-clean-wt-idea",
        "note": "Same; archived worktree on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/_archive/2026-06-08",
        "snapshot_dirname": "thegent-clean-wt-idea",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661/persistent/.git",
        "expected_target": "/Users/kooshapari/.airlock/repos/8711057fb661.git/worktrees/persistent",
        "note": "Airlock bare mirror gone (post-prune); worktree dir still on disk",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661",
        "source_dirname": "persistent",
        "snapshot_dirname": "heliosApp-persistent-8711057fb661",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661/5ffb5ebd-13d7-4e47-9aad-1e4d8f0daa9e/.git",
        "expected_target": "/Users/kooshapari/.airlock/repos/8711057fb661.git/worktrees/5ffb5ebd-13d7-4e47-9aad-1e4d8f0daa9e",
        "note": "Same",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661",
        "source_dirname": "5ffb5ebd-13d7-4e47-9aad-1e4d8f0daa9e",
        "snapshot_dirname": "heliosApp-5ffb5ebd-8711057fb661",
    },
    {
        "kind": "worktree_pointer_orphan",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661/2a97c405-f982-4e17-972a-07c34f5c385c/.git",
        "expected_target": "/Users/kooshapari/.airlock/repos/8711057fb661.git/worktrees/2a97c405-f982-4e17-972a-07c34f5c385c",
        "note": "Same",
        "parent_dir": "/Users/kooshapari/CodeProjects/Phenotype/recovery/home-audit-20260715/heliosApp/tree-archive-copy/8711057fb661",
        "source_dirname": "2a97c405-f982-4e17-972a-07c34f5c385c",
        "snapshot_dirname": "heliosApp-2a97c405-8711057fb661",
    },
]

# Superpowers worktrees (4 active + 1 dangling - DETECT ONLY)
SUPERPOWTERS = [
    {
        "kind": "superpowers_worktree",
        "path": "/Users/kooshapari/.config/superpowers/worktrees/forgecode/forge-eval-production/.git",
        "expected_target": None,
        "note": "Active superpowers worktree - do not touch",
    },
    {
        "kind": "superpowers_worktree",
        "path": "/Users/kooshapari/.config/superpowers/worktrees/melosviz/feat-b10-conductor/.git",
        "expected_target": None,
        "note": "Active superpowers worktree - do not touch",
    },
    {
        "kind": "superpowers_worktree",
        "path": "/Users/kooshapari/.config/superpowers/worktrees/Tracera/fix-tracera-docker-contract/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/Tracera/.git/worktrees/fix-tracera-docker-contract",
        "note": "DANGLING: superpowers worktree whose target gitdir no longer exists in Tracera. Dir contents intact. Per policy: detect-only.",
    },
    {
        "kind": "superpowers_worktree",
        "path": "/Users/kooshapari/.config/superpowers/worktrees/Tracera-recovery-20260713/tracera-runtime-auth-wbs80-20260714/.git",
        "expected_target": None,
        "note": "Active superpowers worktree - do not touch",
    },
]

# Thegent (1 runtime stub - DETECT ONLY)
THEGENT_STUB = [
    {
        "kind": "thegent_worktree",
        "path": "/Users/kooshapari/.thegent/worktrees/1481461ff257",
        "expected_target": None,
        "note": "Runtime stub - contains agent-1.fallback.lock and pool_state.txt only; not a git worktree (no .git file)",
    },
]

# Venv cache (not a real worktree - just a vendored copy of temporalio SDK)
VENV_IGNORE = [
    {
        "kind": "venv_cache_pointer",
        "path": "/Users/kooshapari/CodeProjects/Phenotype/repos/Grapheon/.venv/lib/python3.13/site-packages/temporalio/bridge/sdk-core/.git",
        "expected_target": "/Users/kooshapari/CodeProjects/Phenotype/repos/Grapheon/.venv/lib/python3.13/site-packages/.git/modules/sdk-core",
        "note": "Python venv cache vendoring temporalio SDK; not a user-managed worktree",
    },
]


def sha256_file(p: Path) -> str:
    """Compute SHA256 of a file (chunked)."""
    h = __import__("hashlib").sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sh(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run shell command, return (rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except Exception as e:
        return -1, "", f"exception: {e}"


def snapshot_dir(parent: Path, dirname: str, safe_name: str) -> tuple[Path | None, str | None]:
    """Snapshot a dir via tar --zstd. Returns (snapshot_path, sha256).

    SHA256SUMS.txt is regenerated from scratch at end-of-run via
    main() so re-runs don't accumulate duplicate entries.
    """
    archive = PARK / f"{safe_name}.tar.zst"
    if archive.exists():
        print(f"  snapshot already exists: {archive.name}")
        return archive, sha256_file(archive)

    rc, _, err = sh([
        "tar",
        "--zstd",
        "-cf",
        str(archive),
        "-C", str(parent),
        dirname,
    ])
    if rc != 0:
        print(f"  tar FAILED rc={rc}: {err.strip()}")
        return None, None

    digest = sha256_file(archive)
    print(f"  snapshot OK: {archive.name} sha256={digest[:12]}...")
    return archive, digest


def verify_snapshot(archive: Path, source_dirname: str) -> tuple[int, int]:
    """Verify an archive by extracting to a tmp dir, counting refs+files.

    Caches the result in <archive>.verify.json to avoid re-extracting
    large archives on every orchestrator run.
    """
    cache = archive.with_suffix(archive.suffix + ".verify.json")
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            return int(data.get("verified_refs", 0)), int(data.get("verified_files", 0))
        except Exception:
            pass  # fall through to re-verify

    tmp = PARK / f".verify-{archive.stem}"
    if tmp.exists():
        sh(["rm", "-rf", str(tmp)])
    sh(["mkdir", "-p", str(tmp)])
    rc2, _, err2 = sh(["tar", "--zstd", "-xf", str(archive), "-C", str(tmp)])
    if rc2 != 0:
        cache.write_text(json.dumps({"verified_refs": 0, "verified_files": 0}))
        return 0, 0

    extracted = tmp / source_dirname
    ref_count = 0
    file_count = 0
    if extracted.is_dir():
        rc3, out, _ = sh([
            "git", "-C", str(extracted), "for-each-ref", "refs/heads/",
        ], timeout=10)
        if rc3 == 0:
            ref_count = len([l for l in out.splitlines() if l.strip()])
        file_count = sum(1 for _ in extracted.rglob("*") if _.is_file())

    sh(["rm", "-rf", str(tmp)])
    cache.write_text(json.dumps({"verified_refs": ref_count, "verified_files": file_count}))
    return ref_count, file_count


def process_audit_orphan(c: dict) -> dict:
    """Audit-orphan candidates: all already gone. Just verify and record."""
    full_path = REPO_ROOT / c["path"]
    exists = full_path.exists()
    initial_state = "missing_file" if not exists else "present"
    return {
        "kind": c["kind"],
        "initial_state": initial_state,
        "action_taken": "already_resolved_no_action",
        "result": "ok" if not exists else "unexpected_present",
        "expected_target": c["expected_target"],
        "note": c["note"],
        "snapshot_path": None,
        "snapshot_sha256": None,
        "verified_refs": 0,
        "new_branch": None,
        "push_rc": None,
        "drop_rc": None,
    }


def process_outer_orphan(c: dict) -> dict:
    """Outer orphans: dirs present but .git pointer broken. Snapshot+drop-pointer.

    If the .git pointer is already gone (post-prior-run cleanup) and the
    snapshot archive exists, mark as `snapshotted_then_dropped_pre_run`.
    """
    gitfile = Path(c["path"])
    archive = PARK / f"{c['snapshot_dirname']}.tar.zst"

    # If pointer is already gone but archive exists → prior-run snapshot
    if not gitfile.exists():
        if archive.exists():
            digest = sha256_file(archive)
            ref_count, file_count = verify_snapshot(archive, c.get("source_dirname", c["snapshot_dirname"]))
            # Write SENTINEL for pre-run case too (idempotent)
            write_sentinel(c, archive, digest, ref_count, file_count)
            return {
                "kind": c["kind"],
                "initial_state": "broken_link",
                "action_taken": "snapshotted_then_dropped_pre_run",
                "result": "ok",
                "expected_target": c["expected_target"],
                "note": c["note"],
                "snapshot_path": str(archive.relative_to(REPO_ROOT)),
                "snapshot_sha256": digest,
                "verified_refs": ref_count,
                "verified_files": file_count,
                "new_branch": None,
                "push_rc": None,
                "drop_rc": 0,
            }
        # No archive either — truly gone
        return {
            "kind": c["kind"],
            "initial_state": "missing_file",
            "action_taken": "skipped_already_gone",
            "result": "ok",
            "expected_target": c["expected_target"],
            "note": c["note"],
            "snapshot_path": None,
            "snapshot_sha256": None,
            "verified_refs": 0,
            "new_branch": None,
            "push_rc": None,
            "drop_rc": 0,
        }

    parent = Path(c["parent_dir"])
    # source_dirname is the actual dir on disk; snapshot_dirname is the archive name
    source = c.get("source_dirname", c["snapshot_dirname"])
    archive_name = c["snapshot_dirname"]
    target_dir = parent / source

    # First: snapshot the entire worktree dir (including broken .git file)
    archive, digest = snapshot_dir(parent, source, archive_name)
    if not archive:
        return {
            "kind": c["kind"],
            "initial_state": "broken_link",
            "action_taken": "snapshot_failed",
            "result": "failure",
            "expected_target": c["expected_target"],
            "note": c["note"] + " | snapshot tar failed",
            "snapshot_path": None,
            "snapshot_sha256": None,
            "verified_refs": 0,
            "new_branch": None,
            "push_rc": None,
            "drop_rc": None,
        }

    # Verify refs in the snapshot (cached via sidecar JSON)
    ref_count, file_count = verify_snapshot(archive, source)

    # Drop the broken .git file (dir remains intact)
    drop_rc, _, drop_err = sh(["rm", "-f", str(gitfile)])
    if drop_rc != 0:
        print(f"  rm .git FAILED rc={drop_rc}: {drop_err.strip()}")

    # Write SENTINEL file
    write_sentinel(c, archive, digest, ref_count, file_count)

    return {
        "kind": c["kind"],
        "initial_state": "broken_link",
        "action_taken": "snapshotted_then_dropped_pointer",
        "result": "ok" if drop_rc == 0 else "drop_failed",
        "expected_target": c["expected_target"],
        "note": c["note"],
        "snapshot_path": str(archive.relative_to(REPO_ROOT)),
        "snapshot_sha256": digest,
        "verified_refs": ref_count,
        "verified_files": file_count,
        "new_branch": None,
        "push_rc": None,
        "drop_rc": drop_rc,
    }


def process_superpowers(c: dict) -> dict:
    """Superpowers worktrees: detect-only, do not touch."""
    full_path = Path(c["path"])
    exists = full_path.exists()
    return {
        "kind": c["kind"],
        "initial_state": "present" if exists else "missing",
        "action_taken": "detected_only_no_action",
        "result": "active-do-not-touch" if exists else "missing",
        "expected_target": c["expected_target"],
        "note": c["note"],
        "snapshot_path": None,
        "snapshot_sha256": None,
        "verified_refs": 0,
        "new_branch": None,
        "push_rc": None,
        "drop_rc": None,
    }


def process_thegent(c: dict) -> dict:
    """Thegent stub: detect-only."""
    full_path = Path(c["path"])
    exists = full_path.exists()
    return {
        "kind": c["kind"],
        "initial_state": "present" if exists else "missing",
        "action_taken": "detected_only_no_action",
        "result": "runtime-stub-not-a-worktree" if exists else "missing",
        "expected_target": c["expected_target"],
        "note": c["note"],
        "snapshot_path": None,
        "snapshot_sha256": None,
        "verified_refs": 0,
        "new_branch": None,
        "push_rc": None,
        "drop_rc": None,
    }


def write_sentinel(c: dict, archive: Path, digest: str, ref_count: int, file_count: int) -> None:
    """Write per-ptr SENTINEL-<safe-filename>.md."""
    safe = c["snapshot_dirname"].replace("/", "_").replace(" ", "_")
    sentinel_path = PARK / f"SENTINEL-{safe}.md"
    body = f"""# SENTINEL: {c["path"]}

- **kind**: `{c["kind"]}`
- **original-path**: `{c["path"]}`
- **expected-target**: `{c["expected_target"]}`
- **note**: {c["note"]}
- **snapshot-path**: `{archive.relative_to(REPO_ROOT)}`
- **sha256**: `{digest}`
- **verified-refs**: {ref_count}
- **verified-files**: {file_count}
- **resolution-date**: {DATE}

> NOTE: `verified-refs` is the count of git refs in the snapshot's
> restored HEAD (`git for-each-ref refs/heads/`). For these broken-pointer
> candidates the parent gitdir was already gone, so refs are 0 — file
> content is preserved but the git history linkage is lost.
> `verified-files` counts the on-disk files preserved in the archive.

## Restore command
```bash
mkdir -p "{c["parent_dir"]}"
tar --zstd -xf "{archive}" -C "{c["parent_dir"]}"
# After restore: re-derive proper gitdir or rebuild worktree via:
#   git worktree repair "{c["parent_dir"]}/{c.get("source_dirname", c["snapshot_dirname"])}"
```

## Verification
```bash
sha256sum -c SHA256SUMS.txt  # matches this entry
# Refs (should match verified-refs):
git -C "{c["parent_dir"]}/{c.get("source_dirname", c["snapshot_dirname"])}" for-each-ref refs/heads/ | wc -l
# Files (should match verified-files):
find "{c["parent_dir"]}/{c.get("source_dirname", c["snapshot_dirname"])}" -type f | wc -l
```
"""
    sentinel_path.write_text(body)


def main() -> int:
    PARK.mkdir(parents=True, exist_ok=True)
    per_ptr: dict[str, dict] = {}
    repaired = 0
    snapshotted_dropped = 0
    left_active = 0
    left_stub = 0
    already_resolved = 0
    failures = 0
    ignored_venv = 0

    # 1. Audit orphans (14)
    print("\n========== AUDIT ORPHANS (14) ==========")
    for c in AUDIT_ORPHANS:
        full = str(REPO_ROOT / c["path"])
        print(f"\n[candidate] {full}")
        result = process_audit_orphan(c)
        per_ptr[full] = result
        if result["action_taken"] == "already_resolved_no_action":
            already_resolved += 1
        elif result["result"] == "failure":
            failures += 1

    # 2. Outer orphans (8)
    print("\n========== OUTER ORPHANS (8) ==========")
    for c in OUTER_ORPHANS:
        full = c["path"]
        print(f"\n[candidate] {full}")
        result = process_outer_orphan(c)
        per_ptr[full] = result
        action = result["action_taken"]
        if action in ("snapshotted_then_dropped_pointer", "snapshotted_then_dropped_pre_run") and result["result"] == "ok":
            snapshotted_dropped += 1
        elif action == "skipped_already_gone":
            already_resolved += 1
        elif result["result"] == "failure":
            failures += 1

    # 3. Superpowers (4)
    print("\n========== SUPERPOWTERS (4) ==========")
    for c in SUPERPOWTERS:
        full = c["path"]
        print(f"\n[candidate] {full}")
        result = process_superpowers(c)
        per_ptr[full] = result
        if result["result"] == "active-do-not-touch":
            left_active += 1

    # 4. Thegent stub (1)
    print("\n========== THEGENT STUB (1) ==========")
    for c in THEGENT_STUB:
        full = c["path"]
        print(f"\n[candidate] {full}")
        result = process_thegent(c)
        per_ptr[full] = result
        if result["result"] == "runtime-stub-not-a-worktree":
            left_stub += 1

    # 5. Venv cache (1) - record but not count toward candidates
    print("\n========== VENV CACHE (1) - IGNORED ==========")
    for c in VENV_IGNORE:
        full = c["path"]
        per_ptr[full] = {
            "kind": c["kind"],
            "initial_state": "present",
            "action_taken": "ignored_venv_cache",
            "result": "not-a-real-worktree",
            "expected_target": c["expected_target"],
            "note": c["note"],
            "snapshot_path": None,
            "snapshot_sha256": None,
            "verified_refs": 0,
            "new_branch": None,
            "push_rc": None,
            "drop_rc": None,
        }
        ignored_venv += 1
        print(f"  ignored (venv cache): {full}")

    audit = {
        "generated_at": DATE,
        "phase": "worktree-pointer-resolution",
        "policy": "aggressive-repair-snapshot-then-delete",
        "candidates_total": len(AUDIT_ORPHANS) + len(OUTER_ORPHANS) + len(SUPERPOWTERS) + len(THEGENT_STUB),
        "repaired": repaired,
        "snapshotted_then_dropped": snapshotted_dropped,
        "left_active": left_active,
        "left_as_stub": left_stub,
        "already_resolved_no_action": already_resolved,
        "failures": failures,
        "venv_cache_ignored": ignored_venv,
        "totals": {
            "audit_orphans": len(AUDIT_ORPHANS),
            "outer_orphans": len(OUTER_ORPHANS),
            "superpowers_worktrees": len(SUPERPOWTERS),
            "thegent_stubs": len(THEGENT_STUB),
        },
        "per_ptr": per_ptr,
    }

    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=False))
    print(f"\n✓ Wrote {AUDIT_JSON}")
    print(f"  candidates_total={audit['candidates_total']}")
    print(f"  repaired={repaired}  snapshotted_then_dropped={snapshotted_dropped}  left_active={left_active}  left_as_stub={left_stub}  already_resolved_no_action={already_resolved}  failures={failures}  venv_cache_ignored={ignored_venv}")

    # Regenerate SHA256SUMS.txt from scratch (idempotent)
    tar_files = sorted(archive.name for archive in PARK.glob("*.tar.zst"))
    if tar_files:
        rc, out, err = sh(["sha256sum", *tar_files], cwd=PARK)
        if rc == 0:
            (PARK / "SHA256SUMS.txt").write_text(out)
            print(f"✓ Regenerated SHA256SUMS.txt ({len(tar_files)} entries)")
        else:
            print(f"WARNING: failed to regenerate SHA256SUMS.txt: {err.strip()}")
    else:
        (PARK / "SHA256SUMS.txt").write_text("")
        print("(no .tar.zst archives; SHA256SUMS.txt cleared)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
