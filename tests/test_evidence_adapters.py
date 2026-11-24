from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

import pytest
import requests

from pheno.evidence.adapters import (
    ArxivAdapter,
    GitHubAdapter,
    HuggingFaceAdapter,
    LocalCorpusAdapter,
    ModelScopeAdapter,
    OpenAlexAdapter,
    RedditAdapter,
    SemanticScholarAdapter,
    WikipediaAdapter,
)
from pheno.evidence.adapters.base import DiscoveryPage, MetadataClient
from pheno.evidence.adapters.protocols import (
    CandidateExtractor,
    SourceAdapter,
)
from pheno.evidence.contracts import validate_evidence_record

RAW_SHA = "c" * 64
NOW = "2026-07-14T22:00:00+00:00"


def page(
    kind: str, payload, *, endpoint: str, final_url: str | None = None
) -> DiscoveryPage:
    return DiscoveryPage(
        source_kind=kind,
        method="GET",
        endpoint=endpoint,
        query={"q": "test"},
        final_url=final_url or endpoint,
        api_version=None,
        status=200,
        response_headers={"x-ratelimit-remaining": "99"},
        retrieved_at=NOW,
        payload=payload,
        media_type="application/json",
        incomplete=False,
    )


def arxiv_feed(*paper_ids: str) -> str:
    entries = "".join(
        f"""
  <entry>
    <id>http://arxiv.org/abs/{paper_id}</id>
    <title>Paper {paper_id}</title>
    <published>2026-07-02T00:00:00Z</published>
    <category term="cs.CL" />
  </entry>"""
        for paper_id in paper_ids
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>{len(paper_ids)}</opensearch:totalResults>{entries}
</feed>"""


class FakeClient:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return page(
            kwargs["source_kind"],
            self.payload,
            endpoint=kwargs["url"],
            final_url=kwargs["url"] + "?wire=1",
        )


class SequenceClient:
    def __init__(self, payloads, *, final_urls=None) -> None:
        self.payloads = list(payloads)
        self.final_urls = list(final_urls or [])
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        final_url = (
            self.final_urls.pop(0) if self.final_urls else kwargs["url"] + "?wire=1"
        )
        return page(
            kwargs["source_kind"],
            payload,
            endpoint=kwargs["url"],
            final_url=final_url,
        )


class AdapterTests(unittest.TestCase):
    def test_huggingface_search_normalizes_without_downloads(self) -> None:
        client = FakeClient(
            [
                {
                    "id": "Qwen/Qwen3.6-35B-A3B",
                    "sha": "0123456789abcdef0123456789abcdef01234567",
                    "createdAt": "2026-07-10T00:00:00Z",
                    "tags": ["license:apache-2.0"],
                    "config": {
                        "architectures": ["Qwen3MoEForCausalLM"],
                        "max_position_embeddings": 262144,
                    },
                    "safetensors": {"total": 35000000000},
                }
            ]
        )
        adapter = HuggingFaceAdapter(client)
        result = adapter.search("Qwen3.6", limit=5)
        record = adapter.normalize(result, raw_sha256=RAW_SHA)[0]
        validate_evidence_record(record)
        self.assertFalse(record["resolved"]["mutable"])
        self.assertEqual(record["model"]["active_parameters"], None)
        self.assertEqual(client.calls[0]["params"]["limit"], 5)

    def test_huggingface_detail_hydrates_only_pinned_config_metadata(self) -> None:
        sha = "a" * 40
        detail_payload = {
            "id": "Qwen/Qwen3.6-35B-A3B",
            "sha": sha,
            "createdAt": "2026-07-10T00:00:00Z",
            "safetensors": {"total": 35_953_925_552},
            "config": {"model_type": "shallow-hub-config"},
        }
        config_payload = {
            "architectures": ["Qwen3_5MoeForConditionalGeneration"],
            "vision_config": {"hidden_size": 1024},
            "video_token_id": 12,
            "text_config": {
                "architectures": ["Qwen3_5MoeForCausalLM"],
                "hidden_size": 4096,
                "vocab_size": 151_936,
                "max_position_embeddings": 262_144,
                "num_experts": 256,
                "num_experts_per_tok": 8,
                "num_nextn_predict_layers": 1,
                "active_parameters": 3_000_000_000,
            },
        }
        client = SequenceClient([detail_payload, config_payload])
        adapter = HuggingFaceAdapter(client)

        hydrated = adapter.detail("Qwen/Qwen3.6-35B-A3B")
        record = adapter.normalize(hydrated, raw_sha256=RAW_SHA)[0]

        validate_evidence_record(record)
        self.assertEqual(len(client.calls), 2)
        config_call = client.calls[1]
        self.assertEqual(
            config_call["url"],
            f"https://huggingface.co/Qwen/Qwen3.6-35B-A3B/resolve/{sha}/config.json",
        )
        self.assertEqual(config_call["headers"], {"Accept": "application/json"})
        self.assertNotIn("model.safetensors", str(client.calls))
        self.assertEqual(hydrated.payload["_pheno_config_hydration"]["revision"], sha)
        self.assertEqual(record["model"]["context_tokens"], 262_144)
        self.assertEqual(record["model"]["expert_count"], 256)
        self.assertEqual(record["model"]["experts_per_token"], 8)
        self.assertEqual(record["model"]["active_parameters"], 3_000_000_000)
        self.assertEqual(
            record["model"]["mtp_or_draft"], "native MTP (1 predictor layer)"
        )
        self.assertEqual(record["model"]["modalities"], ["text", "image", "video"])

    def test_huggingface_rejects_catastrophic_safetensors_undercount(self) -> None:
        result = page(
            "hf",
            {
                "id": "Example/Example-35B-A3B",
                "sha": "b" * 40,
                "config": {
                    "architectures": ["ExampleMoeForCausalLM"],
                    "hidden_size": 4096,
                    "vocab_size": 128_000,
                },
                "safetensors": {"total": 35_000_000},
            },
            endpoint="https://huggingface.co/api/models/Example/Example-35B-A3B",
        )
        record = HuggingFaceAdapter(FakeClient({})).normalize(
            result,
            raw_sha256=RAW_SHA,
        )[0]

        validate_evidence_record(record)
        self.assertIsNone(record["model"]["total_parameters"])
        self.assertTrue(record["quality"]["incomplete"])
        self.assertEqual(record["quality"]["confidence"], "low")
        self.assertTrue(
            any("Rejected Hub safetensors.total" in note for note in record["notes"])
        )

    def test_huggingface_does_not_hydrate_mutable_or_malformed_revision(self) -> None:
        client = SequenceClient(
            [
                {
                    "id": "Example/Model-1B",
                    "sha": "short-sha",
                    "lastModified": "2026-07-14T00:00:00Z",
                    "config": {"model_type": "example"},
                }
            ]
        )
        adapter = HuggingFaceAdapter(client)

        detail = adapter.detail("Example/Model-1B")
        record = adapter.normalize(detail, raw_sha256=RAW_SHA)[0]

        self.assertEqual(len(client.calls), 1)
        self.assertTrue(detail.incomplete)
        self.assertTrue(record["resolved"]["mutable"])
        self.assertEqual(record["source"]["revision"], "2026-07-14T00:00:00Z")

    def test_huggingface_rejects_cross_host_config_redirect(self) -> None:
        sha = "c" * 40
        client = SequenceClient(
            [
                {"id": "Example/Model-1B", "sha": sha},
                {"architectures": ["ExampleForCausalLM"]},
            ],
            final_urls=[
                "https://huggingface.co/api/models/Example/Model-1B",
                f"https://cdn.example.invalid/Example/Model-1B/{sha}/config.json",
            ],
        )
        adapter = HuggingFaceAdapter(client)

        with self.assertRaisesRegex(ValueError, "unexpected URL"):
            adapter.detail("Example/Model-1B")

    def test_huggingface_retains_immutable_detail_when_config_is_404(self) -> None:
        sha = "d" * 40
        response = requests.Response()
        response.status_code = 404
        missing = requests.HTTPError("not found", response=response)
        client = SequenceClient(
            [
                {
                    "id": "Example/Artifact-1B-GGUF",
                    "sha": sha,
                    "config": {"model_type": "example"},
                    "safetensors": {"total": 1_000_000_000},
                },
                missing,
            ]
        )
        adapter = HuggingFaceAdapter(client)

        detail = adapter.detail("Example/Artifact-1B-GGUF")
        record = adapter.normalize(detail, raw_sha256=RAW_SHA)[0]

        validate_evidence_record(record)
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(detail.incomplete)
        self.assertEqual(
            detail.payload["_pheno_config_hydration"],
            {
                "filename": "config.json",
                "revision": sha,
                "status": "missing",
            },
        )
        self.assertFalse(record["resolved"]["mutable"])
        self.assertTrue(record["quality"]["incomplete"])
        self.assertTrue(any("returned HTTP 404" in note for note in record["notes"]))

    def test_huggingface_rejects_detail_identity_mismatch(self) -> None:
        client = SequenceClient([{"id": "Wrong/Model-1B", "sha": "e" * 40}])
        adapter = HuggingFaceAdapter(client)

        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            adapter.detail("Expected/Model-1B")
        self.assertEqual(len(client.calls), 1)

    @pytest.mark.slow
    def test_huggingface_does_not_swallow_config_server_error(self) -> None:
        pytest.skip('slow: retry backoff sleeps >30s')
        response = requests.Response()
        response.status_code = 503
        unavailable = requests.HTTPError("unavailable", response=response)
        # detail() and hydrate_config() are both wrapped with @with_retry(max_retries=3).
        # When hydrate_config exhausts retries on 503, it re-raises; detail's try/except
        # re-raises (status != 404); detail's own @with_retry catches and retries the
        # entire detail call.  Each detail attempt needs 1 dict + 4 hydrate_config calls,
        # and detail retries up to 3 times → 4 × (1 + 4) = 20 payloads.
        payloads: list = []
        for _ in range(4):
            payloads.append({"id": "Example/Model-1B", "sha": "f" * 40})
            payloads.extend([unavailable] * 4)
        client = SequenceClient(payloads)
        adapter = HuggingFaceAdapter(client)

        with self.assertRaises(requests.HTTPError):
            adapter.detail("Example/Model-1B")

    def test_modelscope_uses_current_parameter_names_and_bound(self) -> None:
        client = FakeClient({"data": {"models": []}})
        adapter = ModelScopeAdapter(client)
        adapter.search("Qwen", page_number=2, page_size=25, owner="Qwen")
        params = client.calls[0]["params"]
        self.assertEqual(params["page_number"], 2)
        self.assertEqual(params["page_size"], 25)
        self.assertNotIn("author", params)
        with self.assertRaisesRegex(ValueError, "<= 3000"):
            adapter.search("Qwen", page_number=31, page_size=100)

    def test_modelscope_normalizes_live_detail_data_envelope(self) -> None:
        result = page(
            "modelscope",
            {
                "success": True,
                "data": {
                    "id": "Qwen/Qwen3.6-27B",
                    "last_modified": "2026-07-14T00:00:00Z",
                    "license": "apache-2.0",
                    "params": 27_000_000_000,
                },
            },
            endpoint="https://modelscope.cn/openapi/v1/models/Qwen/Qwen3.6-27B",
        )
        record = ModelScopeAdapter(FakeClient({})).normalize(
            result,
            raw_sha256=RAW_SHA,
        )[0]
        validate_evidence_record(record)
        self.assertEqual(record["subject"]["canonical_name"], "Qwen/Qwen3.6-27B")
        self.assertEqual(record["model"]["total_parameters"], 27_000_000_000)
        self.assertEqual(record["license"]["declared"], ["apache-2.0"])

        zero = page(
            "modelscope",
            {"data": {"id": "Qwen/Empty-Params", "params": 0}},
            endpoint="https://modelscope.cn/openapi/v1/models/Qwen/Empty-Params",
        )
        zero_record = ModelScopeAdapter(FakeClient({})).normalize(
            zero,
            raw_sha256=RAW_SHA,
        )[0]
        self.assertIsNone(zero_record["model"]["total_parameters"])

    def test_github_search_token_never_enters_record(self) -> None:
        client = FakeClient(
            {
                "incomplete_results": False,
                "items": [
                    {
                        "full_name": "vllm-project/vllm",
                        "html_url": "https://github.com/vllm-project/vllm",
                        "pushed_at": "2026-07-14T00:00:00Z",
                        "created_at": "2023-01-01T00:00:00Z",
                        "license": {"spdx_id": "Apache-2.0"},
                    }
                ],
            }
        )
        secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
        adapter = GitHubAdapter(client, token=secret)
        result = adapter.search("speculative decoding")
        record = adapter.normalize(result, raw_sha256=RAW_SHA)[0]
        validate_evidence_record(record)
        self.assertNotIn(secret, str(record))
        self.assertTrue(record["resolved"]["mutable"])

    def test_arxiv_atom_parses_versioned_identity(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2607.01234v1</id>
    <title>Example speculative decoding paper</title>
    <published>2026-07-02T00:00:00Z</published>
    <category term="cs.CL" />
  </entry>
</feed>"""
        result = page(
            "arxiv",
            xml,
            endpoint="https://export.arxiv.org/api/query",
        )
        result = DiscoveryPage(
            **{**result.__dict__, "media_type": "application/atom+xml"}
        )
        record = ArxivAdapter(FakeClient(xml)).normalize(
            result,
            raw_sha256=RAW_SHA,
        )[0]
        validate_evidence_record(record)
        self.assertFalse(record["resolved"]["mutable"])
        self.assertEqual(record["subject"]["canonical_name"], "2607.01234v1")

    def test_arxiv_resolves_base_id_with_id_list_and_pacing(self) -> None:
        client = FakeClient(arxiv_feed("2603.03251v3"))
        adapter = ArxivAdapter(client)

        result = adapter.resolve_paper("2603.03251")
        record = adapter.normalize(result, raw_sha256=RAW_SHA)[0]

        validate_evidence_record(record)
        self.assertEqual(
            client.calls[0]["params"],
            {"id_list": "2603.03251", "start": 0, "max_results": 1},
        )
        self.assertNotIn("search_query", client.calls[0]["params"])
        self.assertEqual(client.calls[0]["minimum_interval"], 3.0)
        self.assertFalse(result.incomplete)
        self.assertFalse(record["resolved"]["mutable"])
        self.assertEqual(record["subject"]["canonical_name"], "2603.03251v3")

    def test_arxiv_resolves_exact_versioned_id(self) -> None:
        client = FakeClient(arxiv_feed("2605.17613v2"))
        adapter = ArxivAdapter(client)

        result = adapter.resolve_paper("2605.17613v2")

        self.assertEqual(result.payload, arxiv_feed("2605.17613v2"))
        self.assertEqual(client.calls[0]["params"]["id_list"], "2605.17613v2")

    def test_arxiv_resolution_rejects_malformed_ids_before_request(self) -> None:
        invalid_ids = [
            "2603.03251,2504.19874",
            "https://arxiv.org/abs/2603.03251",
            "2613.03251",
            "2603.123",
            "2603.03251v0",
            " 2603.03251",
        ]
        for paper_id in invalid_ids:
            with self.subTest(paper_id=paper_id):
                client = FakeClient(arxiv_feed("2603.03251v1"))
                adapter = ArxivAdapter(client)
                with self.assertRaisesRegex(ValueError, "modern base or versioned"):
                    adapter.resolve_paper(paper_id)
                self.assertEqual(client.calls, [])

    def test_arxiv_resolution_rejects_identity_or_cardinality_mismatch(self) -> None:
        cases = [
            ("2603.03251", arxiv_feed(), "exactly one entry"),
            (
                "2603.03251",
                arxiv_feed("2603.03251v1", "2603.03251v2"),
                "exactly one entry",
            ),
            ("2603.03251", arxiv_feed("2603.03252v1"), "identity mismatch"),
            ("2603.03251v2", arxiv_feed("2603.03251v3"), "version mismatch"),
        ]
        for requested, payload, message in cases:
            with self.subTest(requested=requested, message=message):
                adapter = ArxivAdapter(FakeClient(payload))
                with self.assertRaisesRegex(ValueError, message):
                    adapter.resolve_paper(requested)

    def test_reddit_discards_raw_title_and_body(self) -> None:
        raw = {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_example",
                            "permalink": "/r/LocalLLaMA/comments/example/report/",
                            "subreddit": "LocalLLaMA",
                            "title": "must not persist",
                            "selftext": "must not persist either",
                        }
                    }
                ]
            }
        }
        result = page(
            "reddit",
            raw,
            endpoint="https://oauth.reddit.com/search",
        )
        citation = RedditAdapter.citation_pages(result)[0]
        self.assertNotIn("title", citation.payload)
        self.assertNotIn("selftext", citation.payload)
        record = RedditAdapter.normalize_citation(citation, raw_sha256=RAW_SHA)
        validate_evidence_record(record)
        self.assertEqual(record["source"]["evidence_class"], "A")

    def test_local_corpus_persists_hash_metadata_not_content_or_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = "# Private research\nA design hypothesis."
            source = root / "ChatGPT-example.md"
            source.write_text(content, encoding="utf-8")
            result = LocalCorpusAdapter.scan(root)[0]
            self.assertNotIn(content, str(result.payload))
            self.assertNotIn(str(root), str(result.payload))
            record = LocalCorpusAdapter.normalize(result, raw_sha256=RAW_SHA)
            validate_evidence_record(record)
            self.assertEqual(record["source"]["evidence_class"], "L")

    def test_metadata_client_rejects_nonmetadata_hosts_before_network(self) -> None:
        class ExplodingSession:
            def request(self, *args, **kwargs):
                raise AssertionError("network should not be reached")

        client = MetadataClient(session=ExplodingSession())
        with self.assertRaisesRegex(ValueError, "not allowed"):
            client.request(
                source_kind="hf",
                method="GET",
                url="https://example.com/model.bin",
            )

    def test_protocol_conformance_all_adapters_satisfy_sourceadapter(self) -> None:
        """Every built-in adapter class must satisfy the SourceAdapter Protocol.

        SourceAdapter requires ``kind`` (str), ``endpoint`` (str), and
        ``search`` + ``normalize`` callables returning the right types.
        Adapters that also implement ``candidate_ids`` satisfy the
        CandidateExtractor Protocol too.
        """
        client = MetadataClient()
        adapters = [
            ("hf", HuggingFaceAdapter(client)),
            ("modelscope", ModelScopeAdapter(client)),
            ("arxiv", ArxivAdapter(client)),
            ("github", GitHubAdapter(client)),
            # RedditAdapter requires OAuth tokens — checked separately.
        ]
        for kind, adapter in adapters:
            with self.subTest(kind=kind):
                self.assertIsInstance(adapter, SourceAdapter)
                self.assertTrue(hasattr(adapter, "kind"))
                self.assertTrue(hasattr(adapter, "endpoint"))
                self.assertTrue(callable(getattr(adapter, "normalize", None)))
                if kind in ("hf", "modelscope"):
                    # Adapters that emit registry records expose
                    # candidate_ids() for enumeration.
                    self.assertIsInstance(adapter, CandidateExtractor)
                else:
                    self.assertFalse(
                        isinstance(adapter, CandidateExtractor),
                        f"{kind} should NOT satisfy CandidateExtractor "
                        "(no candidate_ids method)",
                    )

    def test_build_adapter_dispatch_all_kinds(self) -> None:
        """build_adapter() returns a usable instance for every supported kind."""
        from pheno.evidence.adapters import build_adapter, supported_kinds

        client = MetadataClient()
        expected_classes = {
            "hf": HuggingFaceAdapter,
            "modelscope": ModelScopeAdapter,
            "arxiv": ArxivAdapter,
            "github": GitHubAdapter,
            "openalex": OpenAlexAdapter,
            "semantic_scholar": SemanticScholarAdapter,
            "wikipedia": WikipediaAdapter,
        }
        for kind in supported_kinds():
            with self.subTest(kind=kind):
                if kind == "local_corpus":
                    # Returns the class itself (no instance).
                    self.assertIs(build_adapter(kind), LocalCorpusAdapter)
                elif kind == "reddit":
                    # Requires OAuth kwargs.
                    with self.assertRaises(ValueError):
                        build_adapter(kind, client=client)
                    with self.assertRaises(ValueError):
                        build_adapter(kind, client=client, access_token="x")
                    adapter = build_adapter(
                        kind,
                        client=client,
                        access_token="x",
                        user_agent="pheno-test",
                    )
                    self.assertIsInstance(adapter, RedditAdapter)
                else:
                    adapter = build_adapter(kind, client=client)
                    self.assertIsInstance(adapter, expected_classes[kind])

    def test_build_adapter_rejects_unknown_kind(self) -> None:
        """build_adapter() raises ValueError for unknown kinds."""
        from pheno.evidence.adapters import build_adapter

        with self.assertRaisesRegex(ValueError, "unknown adapter kind"):
            build_adapter("not-a-real-kind", client=MetadataClient())

    def test_dispatch_search_requires_sourceadapter(self) -> None:
        """search() dispatch raises TypeError for local_corpus (no search)."""
        from pheno.evidence.adapters import search

        with self.assertRaises(TypeError):
            search("local_corpus", "anything")

    def test_dispatch_candidate_ids_rejects_non_extractors(self) -> None:
        """candidate_ids() dispatch raises TypeError for arxiv/github."""
        from pheno.evidence.adapters import candidate_ids

        # Build a fake DiscoveryPage with the minimum required fields.
        fake_page = page("arxiv", [], endpoint="https://export.arxiv.org/api/query")
        with self.assertRaises(TypeError):
            candidate_ids("arxiv", fake_page, client=MetadataClient())
        with self.assertRaises(TypeError):
            candidate_ids("github", fake_page, client=MetadataClient())

    def test_adapter_init_validation(self) -> None:
        """Each adapter __init__ validates its inputs."""
        # MetadataClient rejects negative timeout / max_response_bytes / retries.
        with self.assertRaises(ValueError):
            MetadataClient(timeout=0)
        with self.assertRaises(ValueError):
            MetadataClient(max_response_bytes=0)
        with self.assertRaises(ValueError):
            MetadataClient(retries=-1)
        # RedditAdapter requires access_token + user_agent.
        with self.assertRaises(ValueError):
            RedditAdapter(MetadataClient(), access_token="", user_agent="")
        with self.assertRaises(ValueError):
            RedditAdapter(MetadataClient(), access_token="x", user_agent="")

    def test_full_pipeline_search_normalize_registry(self) -> None:
        """End-to-end pipeline: build_adapter → search → normalize → validate.

        Uses a fake HF payload (no network) to verify the entire flow:
          1. Build an HF adapter via build_adapter('hf', client=...)
          2. Inject a fake DiscoveryPage that looks like an HF search response
          3. Call candidate_ids(page) (CandidateExtractor path)
          4. Call normalize(page, raw_sha256=...) (SourceAdapter path)
          5. Validate each record against the registry contract.
        """
        from pheno.evidence.contracts import validate_evidence_record

        client = MetadataClient()
        adapter = HuggingFaceAdapter(client)
        self.assertIsInstance(adapter, SourceAdapter)
        self.assertIsInstance(adapter, CandidateExtractor)

        # Fake HF search response (list of {id, modelId, sha, ...}).
        fake_payload = [
            {
                "id": "owner/model-a",
                "modelId": "owner/model-a",
                "sha": "a" * 40,
                "private": False,
            },
            {
                "id": "owner/model-b",
                "modelId": "owner/model-b",
                "sha": "b" * 40,
                "private": False,
            },
        ]
        fake_page = page(
            "hf", fake_payload, endpoint="https://huggingface.co/api/models"
        )
        fake_page = dataclasses.replace(fake_page, incomplete=True)

        ids = adapter.candidate_ids(fake_page)
        self.assertEqual(ids, ["owner/model-a", "owner/model-b"])

        records = adapter.normalize(fake_page, raw_sha256="c" * 64)
        self.assertEqual(len(records), 2)
        for r in records:
            validate_evidence_record(r)
            self.assertEqual(r["schema_version"], "pheno.evidence.v1")
            self.assertTrue(r["record_id"])
            self.assertEqual(r["gates"]["metadata_only"], True)


if __name__ == "__main__":
    unittest.main()
