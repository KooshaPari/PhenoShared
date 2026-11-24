from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from scripts import acquire_reconciliation_remote_snapshot as acquisition
from scripts import reconciliation_preflight as preflight

BASE = "1" * 40
LOCAL = "2" * 40
LIVE = "3" * 40
FEATURE = "4" * 40
REPOSITORY = "example/pheno"


def _json_result(value: object, *, returncode: int = 0) -> acquisition.CommandResult:
    return acquisition.CommandResult(
        returncode=returncode,
        stdout=acquisition._canonical_bytes(value),
        stderr=b"secret-bearing diagnostics must remain captured",
    )


def _repo() -> dict[str, object]:
    return {
        "archived": False,
        "default_branch": "main",
        "full_name": REPOSITORY,
        "private": True,
    }


def _branches(live: str = LIVE) -> list[dict[str, str]]:
    return [
        {"name": "feat/kernel", "sha": FEATURE},
        {"name": "main", "sha": live},
    ]


def _compare() -> dict[str, object]:
    return {
        "ahead_by": 18,
        "base_sha": BASE,
        "behind_by": 0,
        "merge_base_sha": BASE,
        "status": "ahead",
        "total_commits": 18,
    }


class FakeRunner:
    def __init__(self, responses: list[acquisition.CommandResult]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, command, **kwargs):
        self.calls.append((list(command), dict(kwargs)))
        if not self.responses:
            raise AssertionError(f"unexpected command: {command!r}")
        return self.responses.pop(0)


def _stable_responses() -> list[acquisition.CommandResult]:
    observation = [
        _json_result(_repo()),
        _json_result(_branches()),
        _json_result({"name": "main", "sha": LIVE}),
    ]
    return [*observation, _json_result(_compare()), *observation]


def _options(**changes) -> acquisition.SnapshotOptions:
    value = acquisition.SnapshotOptions(
        repository=REPOSITORY,
        expected_default_branch="main",
        base_sha=BASE,
        local_sha=LOCAL,
        timeout_seconds=3,
        attempts=1,
    )
    return replace(value, **changes)


