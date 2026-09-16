"""Download logic for GitHub reconciliation snapshot acquisition.

This module contains the GitHub CLI client, bounded stream readers,
and command execution infrastructure.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, BinaryIO

SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,99})/"
    r"[A-Za-z0-9_.-](?:[A-Za-z0-9_.-]{0,99})$"
)

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_ATTEMPTS = 3
BRANCH_PAGE_SIZE = 100
MAX_BRANCH_PAGE_REQUESTS = 65
API_VERSION = "2026-03-10"
API_HOST = "github.com"

REPOSITORY_FILTER = (
    "{full_name:.full_name,private:.private,archived:.archived,"
    "default_branch:.default_branch}"
)
BRANCH_FILTER = "map({name:.name,sha:.commit.sha})"
DEFAULT_BRANCH_FILTER = "{name:.name,sha:.commit.sha}"
COMPARE_FILTER = (
    "{status:.status,ahead_by:.ahead_by,behind_by:.behind_by,"
    "total_commits:.total_commits,base_sha:.base_commit.sha,"
    "merge_base_sha:.merge_base_commit.sha}"
)


class SnapshotError(RuntimeError):
    """A fail-closed error whose message is safe to emit."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


class CommandResult:
    __slots__ = (
        "returncode",
        "stdout",
        "stderr",
        "stdout_exceeded",
        "stderr_exceeded",
        "stream_failed",
        "timed_out",
    )

    def __init__(
        self,
        returncode: int,
        stdout: bytes,
        stderr: bytes = b"",
        stdout_exceeded: bool = False,
        stderr_exceeded: bool = False,
        stream_failed: bool = False,
        timed_out: bool = False,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_exceeded = stdout_exceeded
        self.stderr_exceeded = stderr_exceeded
        self.stream_failed = stream_failed
        self.timed_out = timed_out

    def __repr__(self) -> str:
        return (
            f"CommandResult(returncode={self.returncode}, "
            f"stdout_exceeded={self.stdout_exceeded}, "
            f"stderr_exceeded={self.stderr_exceeded})"
        )


@dataclass(slots=True)
class SnapshotOptions:
    repository: str
    expected_default_branch: str
    base_sha: str
    local_sha: str
    expected_live_sha: str | None = None
    expected_branches: tuple[tuple[str, str], ...] = ()
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    attempts: int = DEFAULT_ATTEMPTS


@dataclass(slots=True)
class _Observation:
    repository: Mapping[str, Any]
    branches: tuple[tuple[str, str], ...]


CommandRunner = Callable[..., CommandResult]


def _canonical_bytes(value: Any) -> bytes:
    import json

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SnapshotError(
                "API_RESPONSE_DUPLICATE_KEY",
                "GitHub returned JSON with a duplicate key",
            )
        value[key] = item
    return value


def _reject_constant(_value: str) -> None:
    raise SnapshotError("API_RESPONSE_INVALID", "GitHub returned invalid JSON data")


def _decode_json(payload: bytes) -> Any:
    import json

    if not payload or len(payload) > MAX_RESPONSE_BYTES:
        raise SnapshotError(
            "API_RESPONSE_TOO_LARGE", "GitHub response violates the size bound"
        )
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_closed_object,
            parse_constant=_reject_constant,
        )
    except SnapshotError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(
            "API_RESPONSE_INVALID", "GitHub returned invalid UTF-8 JSON"
        ) from exc


def _require_exact_keys(
    payload: Mapping[str, Any], expected: set[str], *, code: str
) -> None:
    if set(payload) != expected:
        raise SnapshotError(code, "GitHub response fields do not match the contract")


def _valid_branch_name(name: str) -> bool:
    if (
        not name
        or len(name) > 1024
        or name.startswith(("/", "."))
        or name.endswith(("/", "."))
    ):
        return False
    if any(token in name for token in {"..", "@{", "//"}):
        return False
    return re.search(r"[\x00-\x20~^:?*\[]", name) is None


def _validate_sha(raw: str, *, code: str = "ARGUMENT_SHA_INVALID") -> str:
    value = raw.lower()
    if SHA_RE.fullmatch(value) is None:
        raise SnapshotError(code, "a Git object ID is invalid")
    return value


def _gh_environment() -> dict[str, str]:
    blocked = {
        "DEBUG",
        "GH_DEBUG",
        "GH_FORCE_TTY",
        "GH_PAGER",
        "PAGER",
    }
    environment = {
        key: value for key, value in os.environ.items() if key.upper() not in blocked
    }
    environment.update(
        {
            "CLICOLOR": "0",
            "GH_NO_UPDATE_NOTIFIER": "1",
            "GH_PROMPT_DISABLED": "1",
            "NO_COLOR": "1",
        }
    )
    return environment


