"""Append-only, content-addressed persistence for evidence metadata."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import (
    SOURCE_KINDS,
    canonical_json_bytes,
    sha256_hex,
    validate_evidence_record,
)
from .redaction import redact_object, redact_text

DEFAULT_MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024

_REDDIT_CITATION_MEDIA_TYPE = "application/vnd.pheno.reddit-citation+json"
_REDDIT_DURABLE_FIELDS = {
    "fullname",
    "permalink",
    "retrieved_at",
    "observed_at",
    "subreddit",
    "paraphrased_claim",
    "tombstone_state",
    "needs_revalidation_at",
}


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _timestamp_key(value: Any) -> datetime:
    """Normalize a contract-validated ISO timestamp for chronological ordering."""

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _stale_lock(path: Path) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
        text = path.read_text(encoding="ascii", errors="ignore")
    except OSError:
        return False
    pid = 0
    for line in text.splitlines():
        if line.startswith("pid="):
            try:
                pid = int(line.split("=", 1)[1])
            except ValueError:
                pid = 0
    if pid:
        return not _process_exists(pid)
    return age > 300.0


@contextmanager
def _exclusive_lock(path: Path, timeout: float = 10.0) -> Iterator[None]:
    """Use an O_EXCL lock file so appends are safe on Windows and POSIX."""

    deadline = time.monotonic() + timeout
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(
                descriptor,
                f"pid={os.getpid()}\ncreated={utc_now()}\n".encode("ascii"),
            )
        except FileExistsError:
            if _stale_lock(path):
                try:
                    path.unlink()
                    continue
                except FileNotFoundError:
                    continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for registry lock: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _write_content_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError(f"content-address collision or corruption: {path}")


class RegistryStore:
    """Persist sanitized raw snapshots and normalized records without mutation."""

    def __init__(
        self, root: Path, *, max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES
    ):
        """Initialize the registry store.

        Args:
            root: Root directory for raw snapshots, records and events.
            max_snapshot_bytes: Maximum allowed snapshot payload size.

        """
        if max_snapshot_bytes < 1:
            raise ValueError("max_snapshot_bytes must be positive")
        self.root = Path(root)
        self.max_snapshot_bytes = int(max_snapshot_bytes)
        self.raw_root = self.root / "raw"
        self.record_root = self.root / "records"
        self.anecdote_root = self.root / "anecdotes"
        self.event_root = self.root / "events"

    def _append_event(
        self,
        name: str,
        event: Mapping[str, Any],
        *,
        identity_fields: tuple[str, ...] = (),
    ) -> None:
        path = self.event_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = canonical_json_bytes(dict(event))
        with _exclusive_lock(path.with_suffix(path.suffix + ".lock")):
            if identity_fields and path.exists():
                identity = tuple(event.get(field) for field in identity_fields)
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    existing = json.loads(line)
                    if (
                        tuple(existing.get(field) for field in identity_fields)
                        == identity
                    ):
                        return
            with path.open("ab") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())

    def put_snapshot(
        self,
        *,
        source_kind: str,
        source_url: str,
        payload: bytes | str | Mapping[str, Any] | list[Any],
        media_type: str = "application/json",
        retrieved_at: str | None = None,
    ) -> dict[str, Any]:
        """Sanitize and persist one bounded API/document metadata response."""

        kind = source_kind.strip().lower()
        if kind not in SOURCE_KINDS:
            raise ValueError(f"unsupported source kind: {source_kind!r}")
        if kind == "reddit":
            if media_type != _REDDIT_CITATION_MEDIA_TYPE:
                raise ValueError(
                    "durable Reddit snapshots are forbidden; persist only deletion-aware "
                    f"citation metadata as {_REDDIT_CITATION_MEDIA_TYPE}"
                )
            if not isinstance(payload, Mapping):
                raise ValueError("Reddit citation metadata must be a JSON object")
            unexpected = sorted(set(payload) - _REDDIT_DURABLE_FIELDS)
            if unexpected:
                raise ValueError(
                    "Reddit citation contains non-durable fields: "
                    + ", ".join(unexpected)
                )
            if not payload.get("fullname") or not payload.get("permalink"):
                raise ValueError("Reddit citation requires fullname and permalink")
        if isinstance(payload, (Mapping, list)):
            sanitized: Any = redact_object(payload)
            encoded = canonical_json_bytes(sanitized)
            extension = "json"
        else:
            raw = (
                payload.decode("utf-8", errors="replace")
                if isinstance(payload, bytes)
                else payload
            )
            encoded = redact_text(raw).encode("utf-8")
            extension = "txt"
        if len(encoded) > self.max_snapshot_bytes:
            raise ValueError(
                f"metadata snapshot is {len(encoded)} bytes; limit is {self.max_snapshot_bytes}"
            )
        digest = sha256_hex(encoded)
        relative = Path(kind) / digest[:2] / f"{digest}.{extension}"
        _write_content_once(self.raw_root / relative, encoded)
        event = {
            "schema_version": "pheno.evidence.snapshot.v1",
            "source_kind": kind,
            "source_url": redact_text(source_url),
            "retrieved_at": retrieved_at or utc_now(),
            "media_type": media_type,
            "bytes": len(encoded),
            "sha256": digest,
            "path": relative.as_posix(),
        }
        self._append_event(
            "snapshots.jsonl",
            event,
            identity_fields=("source_kind", "source_url", "retrieved_at", "sha256"),
        )
        return event

    def put_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Validate, content-address, and append a pointer to one record."""

        validated = validate_evidence_record(record)
        raw_digest = str(validated["source"]["raw_sha256"])
        snapshot_hashes = {
            str(event.get("sha256")) for event in self._events("snapshots.jsonl")
        }
        if raw_digest not in snapshot_hashes:
            raise ValueError(
                "record references a raw snapshot that is not in this store"
            )
        encoded = canonical_json_bytes(validated)
        digest = sha256_hex(encoded)
        relative = Path(digest[:2]) / f"{digest}.json"
        anecdotal = validated["source"]["evidence_class"] == "A"
        target_root = self.anecdote_root if anecdotal else self.record_root
        event_name = "anecdotes.jsonl" if anecdotal else "records.jsonl"
        _write_content_once(target_root / relative, encoded)
        event = {
            "schema_version": "pheno.evidence.record-event.v1",
            "record_id": validated["record_id"],
            "record_sha256": digest,
            "raw_sha256": validated["source"]["raw_sha256"],
            "retrieved_at": validated["retrieved_at"],
            "path": relative.as_posix(),
        }
        self._append_event(event_name, event, identity_fields=("record_sha256",))
        return event

    def _events(self, name: str) -> list[dict[str, Any]]:
        path = self.event_root / name
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON in {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"event must be an object in {path}:{line_number}")
            rows.append(value)
        return rows

    def latest_records(self) -> dict[str, dict[str, Any]]:
        """Return the newest observation for every stable record id.

        Event streams are append-only and may receive historical backfills.  A
        later append is therefore not necessarily a newer observation.  Ties
        deliberately resolve to the later event so deterministic reprocessing
        can replace an earlier normalized envelope for the same instant.
        """

        latest: dict[str, dict[str, Any]] = {}
        for event in self._events("records.jsonl"):
            path = self.record_root / str(event["path"])
            record = json.loads(path.read_text(encoding="utf-8"))
            validated = validate_evidence_record(record)
            key = str(event["record_id"])
            current = latest.get(key)
            if current is None or _timestamp_key(
                validated["retrieved_at"]
            ) >= _timestamp_key(current["retrieved_at"]):
                latest[key] = validated
        return latest

    def latest_subject_records(self) -> dict[str, dict[str, Any]]:
        """Return the newest primary record for each source-kind/subject pair."""

        latest: dict[str, dict[str, Any]] = {}
        for record in self.latest_records().values():
            key = f"{record['source']['kind']}:{record['subject']['canonical_name']}"
            current = latest.get(key)
            if current is None or record["retrieved_at"] > current["retrieved_at"]:
                latest[key] = record
        return latest

    def latest_anecdotes(self) -> dict[str, dict[str, Any]]:
        """Return anecdotes separately from primary evidence."""

        latest: dict[str, dict[str, Any]] = {}
        for event in self._events("anecdotes.jsonl"):
            path = self.anecdote_root / str(event["path"])
            record = json.loads(path.read_text(encoding="utf-8"))
            validated = validate_evidence_record(record)
            key = str(event["record_id"])
            current = latest.get(key)
            if current is None or _timestamp_key(
                validated["retrieved_at"]
            ) >= _timestamp_key(current["retrieved_at"]):
                latest[key] = validated
        return latest

    def validate(self) -> dict[str, Any]:
        """Verify hashes, event pointers, contracts, and raw-record lineage."""

        errors: list[str] = []
        snapshots = self._events("snapshots.jsonl")
        snapshot_hashes: set[str] = set()
        for index, event in enumerate(snapshots):
            try:
                digest = str(event["sha256"])
                path = self.raw_root / str(event["path"])
                payload = path.read_bytes()
                if sha256_hex(payload) != digest:
                    errors.append(f"snapshot event {index}: hash mismatch")
                else:
                    snapshot_hashes.add(digest)
            except (KeyError, OSError, TypeError, ValueError) as exc:
                errors.append(f"snapshot event {index}: {exc}")

        records = self._events("records.jsonl")
        anecdotes = self._events("anecdotes.jsonl")
        primary_hashes: set[str] = set()
        primary_ids: set[str] = set()
        anecdote_hashes: set[str] = set()
        anecdote_ids: set[str] = set()
        for stream_name, stream, target_root in (
            ("record", records, self.record_root),
            ("anecdote", anecdotes, self.anecdote_root),
        ):
            for index, event in enumerate(stream):
                try:
                    digest = str(event["record_sha256"])
                    path = target_root / str(event["path"])
                    payload = path.read_bytes()
                    if sha256_hex(payload) != digest:
                        errors.append(f"{stream_name} event {index}: hash mismatch")
                        continue
                    record = json.loads(payload)
                    validate_evidence_record(record)
                    if str(record["record_id"]) != str(event["record_id"]):
                        errors.append(
                            f"{stream_name} event {index}: record_id mismatch"
                        )
                    if str(event["raw_sha256"]) not in snapshot_hashes:
                        errors.append(
                            f"{stream_name} event {index}: raw snapshot is missing"
                        )
                    if str(event["raw_sha256"]) != str(record["source"]["raw_sha256"]):
                        errors.append(
                            f"{stream_name} event {index}: raw_sha256 mismatch"
                        )
                    if str(event["retrieved_at"]) != str(record["retrieved_at"]):
                        errors.append(
                            f"{stream_name} event {index}: retrieved_at mismatch"
                        )
                    if stream_name == "record":
                        primary_hashes.add(digest)
                        primary_ids.add(str(event["record_id"]))
                    else:
                        anecdote_hashes.add(digest)
                        anecdote_ids.add(str(event["record_id"]))
                except (
                    KeyError,
                    OSError,
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
                ) as exc:
                    errors.append(f"{stream_name} event {index}: {exc}")
        return {
            "schema_version": "pheno.evidence.validation.v1",
            "ok": not errors,
            "snapshot_events": len(snapshots),
            "unique_snapshots": len(snapshot_hashes),
            "record_events": len(records),
            "anecdote_events": len(anecdotes),
            # A record id names a logical source/revision observation.  Its
            # normalized content may legitimately be regenerated as adapters
            # improve, so report logical identities and immutable content
            # versions separately instead of conflating both as "unique".
            "unique_records": len(primary_ids),
            "unique_record_contents": len(primary_hashes),
            "superseded_record_events": len(records) - len(primary_ids),
            "unique_anecdotes": len(anecdote_ids),
            "unique_anecdote_contents": len(anecdote_hashes),
            "superseded_anecdote_events": len(anecdotes) - len(anecdote_ids),
            "errors": errors,
        }


