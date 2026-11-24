"""Infrastructure checks for repository reconciliation preflight.

Git operations, file state inspection, category reports, and current-state capture.
"""

from __future__ import annotations

import os
import stat
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from scripts.reconciliation_preflight_check import (
    CurrentSnapshot,
    FileState,
    PreflightError,
    PreflightInputs,
    _canonical_bytes,
    _hash_file,
    _sha256_bytes,
    _validate_sha,
)

_STATIC_GIT_CONTROL_PATHS = {
    ".git/HEAD",
    ".git/config",
    ".git/index",
    ".git/packed-refs",
    ".git/shallow",
}


def _run_git(
    repo_root: Path,
    arguments: list[str],
    *,
    stdin: bytes | None = None,
) -> bytes:
    """Run a bounded git command with hermetic env.

    The function is re-exported via ``scripts.reconciliation_preflight._run_git``
    so monkey-patching tests can target the public name. Local callers
    here use the same name so test patches apply transparently.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
            "SSH_ASKPASS_REQUIRE": "never",
        }
    )
    command = [
        "git",
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=env,
            input=stdin,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise PreflightError("GIT_UNAVAILABLE", "a read-only Git check failed") from exc
    if completed.returncode != 0:
        raise PreflightError("GIT_READ_FAILED", "a read-only Git check failed")
    return completed.stdout


def _file_state(path: Path) -> FileState:
    try:
        before = path.lstat()
    except OSError:
        return FileState("missing", None, None)
    if stat.S_ISLNK(before.st_mode):
        try:
            target = os.readlink(path)
        except OSError:
            target = ""
        return FileState("symlink", before.st_size, _sha256_bytes(os.fsencode(target)))
    if not stat.S_ISREG(before.st_mode):
        marker = f"{before.st_mode}:{before.st_size}".encode()
        return FileState("non_regular", before.st_size, _sha256_bytes(marker))
    try:
        size, digest = _hash_file(path)
        after = path.lstat()
    except OSError:
        return FileState("missing", None, None, raced=True)
    before_key = (before.st_mode, before.st_size, before.st_mtime_ns)
    after_key = (after.st_mode, after.st_size, after.st_mtime_ns)
    return FileState("regular", size, digest, raced=before_key != after_key)


def _current_git_control_paths(repo_root: Path) -> set[str]:
    git_dir = repo_root / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        raise PreflightError(
            "GIT_DIRECTORY_UNSUPPORTED", "local Git directory is unsupported"
        )
    paths = {
        relative
        for relative in _STATIC_GIT_CONTROL_PATHS
        if (repo_root / Path(relative)).is_file()
    }
    for subtree in (git_dir / "refs", git_dir / "logs"):
        if not subtree.exists():
            continue
        for candidate in subtree.rglob("*"):
            if candidate.is_file() and not candidate.is_symlink():
                paths.add(candidate.relative_to(repo_root).as_posix())
    return paths


def _git_control_report(
    repo_root: Path,
    captured: Mapping[str, tuple[int, str]],
) -> tuple[dict[str, Any], list[tuple[str, tuple[Any, ...]]], int, set[str]]:
    captured_paths = {
        path
        for path in captured
        if path in _STATIC_GIT_CONTROL_PATHS
        or path.startswith(".git/refs/")
        or path.startswith(".git/logs/")
    }
    current_paths = _current_git_control_paths(repo_root)
    same = changed = missing = new = raced = 0
    states: list[tuple[str, tuple[Any, ...]]] = []
    for relative in sorted(captured_paths | current_paths):
        if relative not in current_paths:
            state = FileState("missing", None, None)
            missing += 1
        else:
            state = _file_state(repo_root / Path(relative))
            raced += int(state.raced)
            if relative not in captured_paths:
                new += 1
            elif state.kind != "regular":
                changed += 1
            elif (state.size, state.sha256) == captured[relative]:
                same += 1
            else:
                changed += 1
        states.append((relative, state.fingerprint()))
    delta_paths = sorted(
        path
        for path, state in states
        if path not in captured_paths
        or path not in current_paths
        or state[0] != "regular"
        or (state[1], state[2]) != captured.get(path)
    )
    return (
        {
            "checked": len(states),
            "same_as_capture": same,
            "changed_since_capture": changed,
            "missing_since_capture": missing,
            "new_since_capture": new,
            "raced": raced,
            "delta_path_set_sha256": _sha256_bytes(_canonical_bytes(delta_paths)),
        },
        states,
        raced,
        set(delta_paths),
    )


def _category_report(
    repo_root: Path,
    current_paths: Iterable[str],
    captured_category_paths: Iterable[str] | None,
    captured: Mapping[str, tuple[int, str]],
    recorded_exclusions: set[str],
) -> tuple[dict[str, Any], list[tuple[str, tuple[Any, ...]]], int, set[str]]:
    current_set = set(current_paths)
    compare_membership = captured_category_paths is not None
    captured_category_set = set(captured_category_paths or ())
    unique_paths = sorted(current_set | captured_category_set)
    same = changed = absent = non_regular = exclusions = raced = 0
    states: list[tuple[str, tuple[Any, ...]]] = []
    delta_paths = current_set ^ captured_category_set if compare_membership else set()
    for relative in unique_paths:
        state = _file_state(repo_root / Path(relative))
        raced += int(state.raced)
        states.append((relative, state.fingerprint()))
        if state.kind != "regular":
            if state.kind != "missing" and relative in recorded_exclusions:
                exclusions += 1
            else:
                non_regular += 1
                delta_paths.add(relative)
        elif relative not in captured:
            absent += 1
            delta_paths.add(relative)
        elif (state.size, state.sha256) == captured[relative]:
            same += 1
        else:
            changed += 1
            delta_paths.add(relative)
    report = {
        "total": len(unique_paths),
        "same_as_capture": same,
        "changed_since_capture": changed,
        "absent_from_capture": absent,
        "non_regular_or_missing": non_regular,
        "recorded_exclusions": exclusions,
        "added_to_capture_category": (
            len(current_set - captured_category_set) if compare_membership else 0
        ),
        "removed_from_capture_category": (
            len(captured_category_set - current_set) if compare_membership else 0
        ),
        "delta_files": len(delta_paths),
        "raced": raced,
        "all_path_set_sha256": _sha256_bytes(_canonical_bytes(unique_paths)),
        "delta_path_set_sha256": _sha256_bytes(_canonical_bytes(sorted(delta_paths))),
    }
    return report, states, raced, set(delta_paths)


def _captured_payload_report(
    repo_root: Path,
    captured: Mapping[str, tuple[int, str]],
) -> tuple[dict[str, Any], list[tuple[str, tuple[Any, ...]]], int, set[str]]:
    payload_paths = sorted(path for path in captured if not path.startswith(".git/"))
    same = changed = missing = non_regular = raced = 0
    states: list[tuple[str, tuple[Any, ...]]] = []
    delta_paths: set[str] = set()
    for relative in payload_paths:
        state = _file_state(repo_root / Path(relative))
        raced += int(state.raced)
        states.append((relative, state.fingerprint()))
        if state.kind == "missing":
            missing += 1
            delta_paths.add(relative)
        elif state.kind != "regular":
            non_regular += 1
            delta_paths.add(relative)
        elif (state.size, state.sha256) == captured[relative]:
            same += 1
        else:
            changed += 1
            delta_paths.add(relative)
    report = {
        "checked": len(payload_paths),
        "same_as_capture": same,
        "changed_since_capture": changed,
        "missing_since_capture": missing,
        "non_regular_since_capture": non_regular,
        "delta_files": len(delta_paths),
        "raced": raced,
        "delta_path_set_sha256": _sha256_bytes(_canonical_bytes(sorted(delta_paths))),
    }
    return report, states, raced, delta_paths


def _current_git_object_paths(repo_root: Path) -> set[str]:
    object_root = repo_root / ".git" / "objects"
    if not object_root.is_dir() or object_root.is_symlink():
        raise PreflightError("GIT_OBJECT_STORE_INVALID", "Git object store is invalid")
    paths: set[str] = set()
    for directory, directory_names, file_names in os.walk(
        object_root, followlinks=False
    ):
        directory_path = Path(directory)
        retained_directories: list[str] = []
        for name in directory_names:
            candidate = directory_path / name
            if candidate.is_symlink():
                paths.add(candidate.relative_to(repo_root).as_posix())
            else:
                retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in file_names:
            paths.add((directory_path / name).relative_to(repo_root).as_posix())
    return paths


def _git_object_report(
    repo_root: Path,
    captured: Mapping[str, tuple[int, str]],
) -> tuple[dict[str, Any], list[tuple[str, tuple[Any, ...]]], int, set[str]]:
    captured_paths = {path for path in captured if path.startswith(".git/objects/")}
    current_paths = _current_git_object_paths(repo_root)
    same = changed = missing = new = non_regular = raced = 0
    states: list[tuple[str, tuple[Any, ...]]] = []
    delta_paths: set[str] = set()
    for relative in sorted(captured_paths | current_paths):
        state = _file_state(repo_root / Path(relative))
        raced += int(state.raced)
        states.append((relative, state.fingerprint()))
        if relative not in captured_paths:
            new += 1
            delta_paths.add(relative)
            if state.kind != "regular":
                non_regular += 1
        elif state.kind == "missing":
            missing += 1
            delta_paths.add(relative)
        elif state.kind != "regular":
            non_regular += 1
            delta_paths.add(relative)
        elif (state.size, state.sha256) == captured[relative]:
            same += 1
        else:
            changed += 1
            delta_paths.add(relative)
    report = {
        "captured": len(captured_paths),
        "current": len(current_paths),
        "same_as_capture": same,
        "changed_since_capture": changed,
        "missing_since_capture": missing,
        "new_since_capture": new,
        "non_regular": non_regular,
        "delta_files": len(delta_paths),
        "raced": raced,
        "delta_path_set_sha256": _sha256_bytes(_canonical_bytes(sorted(delta_paths))),
    }
    return report, states, raced, delta_paths


def _decode_nul_paths(payload: bytes) -> list[str]:
    return sorted(
        item.decode("utf-8", errors="surrogateescape")
        for item in payload.split(b"\x00")
        if item
    )


def _decode_unmerged_paths(payload: bytes) -> list[str]:
    paths: set[str] = set()
    for item in payload.split(b"\x00"):
        if not item:
            continue
        _metadata, separator, raw_path = item.partition(b"\t")
        if not separator:
            raise PreflightError("GIT_READ_FAILED", "a read-only Git check failed")
        paths.add(raw_path.decode("utf-8", errors="surrogateescape"))
    return sorted(paths)


def _verify_local_graph(inputs: PreflightInputs) -> dict[str, Any]:

    current_head = (
        _run_git(inputs.repo_root, ["rev-parse", "HEAD"]).decode().strip().lower()
    )
    if _validate_sha(current_head) != inputs.expected_local_sha:
        raise PreflightError("LOCAL_HEAD_MISMATCH", "local HEAD does not match")
    _run_git(
        inputs.repo_root, ["cat-file", "-e", f"{inputs.expected_base_sha}^{{commit}}"]
    )
    _run_git(
        inputs.repo_root, ["cat-file", "-e", f"{inputs.expected_local_sha}^{{commit}}"]
    )
    merge_base = (
        _run_git(
            inputs.repo_root,
            ["merge-base", inputs.expected_base_sha, inputs.expected_local_sha],
        )
        .decode()
        .strip()
        .lower()
    )
    if merge_base != inputs.expected_base_sha:
        raise PreflightError(
            "LOCAL_BASE_MISMATCH", "local history boundary does not match"
        )
    local_only = int(
        _run_git(
            inputs.repo_root,
            [
                "rev-list",
                "--count",
                f"{inputs.expected_base_sha}..{inputs.expected_local_sha}",
            ],
        )
        .decode()
        .strip()
    )
    shallow = (
        _run_git(inputs.repo_root, ["rev-parse", "--is-shallow-repository"])
        .decode()
        .strip()
        == "true"
    )
    return {
        "verified": True,
        "head_sha": current_head,
        "base_sha": merge_base,
        "local_only_commits": local_only,
        "shallow_repository": shallow,
    }


def _capture_current_state(
    repo_root: Path,
    captured: Mapping[str, tuple[int, str]],
    recorded_exclusions: set[str],
    captured_categories: Mapping[str, set[str]],
) -> CurrentSnapshot:
    # Import from the public re-export module so monkey-patching tests
    # that target ``scripts.reconciliation_preflight._run_git`` apply.
    from scripts.reconciliation_preflight import _run_git
    from scripts.reconciliation_preflight_check import CurrentSnapshot

    local_head = _run_git(repo_root, ["rev-parse", "HEAD"]).decode().strip().lower()
    unstaged = _decode_nul_paths(
        _run_git(
            repo_root,
            ["diff-files", "--no-ext-diff", "--name-only", "-z", "--"],
        )
    )
    staged = _decode_nul_paths(
        _run_git(
            repo_root,
            [
                "diff-index",
                "--no-ext-diff",
                "--cached",
                "--name-only",
                "-z",
                "HEAD",
                "--",
            ],
        )
    )
    unmerged = _decode_unmerged_paths(
        _run_git(repo_root, ["ls-files", "--unmerged", "-z"])
    )
    categories_to_paths = {
        "tracked": sorted(set(unstaged) | set(staged) | set(unmerged)),
        "untracked": _decode_nul_paths(
            _run_git(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"])
        ),
        "ignored": _decode_nul_paths(
            _run_git(
                repo_root,
                ["ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
            )
        ),
    }
    category_reports: dict[str, Mapping[str, Any]] = {}
    state_material: dict[str, Any] = {"local_head": local_head}
    race_count = 0
    all_delta_paths: set[str] = set()
    for name, paths in categories_to_paths.items():
        report, states, raced, delta_paths = _category_report(
            repo_root,
            paths,
            captured_categories.get(name),
            captured,
            recorded_exclusions,
        )
        category_reports[name] = report
        state_material[name] = {"report": report, "states": states}
        race_count += raced
        all_delta_paths.update(delta_paths)
    payload_report, payload_states, raced, delta_paths = _captured_payload_report(
        repo_root, captured
    )
    race_count += raced
    all_delta_paths.update(delta_paths)
    state_material["captured_payload"] = payload_states
    control_report, control_states, raced, delta_paths = _git_control_report(
        repo_root, captured
    )
    race_count += raced
    all_delta_paths.update(delta_paths)
    state_material["git_controls"] = control_states
    object_report, object_states, raced, delta_paths = _git_object_report(
        repo_root, captured
    )
    race_count += raced
    all_delta_paths.update(delta_paths)
    state_material["git_objects"] = object_states
    fingerprint = _sha256_bytes(_canonical_bytes(state_material))
    return CurrentSnapshot(
        fingerprint=fingerprint,
        local_head=local_head,
        categories=category_reports,
        captured_payload=payload_report,
        git_controls=control_report,
        git_objects=object_report,
        race_count=race_count,
        delta_paths=frozenset(all_delta_paths),
    )


def _delta_total(snapshot: CurrentSnapshot) -> int:
    return len(snapshot.delta_paths)
