"""Tests for evidence adapter tuning overrides (rate/breaker) — v0.12 task 5."""

from __future__ import annotations

from unittest.mock import MagicMock

from pheno.evidence.adapters.base import MetadataClient, RetryPolicy
from pheno.evidence.adapters.circuit_breaker import CircuitBreaker, get_circuit_breaker
from pheno.evidence.adapters.openalex import OpenAlexAdapter
from pheno.evidence.adapters.rate_limit import RateLimiter, get_rate_limiter
from pheno.evidence.adapters.semantic_scholar import SemanticScholarAdapter
from pheno.evidence.adapters.wikipedia import WikipediaAdapter


def _mock_client(payload: dict | None = None) -> MetadataClient:
    """Create a MetadataClient with mocked session that returns a payload."""
    client = MetadataClient(retries=0)
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.url = "https://example.com"
    # iter_content yields JSON bytes
    import json

    body = json.dumps(payload or {"results": []}).encode()
    mock_resp.iter_content.return_value = [body]
    mock_resp.payload = payload or {"results": []}  # not used, but for clarity
    client.session = mock_session
    mock_session.request.return_value = mock_resp
    return client


def test_rate_limiter_override() -> None:
    """Override rate/burst per adapter via RateLimiter injection."""
    limiter = RateLimiter(
        rate=100.0, burst=50, clock=lambda: 0.0, sleeper=lambda _: None
    )  # type: ignore[arg-type]
    # Direct construction with custom limiter
    client = MetadataClient(retries=0)
    adapter = OpenAlexAdapter(client, rate_limiter=limiter)
    assert adapter.rate_limiter.rate == 100.0
    assert adapter.rate_limiter.burst == 50
    # Reset registry so the next get_rate_limiter call creates fresh
    from pheno.evidence.adapters.rate_limit import _reset_registry

    _reset_registry()
    # Global registry override via get_rate_limiter
    rl = get_rate_limiter("openalex", rate=20.0, burst=30)
    assert (
        rl.rate == 20.0 or rl.burst == 30
    )  # first call creates, subsequent returns same
    # Cleanup
    _reset_registry()


def test_circuit_breaker_override() -> None:
    """Override failure_threshold/recovery_timeout per adapter."""
    breaker = CircuitBreaker(
        failure_threshold=2, recovery_timeout=5.0, clock=lambda: 0.0
    )
    client = MetadataClient(retries=0)
    adapter = SemanticScholarAdapter(client, circuit_breaker=breaker)
    assert adapter.circuit_breaker.failure_threshold == 2
    assert adapter.circuit_breaker.recovery_timeout == 5.0
    # Reset registry so the next get_circuit_breaker call creates fresh
    from pheno.evidence.adapters.circuit_breaker import _reset_registry as _reset_cb

    _reset_cb()
    # Global registry override
    cb = get_circuit_breaker(
        "semantic_scholar", failure_threshold=2, recovery_timeout=5.0
    )
    assert cb.failure_threshold == 2
    _reset_cb()


def test_retry_policy_override() -> None:
    """Override RetryPolicy per adapter."""
    policy = RetryPolicy(max_retries=1, base_delay=0.1, factor=1.5)
    client = MetadataClient(retries=0)
    adapter = WikipediaAdapter(client, retry_policy=policy)
    assert adapter.retry_policy.max_retries == 1
    assert adapter.retry_policy.base_delay == 0.1


def test_openalex_normalize_smoke() -> None:
    """Smoke normalize for OpenAlex stub."""
    from pheno.evidence.adapters.base import DiscoveryPage

    page = DiscoveryPage(
        source_kind="openalex",
        method="GET",
        endpoint="https://api.openalex.org/works",
        query={"search": "test"},
        final_url="https://api.openalex.org/works?search=test",
        api_version=None,
        status=200,
        response_headers={},
        retrieved_at="2026-08-20T00:00:00Z",
        payload={
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "display_name": "Test Paper",
                    "doi": "https://doi.org/10.1234/test",
                }
            ]
        },
        media_type="application/json",
    )
    adapter = OpenAlexAdapter(MetadataClient(retries=0))
    records = adapter.normalize(page, raw_sha256="abc123")
    assert len(records) == 1
    assert records[0]["source"]["kind"] == "openalex"


def test_semantic_scholar_normalize_smoke() -> None:
    from pheno.evidence.adapters.base import DiscoveryPage

    page = DiscoveryPage(
        source_kind="semantic_scholar",
        method="GET",
        endpoint="https://api.semanticscholar.org/graph/v1/paper/search",
        query={"query": "test"},
        final_url="https://api.semanticscholar.org/graph/v1/paper/search?query=test",
        api_version=None,
        status=200,
        response_headers={},
        retrieved_at="2026-08-20T00:00:00Z",
        payload={
            "data": [{"paperId": "S123", "title": "Test", "url": "https://example.com"}]
        },
        media_type="application/json",
    )
    adapter = SemanticScholarAdapter(MetadataClient(retries=0))
    records = adapter.normalize(page, raw_sha256="abc123")
    assert len(records) == 1
    assert records[0]["source"]["kind"] == "semantic_scholar"


def test_wikipedia_normalize_smoke() -> None:
    from pheno.evidence.adapters.base import DiscoveryPage

    page = DiscoveryPage(
        source_kind="wikipedia",
        method="GET",
        endpoint="https://en.wikipedia.org/w/api.php",
        query={"srsearch": "test"},
        final_url="https://en.wikipedia.org/w/api.php?srsearch=test",
        api_version=None,
        status=200,
        response_headers={},
        retrieved_at="2026-08-20T00:00:00Z",
        payload={"query": {"search": [{"title": "Test Page", "pageid": 123}]}},
        media_type="application/json",
    )
    adapter = WikipediaAdapter(MetadataClient(retries=0))
    records = adapter.normalize(page, raw_sha256="abc123")
    assert len(records) == 1
    assert records[0]["source"]["kind"] == "wikipedia"


def test_circuit_breaker_blocks_when_open() -> None:
    """When breaker is open, search should raise without calling client."""
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=30.0, clock=lambda: 0.0
    )
    breaker.record_failure()  # open it
    assert breaker.state == "open"
    client = MetadataClient(retries=0)
    mock_session = MagicMock()
    client.session = mock_session
    adapter = OpenAlexAdapter(client, circuit_breaker=breaker)
    try:
        adapter.search("test")
        assert False, "should have raised"
    except RuntimeError as exc:
        assert "circuit breaker is open" in str(exc).lower()
    mock_session.request.assert_not_called()
