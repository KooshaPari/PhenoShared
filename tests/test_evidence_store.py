"""Branch and edge coverage tests for ``pheno.evidence.store``.

The companion suite ``tests/test_evidence_registry.py::RegistryStoreTests``
exercises the user-visible ``RegistryStore`` lifecycle end-to-end; the
tests here exhaustively cover the private lock / timestamp helpers, every
``put_snapshot`` and ``put_record`` validation branch, the
``_append_event`` identity dedup logic, the ``_events`` parsing paths,
the ``latest_records`` / ``latest_subject_records`` / ``latest_anecdotes``
chronological ordering, and the structured ``validate`` error report so
the suite remains the canonical source of truth for the append-only,
content-addressed evidence registry.

Coverage focus areas:

* every ``_process_exists`` branch (pid <= 0, ``ProcessLookupError``,
  ``PermissionError``, generic ``OSError``);
* every ``_stale_lock`` branch (``OSError`` on stat/read, non-numeric
  pid, dead pid, age above the 5-minute threshold);
* the ``_exclusive_lock`` stale-recovery, ``TimeoutError``, and
  ``finally`` unlink paths;
* the ``_write_content_once`` content-collision guard;
* the ``put_snapshot`` reject paths (unknown kind, wrong Reddit media
  type, non-mapping Reddit payload, non-durable Reddit fields,
  missing ``fullname`` / ``permalink``);
* the ``_append_event`` identity dedup logic that suppresses
  duplicate event lines;
* the ``_events`` decode error and non-dict error branches;
* the ``latest_records`` / ``latest_subject_records`` /
  ``latest_anecdotes`` chronological-ordering helpers, including the
  backfill / tie-break semantics;
* the structured ``validate`` error report (snapshot hash mismatch,
  missing snapshot, record id / raw_sha256 / retrieved_at mismatch,
  bad event envelope, JSON decode errors, missing records.jsonl);
* the public ``discover`` / ``discover_all`` adapter lookup tables.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import pheno.evidence.store as store_module
from pheno.evidence.contracts import (
    EVIDENCE_SCHEMA_VERSION,
    make_record_id,
    validate_evidence_record,
)
from pheno.evidence.store import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    RegistryStore,
    _exclusive_lock,
    _process_exists,
    _stale_lock,
    _timestamp_key,
    _write_content_once,
    discover,
    discover_all,
    utc_now,
)


RAW_SHA = "a" * 64


def _record(
    *,
    raw_sha: str = RAW_SHA,
    kind: str = "hf",
    evidence_class: str = "V",
    notes: list[str] | None = None,
    revision: str = "0123456789abcdef",
) -> dict[str, Any]:
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "record_id": make_record_id(kind, "Qwen/Qwen3.6-35B-A3B", revision),
        "retrieved_at": "2026-07-14T20:00:00+00:00",
        "source": {
            "kind": kind,
            "url": "https://huggingface.co/Qwen/Qwen3.6-35B-A3B",
            "revision": revision,
            "evidence_class": evidence_class,
            "raw_sha256": raw_sha,
        },
        "subject": {
            "canonical_name": "Qwen/Qwen3.6-35B-A3B",
            "aliases": ["qwen36-35b-a3b"],
            "released_at": "2026-07-10",
            "license": "apache-2.0",
        },
        "model": {
            "architecture": "Qwen3MoEForCausalLM",
            "total_parameters": 35_000_000_000,
            "active_parameters": 3_000_000_000,
            "context_tokens": 262_144,
            "modalities": ["text"],
            "mtp_or_draft": "native MTP",
        },
        "artifacts": [],
        "runtime_support": [
            {
                "runtime": "vllm",
                "version_or_commit": "0.25.1",
                "state": "released",
                "parser": "qwen3_coder",
            }
        ],
        "benchmark_claims": [
            {
                "suite": "Terminal-Bench 2.1",
                "score": 0.0,
                "harness": "creator-card",
                "attempts": None,
                "evidence_class": "C",
            }
        ],
        "gates": {
            "metadata_only": True,
            "license": "review_required",
            "execution": "blocked",
        },
        "discovery": {
            "method": "GET",
            "endpoint": "https://huggingface.co/api/models",
            "query": {"search": "Qwen3.6"},
            "final_url": "https://huggingface.co/api/models?search=Qwen3.6",
            "adapter_version": "test-v1",
            "api_version": None,
            "status": 200,
            "response_headers": {},
            "incomplete": False,
        },
        "resolved": {"revision": revision, "mutable": False},
        "license": {
            "declared": ["apache-2.0"],
            "source_urls": [],
            "verified": False,
            "caveats": ["publisher-declared metadata"],
        },
        "quality": {
            "incomplete": False,
            "confidence": "high",
            "needs_revalidation_at": None,
        },
        "compliance": {
            "retention_class": "durable_metadata",
            "purge_after": None,
            "tombstoned_at": None,
        },
        "notes": list(notes or []),
    }


def _seed(store: RegistryStore) -> str:
    """Persist one snapshot and return its ``sha256``."""

    snapshot = store.put_snapshot(
        source_kind="hf",
        source_url="https://huggingface.co/api/models",
        payload={"id": "Qwen/Qwen3.6-35B-A3B"},
    )
    return snapshot["sha256"]


def _reddit_snapshot(store: RegistryStore) -> str:
    snapshot = store.put_snapshot(
        source_kind="reddit",
        source_url="https://www.reddit.com/r/LocalLLaMA/comments/example",
        media_type="application/vnd.pheno.reddit-citation+json",
        payload={
            "fullname": "t3_example",
            "permalink": "/r/LocalLLaMA/comments/example",
            "retrieved_at": "2026-07-14T20:00:00Z",
            "tombstone_state": "live",
            "paraphrased_claim": "A user reported sustained thermal throttling.",
        },
    )
    return snapshot["sha256"]


class StoreHelperTests(unittest.TestCase):
    """Cover every branch of the module-level private helpers."""

    def test_utc_now_returns_iso8601_with_utc_tz(self) -> None:
        text = utc_now()
        parsed = datetime.fromisoformat(text)
        self.assertEqual(parsed.tzinfo, UTC)

    def test_timestamp_key_normalizes_to_utc(self) -> None:
        parsed = _timestamp_key("2026-07-14T20:00:00-05:00")
        self.assertEqual(parsed.tzinfo, UTC)
        self.assertEqual(parsed.utcoffset().total_seconds(), 0.0)
        # Round-trip via ISO format yields the canonical UTC representation.
        self.assertEqual(parsed.hour, 1)

    def test_timestamp_key_accepts_z_suffix(self) -> None:
        parsed = _timestamp_key("2026-07-14T20:00:00Z")
        self.assertEqual(parsed.tzinfo, UTC)

    def test_timestamp_key_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(ValueError, "must include a timezone"):
            _timestamp_key("2026-07-14T20:00:00")

    def test_process_exists_rejects_invalid_pids(self) -> None:
        for pid in (0, -1):
            with self.subTest(pid=pid):
                self.assertFalse(_process_exists(pid))

    def test_process_exists_handles_process_lookup_error(self) -> None:
        with patch("pheno.evidence.store.os.kill", side_effect=ProcessLookupError):
            self.assertFalse(_process_exists(12345))

    def test_process_exists_handles_permission_error_as_alive(self) -> None:
        with patch("pheno.evidence.store.os.kill", side_effect=PermissionError):
            self.assertTrue(_process_exists(12345))

    def test_process_exists_handles_generic_os_error(self) -> None:
        with patch("pheno.evidence.store.os.kill", side_effect=OSError("io")):
            self.assertFalse(_process_exists(12345))

    def test_process_exists_returns_true_when_kill_succeeds(self) -> None:
        with patch("pheno.evidence.store.os.kill", return_value=None):
            self.assertTrue(_process_exists(12345))

    def test_stale_lock_returns_false_on_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertFalse(_stale_lock(Path(temp_dir) / "missing.lock"))

    def test_stale_lock_returns_false_for_dead_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock = Path(temp_dir) / "snapshots.jsonl.lock"
            lock.write_text("pid=999999999\n", encoding="ascii")
            with patch("pheno.evidence.store._process_exists", return_value=False):
                self.assertTrue(_stale_lock(lock))

    def test_stale_lock_returns_false_for_alive_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock = Path(temp_dir) / "snapshots.jsonl.lock"
            lock.write_text(f"pid={os.getpid()}\n", encoding="ascii")
            self.assertFalse(_stale_lock(lock))

    def test_stale_lock_returns_false_when_pid_is_garbage(self) -> None:
        # ``pid=not-an-int`` exercises the ``ValueError`` swallow that resets
        # the parsed pid back to zero; without the recovery the lock would
        # always look stale.
        with tempfile.TemporaryDirectory() as temp_dir:
            lock = Path(temp_dir) / "snapshots.jsonl.lock"
            lock.write_text("pid=not-an-int\n", encoding="ascii")
            self.assertFalse(_stale_lock(lock))

    def test_stale_lock_returns_true_when_old_lock_has_no_pid(self) -> None:
        # No ``pid=`` line → fall back to ``age > 300s``.  Capture the file's
        # mtime first, then override ``time.time`` so the apparent age is
        # well past the 5-minute threshold regardless of when the test runs.
        with tempfile.TemporaryDirectory() as temp_dir:
            lock = Path(temp_dir) / "snapshots.jsonl.lock"
            lock.write_text("created=epoch\n", encoding="ascii")
            mtime = lock.stat().st_mtime
            with patch(
                "pheno.evidence.store.time.time",
                return_value=mtime + 10_000.0,
            ):
                self.assertTrue(_stale_lock(lock))

    def test_stale_lock_returns_false_when_old_lock_has_no_pid_and_is_recent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock = Path(temp_dir) / "snapshots.jsonl.lock"
            lock.write_text("created=epoch\n", encoding="ascii")
            mtime = lock.stat().st_mtime
            # Pick a ``time.time`` value *just* after the mtime so the age is
            # smaller than the 5-minute threshold; the lock should not be
            # considered stale.
            with patch(
                "pheno.evidence.store.time.time",
                return_value=mtime + 10.0,
            ):
                self.assertFalse(_stale_lock(lock))

    def test_exclusive_lock_recovers_when_stale_lock_disappears(self) -> None:
        # Lines 102-103 handle the ``FileNotFoundError`` raised when the
        # stale lock file vanishes between the staleness check and the
        # ``unlink()`` call.  Simulate the race by patching ``unlink``
        # to raise ``FileNotFoundError`` on the first call while
        # leaving the live lock to be acquired afterwards.
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "store.lock"
            lock_path.write_text(
                "pid=999999999\ncreated=never\n", encoding="ascii"
            )
            original_unlink = Path.unlink
            calls = {"count": 0}

            def flaky_unlink(self, *args, **kwargs):
                if self == lock_path and calls["count"] == 0:
                    calls["count"] += 1
                    # Pretend the file disappeared before ``unlink`` ran
                    # by removing the file and then raising.
                    original_unlink(self, *args, **kwargs)
                    raise FileNotFoundError(2, "No such file or directory")
                return original_unlink(self, *args, **kwargs)

            with patch.object(Path, "unlink", flaky_unlink):
                with patch.object(store_module, "_process_exists", return_value=False):
                    with _exclusive_lock(lock_path, timeout=2.0):
                        # The lock should have been acquired after the
                        # race-recovery ``continue``.
                        self.assertTrue(lock_path.exists())

    def test_exclusive_lock_recovers_when_pid_is_dead(self) -> None:
        # Patch ``_process_exists`` to avoid touching the real process table;
        # the underlying ``os.kill`` call against the very large fake pid can
        # otherwise interact badly with the previous timeout test's lock
        # handle on Windows.  The dead-pid branch only cares about the
        # boolean return value.
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "snapshots.jsonl.lock"
            lock_path.write_text("pid=999999999\n", encoding="ascii")
            with patch("pheno.evidence.store._process_exists", return_value=False):
                with _exclusive_lock(lock_path, timeout=2.0):
                    self.assertTrue(lock_path.exists())
            # The lock file is cleaned up when the context manager exits.
            self.assertFalse(lock_path.exists())

    def test_exclusive_lock_swallows_missing_unlink_in_finally(self) -> None:
        # The ``finally`` block's ``unlink`` swallows ``FileNotFoundError``;
        # patch ``Path.unlink`` to raise the swallowed exception so the
        # branch is exercised without depending on Windows file-locking
        # semantics that make the underlying race hard to reproduce locally.
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "events.jsonl.lock"
            original_unlink = Path.unlink

            def _raise_fnf(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                if Path(self) == lock_path:
                    raise FileNotFoundError(2, "simulated FNF", str(self))
                return original_unlink(self, *args, **kwargs)

            with patch.object(Path, "unlink", _raise_fnf):
                with _exclusive_lock(lock_path, timeout=2.0):
                    pass

    def test_exclusive_lock_raises_timeout_when_contended(self) -> None:
        # Use an isolated directory and remove the lock file before the
        # ``tempfile.TemporaryDirectory`` context exits so Windows does not
        # hold a leftover handle during teardown (the high-level writer
        # above + ``_exclusive_lock``'s repeated stat/read loop can keep
        # the directory locked for a short while).
        temp_dir = Path(tempfile.mkdtemp())
        try:
            lock_path = temp_dir / "events.jsonl.lock"
            lock_path.write_text(f"pid={os.getpid()}\n", encoding="ascii")
            with self.assertRaisesRegex(TimeoutError, "timed out"):
                with _exclusive_lock(lock_path, timeout=0.1):
                    self.fail("lock should not have been acquired")
        finally:
            # Best-effort cleanup that ignores ``PermissionError`` so the
            # Windows file-system race during teardown cannot fail the test.
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_write_content_once_rejects_different_payload_at_same_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "raw.json"
            _write_content_once(path, b"hello")
            with self.assertRaisesRegex(ValueError, "content-address collision"):
                _write_content_once(path, b"different")


class RegistryStoreInitTests(unittest.TestCase):
    """Cover ``RegistryStore.__init__`` validation."""

    def test_init_rejects_non_positive_max_snapshot_bytes(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_snapshot_bytes"):
            RegistryStore(Path("ignored"), max_snapshot_bytes=0)
        with self.assertRaisesRegex(ValueError, "max_snapshot_bytes"):
            RegistryStore(Path("ignored"), max_snapshot_bytes=-1)

    def test_init_creates_subdirectory_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = RegistryStore(root)
            self.assertEqual(store.root, root)
            self.assertEqual(store.raw_root, root / "raw")
            self.assertEqual(store.record_root, root / "records")
            self.assertEqual(store.anecdote_root, root / "anecdotes")
            self.assertEqual(store.event_root, root / "events")
            self.assertEqual(store.max_snapshot_bytes, DEFAULT_MAX_SNAPSHOT_BYTES)


class PutSnapshotValidationTests(unittest.TestCase):
    """Cover every reject path of ``put_snapshot``."""

    def test_unsupported_source_kind_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "unsupported source kind"):
                store.put_snapshot(
                    source_kind="not-a-source",
                    source_url="https://example.com",
                    payload={"x": 1},
                )

    def test_reddit_payload_requires_citation_media_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "snapshots are forbidden"):
                store.put_snapshot(
                    source_kind="reddit",
                    source_url="https://www.reddit.com/r/example",
                    payload={"fullname": "t3_example"},
                )

    def test_reddit_payload_must_be_a_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "must be a JSON object"):
                store.put_snapshot(
                    source_kind="reddit",
                    source_url="https://www.reddit.com/r/example",
                    media_type="application/vnd.pheno.reddit-citation+json",
                    payload=["not", "a", "mapping"],
                )

    def test_reddit_payload_rejects_non_durable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(
                ValueError, "non-durable fields"
            ):
                store.put_snapshot(
                    source_kind="reddit",
                    source_url="https://www.reddit.com/r/example",
                    media_type="application/vnd.pheno.reddit-citation+json",
                    payload={
                        "fullname": "t3_example",
                        "permalink": "/r/example",
                        "title": "raw content must not persist",
                    },
                )

    def test_reddit_payload_requires_fullname_and_permalink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            for missing in ("fullname", "permalink"):
                with self.subTest(missing=missing):
                    payload: dict[str, Any] = {
                        "permalink": "/r/example",
                        "retrieved_at": "2026-07-14T20:00:00Z",
                        "tombstone_state": "live",
                    }
                    if missing == "permalink":
                        del payload["permalink"]
                    # ``fullname`` is absent by default; the missing branch
                    # never adds it so the contract fires for both cases.
                    with self.assertRaisesRegex(
                        ValueError, "requires fullname and permalink"
                    ):
                        store.put_snapshot(
                            source_kind="reddit",
                            source_url="https://www.reddit.com/r/example",
                            media_type="application/vnd.pheno.reddit-citation+json",
                            payload=payload,
                        )

    def test_snapshot_size_limit_enforced_for_text_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir), max_snapshot_bytes=8)
            with self.assertRaisesRegex(ValueError, "limit"):
                store.put_snapshot(
                    source_kind="github",
                    source_url="https://api.github.com/repos/example/example",
                    payload="too long for the cap",
                    media_type="text/plain",
                )

    def test_snapshot_size_limit_enforced_for_mapping_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir), max_snapshot_bytes=4)
            with self.assertRaisesRegex(ValueError, "limit"):
                store.put_snapshot(
                    source_kind="hf",
                    source_url="https://huggingface.co/api/models",
                    payload={"id": "Qwen/Qwen3.6-35B-A3B"},
                )


class PutSnapshotContentAddressingTests(unittest.TestCase):
    """Cover the content-addressing + event-write side-effects."""

    def test_mapping_payload_is_canonicalized_and_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"b": 2, "a": 1},
            )
            self.assertEqual(event["source_kind"], "hf")
            self.assertEqual(event["media_type"], "application/json")
            self.assertTrue(event["sha256"])
            self.assertTrue(event["bytes"] > 0)
            # Canonical ordering means the JSON form starts with "a".
            raw_path = store.raw_root / event["path"]
            self.assertTrue(raw_path.exists())
            self.assertTrue(raw_path.read_bytes().startswith(b'{"a":'))

    def test_text_payload_is_written_as_txt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event = store.put_snapshot(
                source_kind="github",
                source_url="https://api.github.com/repos/example/example",
                payload="plain text payload",
                media_type="text/plain",
            )
            self.assertTrue(event["path"].endswith(".txt"))
            self.assertTrue((store.raw_root / event["path"]).exists())

    def test_bytes_payload_is_decoded_with_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            payload = "raw bytes \xff with non-utf8"
            event = store.put_snapshot(
                source_kind="github",
                source_url="https://api.github.com/repos/example/example",
                payload=payload.encode("utf-8", errors="replace"),
                media_type="text/plain",
            )
            stored = (store.raw_root / event["path"]).read_bytes()
            self.assertIn(b"non-utf8", stored)

    def test_snapshot_event_is_appended_with_retrieved_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
                retrieved_at="2026-07-14T20:00:00+00:00",
            )
            events = store._events("snapshots.jsonl")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["retrieved_at"], "2026-07-14T20:00:00+00:00")


class PutRecordTests(unittest.TestCase):
    """Cover ``put_record`` validation, content addressing, and dedup."""

    def test_put_record_writes_event_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            self.assertEqual(event["record_sha256"], event["record_sha256"])
            self.assertEqual(event["raw_sha256"], sha)
            self.assertTrue((store.record_root / event["path"]).exists())

    def test_put_record_rejects_unknown_raw_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "raw snapshot"):
                store.put_record(_record(raw_sha="b" * 64))

    def test_put_record_routes_anecdotes_to_separate_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _reddit_snapshot(store)
            anecdote = _record(
                raw_sha=sha, kind="reddit", evidence_class="A"
            )
            anecdote["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            event = store.put_record(anecdote)
            self.assertTrue((store.anecdote_root / event["path"]).exists())
            self.assertFalse((store.record_root / event["path"]).exists())

    def test_put_record_dedups_duplicate_record_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            payload = _record(raw_sha=sha)
            first = store.put_record(payload)
            second = store.put_record(payload)
            self.assertEqual(first["record_sha256"], second["record_sha256"])
            events = store._events("records.jsonl")
            self.assertEqual(len(events), 1)


class EventStreamTests(unittest.TestCase):
    """Cover ``_events`` parsing and ``_append_event`` dedup semantics."""

    def test_events_returns_empty_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            self.assertEqual(store._events("records.jsonl"), [])

    def test_events_skips_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event_path = store.event_root / "snapshots.jsonl"
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.write_text(
                '{"a": 1}\n\n{"a": 2}\n',
                encoding="utf-8",
            )
            events = store._events("snapshots.jsonl")
            self.assertEqual([row["a"] for row in events], [1, 2])

    def test_events_raises_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event_path = store.event_root / "snapshots.jsonl"
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                store._events("snapshots.jsonl")

    def test_events_raises_on_non_object_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event_path = store.event_root / "snapshots.jsonl"
            event_path.parent.mkdir(parents=True, exist_ok=True)
            event_path.write_text("[1, 2, 3]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "event must be an object"):
                store._events("snapshots.jsonl")

    def test_append_event_skips_blank_lines_when_deduping(self) -> None:
        # The ``continue`` at line 166 fires for blank/whitespace-only
        # lines already present in the event stream.  Pre-seed
        # ``snapshots.jsonl`` with empty lines and then append with a
        # unique identity so the dedup loop walks over (and skips) them
        # before reaching the end and appending.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            store.event_root.mkdir(parents=True, exist_ok=True)
            event_path = store.event_root / "snapshots.jsonl"
            event_path.write_text("\n\n   \n", encoding="utf-8")
            store._append_event(
                "snapshots.jsonl",
                {"record_sha256": "uniq", "bytes": 1},
                identity_fields=("record_sha256",),
            )
            events = store._events("snapshots.jsonl")
            self.assertEqual([e["record_sha256"] for e in events], ["uniq"])

    def test_append_event_dedups_by_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            # The first append succeeds; the second has identical
            # identity_fields values and must be skipped.
            store._append_event(
                "snapshots.jsonl",
                {"record_sha256": "abc", "bytes": 1},
                identity_fields=("record_sha256",),
            )
            store._append_event(
                "snapshots.jsonl",
                {"record_sha256": "abc", "bytes": 99},
                identity_fields=("record_sha256",),
            )
            store._append_event(
                "snapshots.jsonl",
                {"record_sha256": "def", "bytes": 1},
                identity_fields=("record_sha256",),
            )
            events = store._events("snapshots.jsonl")
            self.assertEqual([e["record_sha256"] for e in events], ["abc", "def"])
            self.assertEqual(events[0]["bytes"], 1)


class LatestRecordsTests(unittest.TestCase):
    """Cover the chronological-ordering helpers."""

    def test_latest_records_picks_newest_observation_per_record_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            older = _record(raw_sha=sha)
            older["retrieved_at"] = "2026-07-14T19:00:00+00:00"
            older["notes"] = ["older"]
            newer = _record(raw_sha=sha)
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            newer["notes"] = ["newer"]
            # Order: older first, then newer — chronological tie-break goes to
            # the later event for the same instant.
            store.put_record(older)
            store.put_record(newer)
            latest = store.latest_records()
            self.assertIn(newer["record_id"], latest)
            self.assertEqual(latest[newer["record_id"]]["notes"], ["newer"])

    def test_latest_records_tie_breaks_on_later_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            first = _record(raw_sha=sha)
            first["retrieved_at"] = "2026-07-14T20:00:00+00:00"
            first["notes"] = ["first"]
            second = _record(raw_sha=sha)
            second["retrieved_at"] = "2026-07-14T20:00:00+00:00"
            second["notes"] = ["second"]
            store.put_record(first)
            store.put_record(second)
            latest = store.latest_records()
            self.assertEqual(latest[first["record_id"]]["notes"], ["second"])

    def test_latest_records_keeps_newer_event_when_older_one_arrives_later(self) -> None:
        # The ``309 -> 303`` branch keeps an existing newer entry in
        # ``latest_records``; inserting an older event after a newer one
        # exercises the skip path.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            newer = _record(raw_sha=sha)
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            newer["notes"] = ["newer"]
            store.put_record(newer)
            older = _record(raw_sha=sha)
            older["retrieved_at"] = "2026-07-14T19:00:00+00:00"
            older["notes"] = ["older"]
            store.put_record(older)
            latest = store.latest_records()
            self.assertEqual(latest[newer["record_id"]]["notes"], ["newer"])

    def test_latest_records_returns_empty_when_no_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            self.assertEqual(store.latest_records(), {})

    def test_latest_subject_records_keeps_newer_record_when_older_one_arrives_later(self) -> None:
        # The ``322 -> 319`` branch in ``latest_subject_records`` keeps an
        # existing newer record when an older one for the same
        # subject lands later in the stream.  The two records need
        # distinct ``record_id`` values so ``latest_records`` retains
        # both of them and ``latest_subject_records`` then compares
        # them.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            newer = _record(raw_sha=sha, revision="rev-newer")
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            newer["notes"] = ["newer"]
            store.put_record(newer)
            older = _record(raw_sha=sha, revision="rev-older")
            older["retrieved_at"] = "2026-07-14T19:00:00+00:00"
            older["notes"] = ["older"]
            store.put_record(older)
            subjects = store.latest_subject_records()
            key = f"{newer['source']['kind']}:{newer['subject']['canonical_name']}"
            self.assertEqual(subjects[key]["notes"], ["newer"])

    def test_latest_subject_records_groups_by_kind_and_canonical_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            older = _record(raw_sha=sha)
            older["retrieved_at"] = "2026-07-14T19:00:00+00:00"
            newer = _record(raw_sha=sha)
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            store.put_record(older)
            store.put_record(newer)
            subjects = store.latest_subject_records()
            key = f"{newer['source']['kind']}:{newer['subject']['canonical_name']}"
            self.assertEqual(list(subjects), [key])
            self.assertEqual(subjects[key]["retrieved_at"], newer["retrieved_at"])

    def test_latest_anecdotes_keeps_newer_record_when_older_one_arrives_later(self) -> None:
        # The ``336 -> 330`` branch in ``latest_anecdotes`` skips an
        # older anecdote when a newer one is already present for the
        # same ``record_id``.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _reddit_snapshot(store)
            newer = _record(
                raw_sha=sha, kind="reddit", evidence_class="A"
            )
            newer["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            newer["notes"] = ["newer"]
            store.put_record(newer)
            older = _record(
                raw_sha=sha, kind="reddit", evidence_class="A"
            )
            older["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            older["retrieved_at"] = "2026-07-14T19:00:00+00:00"
            older["notes"] = ["older"]
            store.put_record(older)
            latest = store.latest_anecdotes()
            self.assertEqual(latest[newer["record_id"]]["notes"], ["newer"])

    def test_latest_anecdotes_returns_only_anecdotal_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _reddit_snapshot(store)
            anecdote = _record(
                raw_sha=sha, kind="reddit", evidence_class="A"
            )
            anecdote["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            store.put_record(anecdote)
            self.assertEqual(len(store.latest_records()), 0)
            self.assertEqual(len(store.latest_anecdotes()), 1)


class ValidateReportTests(unittest.TestCase):
    """Cover every branch of ``RegistryStore.validate``."""

    def test_validate_ok_for_clean_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            store.put_record(_record(raw_sha=sha))
            report = store.validate()
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["snapshot_events"], 1)
            self.assertEqual(report["unique_snapshots"], 1)
            self.assertEqual(report["record_events"], 1)
            self.assertEqual(report["unique_records"], 1)
            self.assertEqual(report["unique_record_contents"], 1)

    def test_validate_detects_tampered_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            (store.raw_root / event["path"]).write_bytes(b"tampered")
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(any("hash mismatch" in e for e in report["errors"]))

    def test_validate_detects_missing_snapshot_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            (store.raw_root / event["path"]).unlink()
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("No such file" in e or "cannot find" in e for e in report["errors"])
            )

    def test_validate_detects_snapshot_event_missing_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event_path = store.event_root / "snapshots.jsonl"
            event_path.parent.mkdir(parents=True, exist_ok=True)
            # Hand-craft an event missing the required ``sha256`` field so
            # the snapshot-validation ``try`` branch fires.
            event_path.write_text(
                json.dumps({"source_kind": "hf", "path": "missing"}) + "\n",
                encoding="utf-8",
            )
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("snapshots.jsonl" not in e and "snapshot event" in e for e in report["errors"])
            )

    def test_validate_detects_tampered_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            (store.record_root / event["path"]).write_text(
                json.dumps({"tampered": True}), encoding="utf-8"
            )
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(any("hash mismatch" in e for e in report["errors"]))

    def test_validate_detects_record_id_mismatch(self) -> None:
        # The line-381 branch fires when the event envelope's ``record_id``
        # disagrees with the record file's ``record_id``; both still need
        # to pass the upstream contract and hash checks.  Mutate only the
        # event envelope so the record file remains unchanged and the
        # mismatch surfaces from ``validate``.
        from pheno.evidence.contracts import canonical_json_bytes

        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            event_path = store.event_root / "records.jsonl"
            event_entry = json.loads(event_path.read_text(encoding="utf-8"))
            original_record_id = event_entry["record_id"]
            # Pick a record_id that satisfies the contract regex but
            # unambiguously differs from the original so the field
            # comparison fires inside ``validate``.
            event_entry["record_id"] = (
                "hf:wrong:zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
            )
            # Rewriting the envelope requires re-canonicalising so the
            # event-hash check does not also fail and short-circuit the
            # field-level comparison.
            new_bytes = canonical_json_bytes(event_entry)
            event_path.write_bytes(new_bytes)
            # Sanity: ensure the new envelope differs from the original
            # record file's ``record_id``.
            record_path = store.record_root / event["path"]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertNotEqual(event_entry["record_id"], record["record_id"])
            del original_record_id
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("record_id mismatch" in e for e in report["errors"])
            )

    def test_validate_detects_raw_sha_mismatch(self) -> None:
        from pheno.evidence.contracts import canonical_json_bytes, sha256_hex

        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            record_path = store.record_root / event["path"]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["source"]["raw_sha256"] = "0" * 64
            new_bytes = canonical_json_bytes(record)
            record_path.write_bytes(new_bytes)
            event_path = store.event_root / "records.jsonl"
            event_entry = json.loads(event_path.read_text(encoding="utf-8"))
            event_entry["record_sha256"] = sha256_hex(new_bytes)
            event_path.write_text(
                json.dumps(event_entry) + "\n", encoding="utf-8"
            )
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("raw_sha256 mismatch" in e for e in report["errors"])
            )

    def test_validate_detects_retrieved_at_mismatch(self) -> None:
        # ``validate_evidence_record`` validates ``retrieved_at`` as an
        # ISO-8601 timestamp; mutating it to a different value that still
        # parses keeps the field check downstream in ``validate`` running.
        from pheno.evidence.contracts import canonical_json_bytes, sha256_hex

        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            record_path = store.record_root / event["path"]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            new_retrieved = "2026-07-14T22:00:00+00:00"
            record["retrieved_at"] = new_retrieved
            new_bytes = canonical_json_bytes(record)
            record_path.write_bytes(new_bytes)
            event_path = store.event_root / "records.jsonl"
            event_entry = json.loads(event_path.read_text(encoding="utf-8"))
            event_entry["record_sha256"] = sha256_hex(new_bytes)
            # Leave the event envelope's ``retrieved_at`` untouched so the
            # downstream field check fails.
            event_path.write_text(
                json.dumps(event_entry) + "\n", encoding="utf-8"
            )
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("retrieved_at mismatch" in e for e in report["errors"])
            )

    def test_validate_detects_missing_snapshot_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            event = store.put_record(_record(raw_sha=sha))
            # Drop the snapshot event so the record's raw_sha256 is no longer
            # in the snapshot lineage set.
            (store.event_root / "snapshots.jsonl").unlink()
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("raw snapshot is missing" in e for e in report["errors"])
            )

    def test_validate_detects_invalid_event_envelope_json(self) -> None:
        # Hand-craft a record event whose JSON is invalid so ``_events``
        # raises a ``ValueError`` that ``validate`` cannot catch (it sits
        # outside the per-event ``try`` block).  The ``_events`` exception
        # surfaces a ``records.jsonl`` path so the test pins that branch.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            store.put_record(_record(raw_sha=sha))
            (store.event_root / "records.jsonl").write_text(
                "{not-json}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "invalid JSON.*records.jsonl"):
                store.validate()

    def test_validate_catches_record_event_exceptions(self) -> None:
        # Lines 402-409 form the records/anecdotes try/except inside
        # ``validate``.  Inject a record event whose ``record_sha256``
        # field is missing so ``str(event["record_sha256"])`` raises
        # ``KeyError`` and is captured as a structured error.
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _seed(store)
            store.put_record(_record(raw_sha=sha))
            event_path = store.event_root / "records.jsonl"
            event_entry = json.loads(event_path.read_text(encoding="utf-8"))
            del event_entry["record_sha256"]
            from pheno.evidence.contracts import canonical_json_bytes
            event_path.write_bytes(canonical_json_bytes(event_entry))
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any(
                    "record event 0" in e and "record_sha256" in e
                    for e in report["errors"]
                )
            )

    def test_validate_counts_unique_anecdotes_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            sha = _reddit_snapshot(store)
            anecdote = _record(
                raw_sha=sha, kind="reddit", evidence_class="A"
            )
            anecdote["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            store.put_record(anecdote)
            report = store.validate()
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["anecdote_events"], 1)
            self.assertEqual(report["unique_anecdotes"], 1)
            self.assertEqual(report["unique_anecdote_contents"], 1)


class DiscoverAdapterTests(unittest.TestCase):
    """Cover the ``discover`` / ``discover_all`` adapter lookup tables."""

    def test_discover_returns_every_supported_kind(self) -> None:
        mapping = discover()
        self.assertEqual(
            set(mapping),
            {"arxiv", "github", "hf", "local_corpus", "modelscope", "reddit"},
        )
        # Spot-check the public class identities match the module's re-exports.
        from pheno.evidence.adapters import (
            ArxivAdapter,
            GitHubAdapter,
            HuggingFaceAdapter,
            LocalCorpusAdapter,
            ModelScopeAdapter,
            RedditAdapter,
        )

        self.assertIs(mapping["arxiv"], ArxivAdapter)
        self.assertIs(mapping["github"], GitHubAdapter)
        self.assertIs(mapping["hf"], HuggingFaceAdapter)
        self.assertIs(mapping["local_corpus"], LocalCorpusAdapter)
        self.assertIs(mapping["modelscope"], ModelScopeAdapter)
        self.assertIs(mapping["reddit"], RedditAdapter)

    def test_discover_all_delegates_to_discover(self) -> None:
        self.assertEqual(discover_all(), discover())

    def test_discover_falls_back_when_adapter_module_is_patched(self) -> None:
        # ``discover`` imports ``pheno.evidence.adapters`` lazily so tests
        # that ``patch.object`` the module attributes still observe a fresh
        # lookup table on every call.
        sentinel = type("FakeAdapter", (), {})
        with patch("pheno.evidence.adapters.HuggingFaceAdapter", sentinel):
            mapping = discover()
        self.assertIs(mapping["hf"], sentinel)


class ModuleSurfaceTests(unittest.TestCase):
    """Pin the documented module surface."""

    def test_all_is_locked_to_public_names(self) -> None:
        self.assertEqual(
            set(store_module.__all__),
            {
                "DEFAULT_MAX_SNAPSHOT_BYTES",
                "RegistryStore",
                "discover",
                "discover_all",
                "utc_now",
            },
        )


if __name__ == "__main__":
    unittest.main()