class RemoteSnapshotAcquisitionTests(unittest.TestCase):
    def test_success_is_canonical_get_only_and_preflight_compatible(self) -> None:
        runner = FakeRunner(_stable_responses())
        captured = datetime(2026, 7, 15, 5, 6, 7, tzinfo=UTC)
        snapshot = acquisition.acquire_snapshot(
            _options(),
            runner=runner,
            sleeper=lambda _delay: None,
            clock=lambda: captured,
        )
        self.assertEqual(acquisition.SCHEMA_VERSION, snapshot["schema_version"])
        self.assertEqual("2026-07-15T05:06:07Z", snapshot["captured_at_utc"])
        self.assertEqual(LIVE, snapshot["live_sha"])
        self.assertEqual(
            ["feat/kernel", "main"],
            [item["name"] for item in snapshot["branches"]],
        )
        self.assertEqual(snapshot, json.loads(acquisition._canonical_bytes(snapshot)))

        for command, kwargs in runner.calls:
            self.assertEqual(["gh", "api"], command[:2])
            self.assertIn("--method", command)
            self.assertEqual("GET", command[command.index("--method") + 1])
            self.assertNotIn("--field", command)
            self.assertNotIn("--raw-field", command)
            self.assertNotIn("--input", command)
            self.assertFalse(any("token" in item.casefold() for item in command))
            self.assertEqual(acquisition.MAX_RESPONSE_BYTES, kwargs["max_stdout_bytes"])
        compare_calls = [
            command for command, _kwargs in runner.calls if "/compare/" in command[-1]
        ]
        self.assertEqual(1, len(compare_calls))
        self.assertTrue(compare_calls[0][-1].endswith("?per_page=1&page=2"))

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "snapshot.cjson"
            raw = acquisition._canonical_bytes(snapshot) + b"\n"
            path.write_bytes(raw)
            inputs = preflight.PreflightInputs(
                repo_root=Path(temporary),
                packet=Path(temporary),
                packet_checksum_manifest_sha256="a" * 64,
                remote_snapshot=path,
                remote_snapshot_sha256=hashlib.sha256(raw).hexdigest(),
                expected_repository=REPOSITORY,
                expected_default_branch="main",
                expected_base_sha=BASE,
                expected_local_sha=LOCAL,
                expected_live_sha=LIVE,
                expected_branches=(("feat/kernel", FEATURE), ("main", LIVE)),
            )
            report = preflight._verify_remote_snapshot(inputs)
            self.assertTrue(report["verified"])
            self.assertEqual(2, report["branch_count"])

    def test_cli_emits_one_lf_terminated_document_and_no_raw_error(self) -> None:
        output = io.BytesIO()
        runner = FakeRunner(
            [
                acquisition.CommandResult(
                    returncode=1,
                    stdout=b"",
                    stderr=b"Authorization: Bearer test-value-not-for-output",
                )
            ]
        )
        status = acquisition.main(
            [
                "--repository",
                REPOSITORY,
                "--base-sha",
                BASE,
                "--local-sha",
                LOCAL,
                "--attempts",
                "1",
            ],
            runner=runner,
            sleeper=lambda _delay: None,
            output=output,
        )
        self.assertEqual(2, status)
        self.assertEqual(1, output.getvalue().count(b"\n"))
        document = json.loads(output.getvalue())
        self.assertEqual(acquisition.ERROR_SCHEMA_VERSION, document["schema_version"])
        self.assertNotIn(b"test-value", output.getvalue())
        self.assertNotIn(b"Bearer", output.getvalue())

    def test_cli_success_is_exact_canonical_bytes(self) -> None:
        output = io.BytesIO()
        captured = datetime(2026, 7, 15, 5, 6, 7, tzinfo=UTC)
        status = acquisition.main(
            [
                "--repository",
                REPOSITORY,
                "--base-sha",
                BASE,
                "--local-sha",
                LOCAL,
                "--attempts",
                "1",
            ],
            runner=FakeRunner(_stable_responses()),
            sleeper=lambda _delay: None,
            clock=lambda: captured,
            output=output,
        )
        self.assertEqual(0, status)
        document = json.loads(output.getvalue())
        self.assertEqual(
            acquisition._canonical_bytes(document) + b"\n", output.getvalue()
        )

    def test_oversized_diagnostics_fail_closed_without_relay(self) -> None:
        output = io.BytesIO()
        runner = FakeRunner(
            [
                acquisition.CommandResult(
                    returncode=0,
                    stdout=acquisition._canonical_bytes(_repo()),
                    stderr=b"secret" * 10,
                    stderr_exceeded=True,
                )
            ]
        )
        status = acquisition.main(
            [
                "--repository",
                REPOSITORY,
                "--base-sha",
                BASE,
                "--local-sha",
                LOCAL,
                "--attempts",
                "1",
            ],
            runner=runner,
            output=output,
        )
        self.assertEqual(2, status)
        self.assertEqual(
            "API_DIAGNOSTIC_TOO_LARGE",
            json.loads(output.getvalue())["error"]["code"],
        )
        self.assertNotIn(b"secret", output.getvalue())

    def test_request_failure_retries_only_get(self) -> None:
        failure = acquisition.CommandResult(returncode=1, stdout=b"", stderr=b"private")
        runner = FakeRunner([failure, *_stable_responses()])
        delays: list[float] = []
        snapshot = acquisition.acquire_snapshot(
            _options(attempts=2), runner=runner, sleeper=delays.append
        )
        self.assertEqual(LIVE, snapshot["live_sha"])
        self.assertEqual([0.25], delays)
        self.assertTrue(all(call[0][3] == "GET" for call in runner.calls))

    def test_moving_remote_fails_closed(self) -> None:
        second_live = "5" * 40
        runner = FakeRunner(
            [
                _json_result(_repo()),
                _json_result(_branches()),
                _json_result({"name": "main", "sha": LIVE}),
                _json_result(_compare()),
                _json_result(_repo()),
                _json_result(_branches(second_live)),
                _json_result({"name": "main", "sha": second_live}),
            ]
        )
        with self.assertRaisesRegex(acquisition.SnapshotError, "moved") as raised:
            acquisition.acquire_snapshot(_options(), runner=runner)
        self.assertEqual("REMOTE_NOT_QUIESCENT", raised.exception.code)

    def test_compare_must_prove_exact_ancestry(self) -> None:
        invalid = _compare()
        invalid["merge_base_sha"] = "6" * 40
        responses = _stable_responses()
        responses[3] = _json_result(invalid)
        with self.assertRaises(acquisition.SnapshotError) as raised:
            acquisition.acquire_snapshot(_options(), runner=FakeRunner(responses))
        self.assertEqual("REMOTE_COMPARE_MISMATCH", raised.exception.code)

    def test_private_unarchived_state_is_mandatory(self) -> None:
        repository = _repo()
        repository["archived"] = True
        with self.assertRaises(acquisition.SnapshotError) as raised:
            acquisition.acquire_snapshot(
                _options(), runner=FakeRunner([_json_result(repository)])
            )
        self.assertEqual("REMOTE_SAFETY_STATE_MISMATCH", raised.exception.code)

    def test_expected_live_and_complete_branch_guards_are_exact(self) -> None:
        expected = (("feat/kernel", FEATURE), ("main", LIVE))
        snapshot = acquisition.acquire_snapshot(
            _options(expected_live_sha=LIVE, expected_branches=expected),
            runner=FakeRunner(_stable_responses()),
        )
        self.assertEqual(LIVE, snapshot["live_sha"])
        with self.assertRaises(acquisition.SnapshotError) as raised:
            acquisition.acquire_snapshot(
                _options(expected_live_sha="7" * 40),
                runner=FakeRunner(_stable_responses()),
            )
        self.assertEqual("REMOTE_LIVE_SHA_MISMATCH", raised.exception.code)

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        for payload, code in (
            (b'{"x":1,"x":2}', "API_RESPONSE_DUPLICATE_KEY"),
            (b'{"x":NaN}', "API_RESPONSE_INVALID"),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(acquisition.SnapshotError) as raised:
                    acquisition._decode_json(payload)
                self.assertEqual(code, raised.exception.code)

    def test_oversized_stdout_fails_before_parsing(self) -> None:
        runner = FakeRunner(
            [
                acquisition.CommandResult(
                    returncode=1,
                    stdout=b"{}",
                    stdout_exceeded=True,
                )
            ]
        )
        with self.assertRaises(acquisition.SnapshotError) as raised:
            acquisition.acquire_snapshot(_options(), runner=runner)
        self.assertEqual("API_RESPONSE_TOO_LARGE", raised.exception.code)

    def test_branch_pagination_rejects_cross_page_duplicate(self) -> None:
        page = [
            {"name": f"branch-{index:03d}", "sha": FEATURE}
            for index in range(acquisition.BRANCH_PAGE_SIZE)
        ]
        runner = FakeRunner(
            [
                _json_result(_repo()),
                _json_result(page),
                _json_result([page[-1]]),
            ]
        )
        with self.assertRaises(acquisition.SnapshotError) as raised:
            acquisition.acquire_snapshot(_options(), runner=runner)
        self.assertEqual("REMOTE_BRANCH_DUPLICATE", raised.exception.code)

    def test_environment_suppresses_diagnostics_but_preserves_auth_source(self) -> None:
        environment = {
            "GH_DEBUG": "api",
            "DEBUG": "1",
            "GH_FORCE_TTY": "100",
            "GH_TOKEN": "not-emitted",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            result = acquisition._gh_environment()
        self.assertNotIn("GH_DEBUG", result)
        self.assertNotIn("DEBUG", result)
        self.assertNotIn("GH_FORCE_TTY", result)
        self.assertEqual("not-emitted", result["GH_TOKEN"])
        self.assertEqual("1", result["GH_PROMPT_DISABLED"])

    def test_invalid_arguments_fail_before_any_command(self) -> None:
        runner = FakeRunner([])
        with self.assertRaises(acquisition.SnapshotError):
            acquisition.acquire_snapshot(
                _options(repository="https://github.com/example/pheno"), runner=runner
            )
        self.assertEqual([], runner.calls)


if __name__ == "__main__":
    unittest.main()