__all__ = [
    "DEFAULT_MAX_SNAPSHOT_BYTES",
    "RegistryStore",
    "discover",
    "discover_all",
    "utc_now",
]


def discover() -> dict[str, type]:
    """Return the public adapter lookup table keyed by source kind.

    This is the canonical public API for parent-module adapter lookup.
    Production code (e.g. ``scripts/evidence_registry_discover``) should
    import this function and look up ``discover()[source_kind]`` at call
    time, so that tests that ``patch.object`` any of the public re-export
    modules (e.g. ``scripts.evidence_registry``,
    ``pheno.evidence.adapters``) can substitute fakes.
    """
    # Importing here (rather than at module scope) avoids a hard
    # dependency cycle with the adapters package and keeps the lookup
    # table mutable per Python's module-attribute semantics.
    from .adapters import (
        ArxivAdapter,
        GitHubAdapter,
        HuggingFaceAdapter,
        LocalCorpusAdapter,
        ModelScopeAdapter,
        RedditAdapter,
    )

    return {
        "arxiv": ArxivAdapter,
        "github": GitHubAdapter,
        "hf": HuggingFaceAdapter,
        "local_corpus": LocalCorpusAdapter,
        "modelscope": ModelScopeAdapter,
        "reddit": RedditAdapter,
    }


def discover_all() -> dict[str, type]:
    """Return every public adapter the evidence registry knows about.

    Same lookup semantics as :func:`discover`, but returns the full
    enumeration (including ``local_corpus`` and any future adapters
    that ``discover()`` may decide to filter).
    """
    return discover()
