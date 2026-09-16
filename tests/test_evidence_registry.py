from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.evidence_registry as evidence_registry_cli
from pheno.evidence import ContractError, RegistryStore, make_record_id
from pheno.evidence.contracts import EVIDENCE_SCHEMA_VERSION, validate_evidence_record
from pheno.evidence.redaction import REDACTED, redact_object
from scripts.evidence_registry import _attempt_operation, discover, plan

RAW_SHA = "a" * 64
ROOT = Path(__file__).resolve().parents[1]
AUDITED_ARXIV_IDS = [
    "2603.03251",
    "2504.19874",
    "2602.06036",
    "2607.05147",
    "2606.02091",
    "2604.12989",
    "2606.01813",
    "2606.18394",
    "2605.29707",
    "2607.08642",
    "2511.08923",
    "2511.20639",
    "2605.30876",
    "2605.17613",
    "2603.20216",
    "2602.03338",
    "2605.17757",
    "2603.28430",
    "2607.03333",
    "2607.04244",
    "2607.12696",
    "2604.10152",
    "2603.19289",
    "2607.12875",
    "2607.01308",
    "2607.00760",
    "2607.10582",
    "2607.01520",
    "2607.01065",
    "2606.24597",
    "2606.16140",
]


class _FakeStore:
    def validate(self) -> dict:
        return {"ok": True, "errors": []}


class _FakeMetadataClient:
    def __init__(self, **_kwargs) -> None:
        pass


class _MiddleFailureHuggingFaceAdapter:
    endpoint = "https://huggingface.co/api/models"
    detail_calls: list[str] = []
    search_calls: list[str] = []

    def __init__(self, _client) -> None:
        pass

    def detail(self, subject: str) -> dict:
        self.detail_calls.append(subject)
        if subject == "publisher/resolve-middle":
            raise RuntimeError(
                "Bearer abcdefghijklmnopqrstuvwxyz C:\\private\\registry-secret"
            )
        return {"subject": subject}

    def search(self, query: str, **_kwargs) -> dict:
        self.search_calls.append(query)
        if query == "query-middle":
            raise RuntimeError(
                "Bearer abcdefghijklmnopqrstuvwxyz C:\\private\\registry-secret"
            )
        return {"query": query}

    @staticmethod
    def normalize(_page, *, raw_sha256: str) -> dict:
        return {"raw_sha256": raw_sha256}

    @staticmethod
    def candidate_ids(_page) -> list[str]:
        return []


class _MiddleFailureArxivAdapter:
    endpoint = "https://export.arxiv.org/api/query"
    resolve_calls: list[str] = []

    def __init__(self, _client) -> None:
        pass

    def resolve_paper(self, subject: str) -> dict:
        self.resolve_calls.append(subject)
        if subject == "2605.17613":
            raise RuntimeError("middle arXiv failure")
        return {"subject": subject}

    @staticmethod
    def normalize(_page, *, raw_sha256: str) -> dict:
        return {"raw_sha256": raw_sha256}


def record(
    *, raw_sha: str = RAW_SHA, kind: str = "hf", evidence_class: str = "V"
) -> dict:
    revision = "0123456789abcdef"
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
            "architecture": "Qwen3.6MoEForCausalLM",
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
            "method": "GET" if kind != "local_corpus" else "LOCAL_SCAN",
            "endpoint": (
                "https://huggingface.co/api/models"
                if kind != "local_corpus"
                else "local://corpus-scan"
            ),
            "query": (
                {"search": "Qwen3.6"}
                if kind != "local_corpus"
                else {"pattern": "ChatGPT-*.md"}
            ),
            "final_url": (
                "https://huggingface.co/api/models?search=Qwen3.6"
                if kind != "local_corpus"
                else "local://corpus-scan"
            ),
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
        "notes": [],
    }


