#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _command_plan_hash(commands: list[dict]) -> str:
    payload = json.dumps(commands, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _canonicalize_plan(commands: list[dict]) -> list[dict]:
    return sorted(
        [
            {
                "command": command.command,
                "bucket": command.bucket.value,
                "required": command.required,
                "cwd": command.cwd,
                "source": command.source,
                "rationale": command.rationale,
            }
            for command in commands
        ],
        key=lambda entry: (
            entry["bucket"],
            entry["required"],
            entry["command"],
            entry["source"],
            entry["cwd"],
        ),
    )


def _plan_diff(before: list[dict], after: list[dict]) -> dict[str, list[str]]:
    before_set = {entry.get("command", "") for entry in before}
    after_set = {entry.get("command", "") for entry in after}
    return {
        "added": sorted(after_set - before_set),
        "removed": sorted(before_set - after_set),
    }


def _iter_commands(discovery) -> list[dict]:
    return [
        {
            "command": command.command,
            "bucket": command.bucket.value,
            "required": command.required,
            "cwd": command.cwd,
            "source": command.source,
            "rationale": command.rationale,
        }
        for bucket in discovery.buckets.values()
        for command in bucket
    ]


def _reproducibility_metadata(profile: str, args) -> dict:
    return {
        "profile": profile,
        "runner_config": {
            "max_parallel": args.max_parallel,
            "timeout": args.timeout,
            "retries": args.retries,
            "retry_delay": args.retry_delay,
            "continue_on_fail": bool(args.continue_on_fail),
            "budget_seconds": args.budget,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "working_dir": str(Path.cwd()),
            "argv": sys.argv,
            "pid": os.getpid(),
        },
    }


def _subject_ref(discovery) -> str:
    """Return a stable ref for a Git checkout, including detached HEADs."""
    if discovery.manifest.branch:
        return discovery.manifest.branch
    if discovery.manifest.commit:
        return f"detached:{discovery.manifest.commit}"
    return ""


def _write_output(out: str, content: str) -> None:
    """Write output only after enforcing the invoking workspace boundary.

    Output paths come from CLI arguments and are therefore treated as
    untrusted.  Canonicalizing before the containment check also prevents a
    symlink in the requested path from escaping the workspace boundary.
    """
    workspace = os.path.realpath(os.getcwd())
    candidate = os.path.expanduser(out)
    resolved = os.path.realpath(
        candidate if os.path.isabs(candidate) else os.path.join(workspace, candidate)
    )
    try:
        common_root = os.path.commonpath((workspace, resolved))
    except ValueError as exc:
        raise ValueError(f"output path must remain inside the invoking workspace: {out!r}") from exc
    if common_root != workspace:
        raise ValueError(f"output path must remain inside the invoking workspace: {out!r}")
    if resolved == workspace:
        raise ValueError("output path must name a file inside the invoking workspace")
    relative_parts = Path(os.path.relpath(resolved, workspace)).parts
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(workspace, directory_flags | nofollow)
    try:
        for part in relative_parts[:-1]:
            next_fd = os.open(part, directory_flags | nofollow, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        output_fd = os.open(
            relative_parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | nofollow,
            0o644,
            dir_fd=directory_fd,
        )
        with os.fdopen(output_fd, "w") as output_file:
            output_file.write(content)
    finally:
        os.close(directory_fd)


def _write_unresolved_provenance(payload: dict, out: str, repo: str, subject_ref: str) -> None:
    """Emit an explicit warning instead of fabricating an envelope for non-Git input."""
    payload["result_code"] = "WARN"
    payload["provenance"] = {
        "status": "unresolved",
        "reason": "non_git_repository",
        "collector": "helios-harness",
        "source_ref": subject_ref or None,
        "source_sha": None,
        "repo": repo,
    }
    payload["result"] = {
        "status": "warning",
        "failure_class": "provenance_unresolved",
    }
    _write_output(out, json.dumps(payload, indent=2))


def run_discovery(root: str, out: str, max_scan_depth: int) -> None:
    from harness.discoverer import Discoverer
    from harness.interfaces import DiscoverInput

    discoverer = Discoverer()
    discovery = discoverer.discover(DiscoverInput(repo_root=root, max_scan_depth=max_scan_depth))
    _write_output(out, discovery.to_json())


def run_runner(repo: str, profile: str, out: str, args) -> None:
    from harness.benchmark_envelope import add_envelope, stored_plan_hash
    from harness.discoverer import Discoverer
    from harness.interfaces import DiscoverInput
    from harness.normalizer import QualityNormalizer
    from harness.runner import Runner, RunnerConfig
    from harness.schema import evidence_payload

    discoverer = Discoverer()
    discovery = discoverer.discover(DiscoverInput(repo_root=repo))
    flat_commands = [cmd for bucket in discovery.buckets.values() for cmd in bucket]

    commands = _canonicalize_plan(flat_commands)
    command_hash = _command_plan_hash(commands)

    replay_payload = None
    plan_diff = None
    if args.replay:
        prior_path = Path(args.replay)
        if prior_path.exists():
            prior_payload = json.loads(prior_path.read_text())
            prior_commands = prior_payload.get("plan")
            if not isinstance(prior_commands, list):
                prior_commands = prior_payload.get("commands")
            if isinstance(prior_commands, list):
                prior_plan = [
                    {
                        "command": c.get("command", ""),
                        "bucket": c.get("bucket", ""),
                        "required": c.get("required", False),
                        "cwd": c.get("cwd", "."),
                        "source": c.get("source", ""),
                        "rationale": c.get("rationale", ""),
                    }
                    for c in prior_commands
                ]
                prior_plan = sorted(
                    prior_plan,
                    key=lambda entry: (
                        entry["bucket"],
                        entry["required"],
                        entry["command"],
                        entry["source"],
                        entry["cwd"],
                    ),
                )
                prior_hash = _command_plan_hash(prior_plan)
            else:
                prior_hash = stored_plan_hash(prior_payload)
                prior_plan = []
            replay_payload = {
                "path": str(prior_path),
                "prior_plan_hash": prior_hash,
                "same_plan": prior_hash == command_hash,
            }
            plan_diff = _plan_diff(prior_plan, commands)

    result = {
        "repo": repo,
        "profile": profile,
        "created_at": datetime.now(tz=UTC).isoformat(),
        "plan_hash": command_hash,
        "plan": commands,
        "command_count": len(commands),
        "reproducibility": _reproducibility_metadata(profile, args),
        "fixture": {
            "kind": "discovered-repository",
            "repo": repo,
            "ref": _subject_ref(discovery) or None,
            "commit": discovery.manifest.commit,
            "plan_sha256": command_hash,
        },
    }

    subject_ref = _subject_ref(discovery)
    if not discovery.manifest.commit or not subject_ref:
        _write_unresolved_provenance(result, out, repo, subject_ref)
        return

    if replay_payload is not None:
        result["replay"] = {
            **replay_payload,
            "plan_diff": plan_diff,
        }

    if args.dry_run:
        result["result_code"] = "WARN" if not commands else "PASS"
        result = add_envelope(
            result,
            repo=repo,
            plan_hash=command_hash,
            subject_commit=discovery.manifest.commit or "",
            subject_ref=subject_ref,
        )
        _write_output(out, json.dumps(result, indent=2))
        return

    runner = Runner(
        RunnerConfig(
            timeout_seconds=args.timeout,
            continue_on_fail=args.continue_on_fail,
            max_parallel_jobs=args.max_parallel,
            profile=profile,
            retries=args.retries,
            retry_delay_seconds=args.retry_delay,
            budget_seconds=args.budget,
        )
    )
    runs = runner.run_profile(flat_commands, repo)
    normalization = QualityNormalizer().normalize(runs, flat_commands)
    payload = evidence_payload(discovery, runs, normalization)
    payload["plan_hash"] = command_hash
    payload["reproducibility"] = _reproducibility_metadata(profile, args)
    payload["created_at"] = datetime.now(tz=UTC).isoformat()
    payload["command_count"] = len(commands)
    payload["fixture"] = {
        "kind": "discovered-repository",
        "repo": repo,
        "ref": subject_ref or None,
        "commit": discovery.manifest.commit,
        "plan_sha256": command_hash,
    }
    if args.replay:
        replay_path = Path(args.replay)
        if replay_payload is None and replay_path.exists():
            prior = json.loads(replay_path.read_text())
            prior_commands = prior.get("plan")
            if not isinstance(prior_commands, list):
                prior_commands = prior.get("commands")
            prior_hash = stored_plan_hash(prior)
            if prior_hash is None and isinstance(prior_commands, list):
                prior_plan = [
                    {
                        "command": c.get("command", ""),
                        "bucket": c.get("bucket", ""),
                        "required": c.get("required", False),
                        "cwd": c.get("cwd", "."),
                        "source": c.get("source", ""),
                        "rationale": c.get("rationale", ""),
                    }
                    for c in prior_commands
                ]
                prior_plan = sorted(
                    prior_plan,
                    key=lambda entry: (
                        entry["bucket"],
                        entry["required"],
                        entry["command"],
                        entry["source"],
                        entry["cwd"],
                    ),
                )
                prior_hash = _command_plan_hash(prior_plan)
            payload["replay"] = {
                "path": str(replay_path),
                "prior_plan_hash": prior_hash,
                "same_plan": prior_hash == command_hash,
                "plan_diff": _plan_diff(prior_commands or [], commands),
            }
        elif replay_payload is not None:
            payload["replay"] = {
                **replay_payload,
                "plan_hash": command_hash,
                "plan_diff": plan_diff,
            }

    if not discovery.manifest.commit or not subject_ref:
        _write_unresolved_provenance(payload, out, repo, subject_ref)
        return

    payload = add_envelope(
        payload,
        repo=repo,
        plan_hash=command_hash,
        subject_commit=discovery.manifest.commit or "",
        subject_ref=subject_ref,
    )

    _write_output(out, json.dumps(payload, indent=2))


def normalize_run(input_file: str, out: str) -> None:
    payload = json.loads(Path(input_file).read_text())
    from harness.interfaces import RunResult
    from harness.normalizer import QualityNormalizer

    raw_runs = payload.get("runs", [])
    if not raw_runs:
        raise SystemExit("input file missing runs")

    runs = [
        RunResult(
            command=run.get("command"),
            bucket=run.get("bucket", ""),
            returncode=run.get("returncode", 0),
            started_at=run.get("started_at", ""),
            finished_at=run.get("finished_at", ""),
            stdout_file=run.get("stdout_file", ""),
            stderr_file=run.get("stderr_file", ""),
            duration_ms=run.get("duration_ms", 0),
            artifact_dir=run.get("artifact_dir", ""),
            attempts=run.get("attempts", 1),
            timed_out=run.get("timed_out", False),
            error=run.get("error"),
            skipped=run.get("skipped", False),
        )
        for run in raw_runs
    ]

    discovered_commands = payload.get("commands", [])
    result = QualityNormalizer().normalize(runs, discovered_commands)
    _write_output(
        out, json.dumps({"quality": result.__dict__, "source": str(input_file)}, indent=2)
    )


def validate_artifacts(schema: str, file: str) -> None:
    from jsonschema import validate

    payload = json.loads(Path(file).read_text())
    schema_json = json.loads(Path(schema).read_text())
    validate(instance=payload, schema=schema_json)
    print("VALID")


def main() -> None:
    from harness.commands import (
        cmd_cache_clear,
        cmd_cache_stats,
        cmd_scaling_status,
        cmd_teammates_delegate,
        cmd_teammates_list,
        cmd_teammates_status,
    )

    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)

    d = sp.add_parser("discover")
    d.add_argument("--root", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--max-scan-depth", type=int, default=3)

    r = sp.add_parser("run")
    r.add_argument("--repo", required=True)
    r.add_argument("--profile", default="strict-full")
    r.add_argument("--out", required=True)
    r.add_argument("--max-parallel", type=int, default=2)
    r.add_argument("--timeout", type=int, default=1200)
    r.add_argument("--retries", type=int, default=0)
    r.add_argument("--retry-delay", type=float, default=1.0)
    r.add_argument("--budget", type=int)
    r.add_argument("--continue-on-fail", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--replay")

    n = sp.add_parser("normalize")
    n.add_argument("--in", dest="input_file", required=True)
    n.add_argument("--out", required=True)

    v = sp.add_parser("validate")
    v.add_argument("--schema", required=True)
    v.add_argument("--file", required=True)

    # Teammates commands
    t = sp.add_parser("teammates")
    t_sp = t.add_subparsers(dest="teammates_cmd")

    t_list = t_sp.add_parser("list")
    t_list.add_argument("--agents-dir", default="agents")

    t_delegate = t_sp.add_parser("delegate")
    t_delegate.add_argument("--teammate", required=True)
    t_delegate.add_argument("--task", required=True)
    t_delegate.add_argument("--timeout", type=int, default=300)
    t_delegate.add_argument("--profile", default="default")

    t_status = t_sp.add_parser("status")
    t_status.add_argument("--delegation-id", required=True)

    # Scaling commands
    s = sp.add_parser("scaling")
    s_sp = s.add_subparsers(dest="scaling_cmd")

    s_sp.add_parser("status")

    # Cache commands
    c = sp.add_parser("cache")
    c_sp = c.add_subparsers(dest="cache_cmd")

    c_sp.add_parser("stats")
    c_sp.add_parser("clear")

    args = p.parse_args()

    if args.cmd == "discover":
        run_discovery(args.root, args.out, args.max_scan_depth)
    elif args.cmd == "run":
        run_runner(args.repo, args.profile, args.out, args)
    elif args.cmd == "normalize":
        normalize_run(args.input_file, args.out)
    elif args.cmd == "validate":
        validate_artifacts(args.schema, args.file)
    elif args.cmd == "teammates":
        if args.teammates_cmd == "list":
            cmd_teammates_list(args.agents_dir)
        elif args.teammates_cmd == "delegate":
            cmd_teammates_delegate(args.teammate, args.task, args.timeout, args.profile)
        elif args.teammates_cmd == "status":
            cmd_teammates_status(args.delegation_id)
    elif args.cmd == "scaling":
        if args.scaling_cmd == "status":
            cmd_scaling_status()
    elif args.cmd == "cache":
        if args.cache_cmd == "stats":
            cmd_cache_stats()
        elif args.cache_cmd == "clear":
            cmd_cache_clear()


if __name__ == "__main__":
    main()