def _bounded_reader(
    stream: BinaryIO,
    limit: int,
    process: subprocess.Popen[bytes],
    result: dict[str, Any],
    key: str,
) -> None:
    payload = bytearray()
    exceeded = False
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            remaining = max(0, limit - len(payload))
            payload.extend(chunk[:remaining])
            if len(chunk) > remaining:
                exceeded = True
                try:
                    process.kill()
                except OSError:
                    pass
    except Exception:
        result[f"{key}_failed"] = True
        try:
            process.kill()
        except OSError:
            pass
    finally:
        result[key] = bytes(payload)
        result[f"{key}_exceeded"] = exceeded


def _run_command(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> CommandResult:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_gh_environment(),
            shell=False,
            creationflags=creationflags,
        )
    except (FileNotFoundError, OSError) as exc:
        raise SnapshotError(
            "GH_UNAVAILABLE", "GitHub CLI could not be started"
        ) from exc
    assert process.stdout is not None
    assert process.stderr is not None
    captured: dict[str, Any] = {}
    stdout_thread = threading.Thread(
        target=_bounded_reader,
        args=(process.stdout, max_stdout_bytes, process, captured, "stdout"),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_bounded_reader,
        args=(process.stderr, max_stderr_bytes, process, captured, "stderr"),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        returncode = process.wait()
    stdout_thread.join(timeout=2.0)
    stderr_thread.join(timeout=2.0)
    if stdout_thread.is_alive() or stderr_thread.is_alive():
        try:
            process.stdout.close()
            process.stderr.close()
        except OSError:
            pass
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
        captured["stream_failed"] = True
    return CommandResult(
        returncode=returncode,
        stdout=captured.get("stdout", b""),
        stderr=captured.get("stderr", b""),
        stdout_exceeded=bool(captured.get("stdout_exceeded")),
        stderr_exceeded=bool(captured.get("stderr_exceeded")),
        stream_failed=bool(
            captured.get("stream_failed")
            or captured.get("stdout_failed")
            or captured.get("stderr_failed")
        ),
        timed_out=timed_out,
    )


class _GhClient:
    def __init__(
        self,
        *,
        runner: CommandRunner,
        timeout_seconds: float,
        attempts: int,
        sleeper: Callable[[float], None],
    ) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds
        self._attempts = attempts
        self._sleeper = sleeper

    def get_json(self, endpoint: str, jq_filter: str) -> Any:
        command = [
            "gh",
            "api",
            "--method",
            "GET",
            "--hostname",
            API_HOST,
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            f"X-GitHub-Api-Version: {API_VERSION}",
            "--jq",
            jq_filter,
            endpoint,
        ]
        last_error: SnapshotError | None = None
        for attempt in range(self._attempts):
            try:
                result = self._runner(
                    command,
                    timeout_seconds=self._timeout_seconds,
                    max_stdout_bytes=MAX_RESPONSE_BYTES,
                    max_stderr_bytes=MAX_STDERR_BYTES,
                )
                if result.timed_out:
                    raise SnapshotError(
                        "API_REQUEST_TIMEOUT",
                        "GitHub GET request timed out",
                        retryable=True,
                    )
                if result.stream_failed:
                    raise SnapshotError(
                        "API_STREAM_FAILED",
                        "GitHub response stream failed a bounded read",
                        retryable=True,
                    )
                if result.stdout_exceeded:
                    raise SnapshotError(
                        "API_RESPONSE_TOO_LARGE",
                        "GitHub response violates the size bound",
                    )
                if result.stderr_exceeded:
                    raise SnapshotError(
                        "API_DIAGNOSTIC_TOO_LARGE",
                        "GitHub diagnostics violate the size bound",
                    )
                if result.returncode != 0:
                    raise SnapshotError(
                        "API_REQUEST_FAILED",
                        "GitHub GET request failed",
                        retryable=True,
                    )
                return _decode_json(result.stdout)
            except SnapshotError as exc:
                last_error = exc
                if not exc.retryable or attempt + 1 == self._attempts:
                    raise
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = SnapshotError(
                    "API_REQUEST_FAILED",
                    "GitHub GET request failed",
                    retryable=True,
                )
                if attempt + 1 == self._attempts:
                    raise last_error from exc
            self._sleeper(0.25 * (2**attempt))
        assert last_error is not None
        raise last_error