class EvidenceContractTests(unittest.TestCase):
    def test_valid_record(self) -> None:
        payload = record()
        self.assertEqual(
            validate_evidence_record(payload)["record_id"], payload["record_id"]
        )

    def test_inference_is_a_distinct_evidence_class(self) -> None:
        payload = record(evidence_class="I")
        self.assertEqual(
            validate_evidence_record(payload)["source"]["evidence_class"], "I"
        )

    def test_record_id_must_match_subject_revision(self) -> None:
        payload = record()
        payload["record_id"] = "hf:wrong:0123456789abcdef"
        with self.assertRaisesRegex(ContractError, "does not match"):
            validate_evidence_record(payload)

    def test_unknown_fields_and_nan_are_rejected(self) -> None:
        payload = record()
        payload["unbounded_blob"] = "no"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_evidence_record(payload)
        payload = record()
        payload["benchmark_claims"][0]["score"] = float("nan")
        with self.assertRaisesRegex(ContractError, "finite JSON"):
            validate_evidence_record(payload)

    def test_reddit_is_always_anecdotal(self) -> None:
        payload = record(kind="reddit", evidence_class="V")
        payload["source"]["url"] = (
            "https://www.reddit.com/r/LocalLLaMA/comments/example"
        )
        with self.assertRaisesRegex(ContractError, "class A"):
            validate_evidence_record(payload)

    def test_reddit_raw_content_cannot_enter_durable_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "snapshots are forbidden"):
                store.put_snapshot(
                    source_kind="reddit",
                    source_url="https://www.reddit.com/r/LocalLLaMA/comments/example",
                    payload={"title": "raw user content", "body": "raw user content"},
                )

    def test_reddit_citation_metadata_is_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            event = store.put_snapshot(
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
            self.assertEqual(event["source_kind"], "reddit")

    def test_local_corpus_path_is_not_persisted(self) -> None:
        payload = record(kind="local_corpus", evidence_class="L")
        payload["source"]["url"] = "local://sha256/" + "b" * 64
        self.assertEqual(
            validate_evidence_record(payload)["source"]["kind"], "local_corpus"
        )

    def test_secret_is_rejected(self) -> None:
        payload = record()
        payload["notes"] = ["Bearer abcdefghijklmnopqrstuvwxyz1234"]
        with self.assertRaisesRegex(ContractError, "token"):
            validate_evidence_record(payload)

    def test_redaction_does_not_confuse_context_tokens_with_credentials(self) -> None:
        payload = {
            "context_tokens": 4096,
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
        }
        self.assertEqual(
            redact_object(payload), {"context_tokens": 4096, "authorization": REDACTED}
        )

    def test_modelscope_explicit_resolutions_are_in_discovery_plan(self) -> None:
        config = {
            "sources": {
                "modelscope": {
                    "queries": [{"query": "Qwen3.6"}],
                    "resolve_models": [
                        "Qwen/Qwen3.6-27B",
                        "Qwen/Qwen3.6-35B-A3B",
                    ],
                }
            }
        }
        operations = plan(config, ["modelscope"], max_queries=1)["operations"]
        self.assertEqual(
            [row["resolve_subject"] for row in operations if "resolve_subject" in row],
            ["Qwen/Qwen3.6-27B", "Qwen/Qwen3.6-35B-A3B"],
        )
        self.assertTrue(all(row["artifact_download"] is False for row in operations))
        self.assertTrue(all(row["shortlist_mutation"] is False for row in operations))

    def test_explicit_resolution_with_no_normalized_record_fails(self) -> None:
        report = {
            "snapshots": 0,
            "records": 0,
            "queries": 0,
            "planned": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "operations": [],
            "errors": [],
        }
        succeeded, _ = _attempt_operation(
            report,
            operation_id="hf:resolve:0000",
            source="hf",
            kind="resolve",
            action=lambda: (1, 0, None),
            subject="Example/Empty",
        )
        self.assertFalse(succeeded)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["snapshots"], 1)
        self.assertEqual(report["operations"][0]["status"], "failed")

    def test_local_discovery_plan_does_not_expose_private_roots(self) -> None:
        private_root = r"C:\Users\private\ChatGPT exports"
        config = {
            "sources": {
                "local_corpus": {
                    "roots": [private_root],
                    "pattern": "ChatGPT-*.md",
                }
            }
        }
        result = plan(config, ["local_corpus"], max_queries=None)
        rendered = json.dumps(result)
        self.assertNotIn(private_root, rendered)
        self.assertEqual(
            result["operations"][0]["query"],
            {"root_index": 0, "pattern": "ChatGPT-*.md"},
        )

    def test_arxiv_explicit_resolutions_are_stable_plan_operations(self) -> None:
        config = {
            "sources": {
                "arxiv": {
                    "queries": [{"query": "all:speculative decoding"}],
                    "resolve_papers": ["2603.03251", "2605.17613"],
                }
            }
        }
        operations = plan(config, ["arxiv"], max_queries=1)["operations"]
        resolutions = [row for row in operations if "resolve_subject" in row]
        self.assertEqual(
            [row["operation_id"] for row in resolutions],
            ["arxiv:resolve:0000", "arxiv:resolve:0001"],
        )
        self.assertEqual(
            [row["resolve_subject"] for row in resolutions],
            ["2603.03251", "2605.17613"],
        )

    def test_config_contains_all_audited_arxiv_resolutions(self) -> None:
        config = evidence_registry_cli.load_config(
            ROOT / "config" / "evidence_registry.yaml"
        )
        self.assertEqual(
            config["sources"]["arxiv"]["resolve_papers"], AUDITED_ARXIV_IDS
        )


class EvidenceDiscoveryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        _MiddleFailureHuggingFaceAdapter.detail_calls = []
        _MiddleFailureHuggingFaceAdapter.search_calls = []
        _MiddleFailureArxivAdapter.resolve_calls = []

    @staticmethod
    def _config() -> dict:
        return {
            "policy": {
                "metadata_only": True,
                "allow_model_artifact_download": False,
                "mutate_locked_shortlist": False,
                "timeout_seconds": 1,
                "max_response_bytes": 1024,
                "retries": 0,
            },
            "sources": {
                "hf": {
                    "resolve_models": [
                        "publisher/resolve-first",
                        "publisher/resolve-middle",
                        "publisher/resolve-last",
                    ],
                    "queries": [
                        {"query": "query-first"},
                        {"query": "query-middle"},
                        {"query": "query-last"},
                    ],
                    "hydrate_limit": 0,
                }
            },
        }

    def test_middle_failures_do_not_skip_later_resolutions_or_queries(self) -> None:
        with (
            patch.object(
                evidence_registry_cli,
                "MetadataClient",
                _FakeMetadataClient,
            ),
            patch.object(
                evidence_registry_cli,
                "HuggingFaceAdapter",
                _MiddleFailureHuggingFaceAdapter,
            ),
            patch.object(
                evidence_registry_cli,
                "persist_page",
                return_value=(1, 1),
            ),
        ):
            result = discover(
                self._config(),
                ["hf"],
                _FakeStore(),
                max_queries=None,
                allow_metadata_network=True,
            )

        self.assertEqual(
            _MiddleFailureHuggingFaceAdapter.detail_calls,
            [
                "publisher/resolve-first",
                "publisher/resolve-middle",
                "publisher/resolve-last",
            ],
        )
        self.assertEqual(
            _MiddleFailureHuggingFaceAdapter.search_calls,
            ["query-first", "query-middle", "query-last"],
        )
        self.assertEqual(result["planned"], 6)
        self.assertEqual(result["schema_version"], "pheno.evidence.discovery-run.v2")
        self.assertTrue(result["metadata_only"])
        self.assertFalse(result["artifact_download"])
        self.assertFalse(result["shortlist_mutation"])
        self.assertEqual(result["completed"], 4)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["queries"], 6)
        self.assertEqual(
            [operation["status"] for operation in result["operations"]],
            ["completed", "failed", "completed", "completed", "failed", "completed"],
        )
        self.assertEqual(
            [operation["operation_id"] for operation in result["operations"]],
            [
                "hf:resolve:0000",
                "hf:resolve:0001",
                "hf:resolve:0002",
                "hf:query:0000",
                "hf:query:0001",
                "hf:query:0002",
            ],
        )
        rendered = json.dumps(result)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", rendered)
        self.assertNotIn(r"C:\\private\\registry-secret", rendered)
        self.assertFalse(result["ok"])

    def test_missing_reddit_credentials_are_safely_counted_as_skipped(self) -> None:
        config = self._config()
        config["sources"] = {
            "reddit": {
                "queries": [{"query": "first"}, {"query": "second"}],
            }
        }
        with (
            patch.object(
                evidence_registry_cli,
                "MetadataClient",
                _FakeMetadataClient,
            ),
            patch.dict(
                evidence_registry_cli.os.environ,
                {"REDDIT_ACCESS_TOKEN": "", "REDDIT_USER_AGENT": ""},
            ),
        ):
            result = discover(
                config,
                ["reddit"],
                _FakeStore(),
                max_queries=None,
                allow_metadata_network=True,
            )

        self.assertEqual(result["planned"], 2)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(result["queries"], 0)
        self.assertTrue(
            all(
                operation["reason"] == "credentials_unavailable"
                for operation in result["operations"]
            )
        )
        rendered = json.dumps(result)
        self.assertNotIn("REDDIT_ACCESS_TOKEN", rendered)
        self.assertNotIn("REDDIT_USER_AGENT", rendered)
        self.assertFalse(result["ok"])

    def test_arxiv_middle_resolution_failure_does_not_skip_later_id(self) -> None:
        config = self._config()
        config["sources"] = {
            "arxiv": {
                "resolve_papers": ["2603.03251", "2605.17613", "2605.17757"],
                "queries": [{"query": "must-not-run-in-resolve-only"}],
            }
        }
        with (
            patch.object(
                evidence_registry_cli,
                "MetadataClient",
                _FakeMetadataClient,
            ),
            patch.object(
                evidence_registry_cli,
                "ArxivAdapter",
                _MiddleFailureArxivAdapter,
            ),
            patch.object(
                evidence_registry_cli,
                "persist_page",
                return_value=(1, 1),
            ),
        ):
            result = discover(
                config,
                ["arxiv"],
                _FakeStore(),
                max_queries=1,
                allow_metadata_network=True,
                resolve_only=True,
            )

        self.assertEqual(
            _MiddleFailureArxivAdapter.resolve_calls,
            ["2603.03251", "2605.17613", "2605.17757"],
        )
        self.assertEqual(result["planned"], 3)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(
            [operation["operation_id"] for operation in result["operations"]],
            ["arxiv:resolve:0000", "arxiv:resolve:0001", "arxiv:resolve:0002"],
        )
        self.assertTrue(result["resolve_only"])


class RegistryStoreTests(unittest.TestCase):
    def test_content_addressed_snapshot_record_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            snapshot = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models?access_token=do-not-store",
                payload={"id": "Qwen/Qwen3.6-35B-A3B", "api_key": "do-not-store"},
            )
            payload = record(raw_sha=snapshot["sha256"])
            first = store.put_record(payload)
            second = store.put_record(payload)
            self.assertEqual(first["record_sha256"], second["record_sha256"])
            report = store.validate()
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["snapshot_events"], 1)
            self.assertEqual(report["record_events"], 1)
            self.assertEqual(report["unique_records"], 1)
            self.assertEqual(report["unique_record_contents"], 1)
            self.assertEqual(report["superseded_record_events"], 0)
            all_text = "\n".join(
                path.read_text(encoding="utf-8", errors="replace")
                for path in Path(temp_dir).rglob("*")
                if path.is_file()
            )
            self.assertNotIn("do-not-store", all_text)

    def test_logical_record_counts_and_latest_use_observation_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            snapshot = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            newer = record(raw_sha=snapshot["sha256"])
            newer["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            newer["notes"] = ["newer"]
            store.put_record(newer)

            # Historical backfills may be appended later; they must remain in
            # the immutable event history without replacing the newest view.
            older = record(raw_sha=snapshot["sha256"])
            older["retrieved_at"] = "2026-07-14T19:00:00-01:00"
            older["notes"] = ["older"]
            store.put_record(older)

            report = store.validate()
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["record_events"], 2)
            self.assertEqual(report["unique_records"], 1)
            self.assertEqual(report["unique_record_contents"], 2)
            self.assertEqual(report["superseded_record_events"], 1)
            latest = store.latest_records()[newer["record_id"]]
            self.assertEqual(latest["notes"], ["newer"])

    def test_event_envelope_must_match_record_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            snapshot = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            store.put_record(record(raw_sha=snapshot["sha256"]))
            event_path = store.event_root / "records.jsonl"
            event = json.loads(event_path.read_text(encoding="utf-8"))
            event["retrieved_at"] = "2026-07-14T21:00:00+00:00"
            event_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("retrieved_at mismatch" in error for error in report["errors"])
            )

    def test_tampered_record_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            snapshot = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            event = store.put_record(record(raw_sha=snapshot["sha256"]))
            path = store.record_root / event["path"]
            path.write_text(json.dumps({"tampered": True}), encoding="utf-8")
            report = store.validate()
            self.assertFalse(report["ok"])
            self.assertTrue(any("hash mismatch" in error for error in report["errors"]))

    def test_missing_raw_snapshot_is_rejected_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "raw snapshot"):
                store.put_record(record())

    def test_anecdote_records_have_a_separate_event_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            snapshot = store.put_snapshot(
                source_kind="reddit",
                source_url="https://www.reddit.com/r/LocalLLaMA/comments/example",
                media_type="application/vnd.pheno.reddit-citation+json",
                payload={
                    "fullname": "t3_example",
                    "permalink": "/r/LocalLLaMA/comments/example",
                    "retrieved_at": "2026-07-14T20:00:00Z",
                    "tombstone_state": "live",
                    "paraphrased_claim": "A user reported thermal throttling.",
                },
            )
            payload = record(
                raw_sha=snapshot["sha256"],
                kind="reddit",
                evidence_class="A",
            )
            payload["source"]["url"] = (
                "https://www.reddit.com/r/LocalLLaMA/comments/example"
            )
            store.put_record(payload)
            report = store.validate()
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["record_events"], 0)
            self.assertEqual(report["anecdote_events"], 1)
            self.assertEqual(report["unique_records"], 0)
            self.assertEqual(report["unique_anecdotes"], 1)
            self.assertEqual(report["unique_anecdote_contents"], 1)
            self.assertEqual(report["superseded_anecdote_events"], 0)
            self.assertEqual(len(store.latest_records()), 0)
            self.assertEqual(len(store.latest_anecdotes()), 1)

    def test_dead_writer_lock_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir))
            lock = store.event_root / "snapshots.jsonl.lock"
            lock.parent.mkdir(parents=True)
            lock.write_text("pid=999999999\n", encoding="ascii")
            event = store.put_snapshot(
                source_kind="hf",
                source_url="https://huggingface.co/api/models",
                payload={"id": "example"},
            )
            self.assertEqual(event["source_kind"], "hf")

    def test_snapshot_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RegistryStore(Path(temp_dir), max_snapshot_bytes=4)
            with self.assertRaisesRegex(ValueError, "limit"):
                store.put_snapshot(
                    source_kind="github",
                    source_url="https://api.github.com/search/repositories",
                    payload="too large",
                    media_type="text/plain",
                )


if __name__ == "__main__":
    unittest.main()
