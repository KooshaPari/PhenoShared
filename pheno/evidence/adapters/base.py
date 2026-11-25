"""Common bounded HTTP and normalization primitives for source adapters."""

from __future__ import annotations

import functools
import json
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar
from urllib.parse import urlparse

import requests

from ..contracts import make_record_id

F = TypeVar("F", bound=Callable[..., Any])


ADAPTER_VERSION = "pheno-evidence-adapters/1"

_ALLOWED_HOSTS = {
    "hf": {"huggingface.co"},
    "modelscope": {"modelscope.cn"},
    "github": {"api.github.com"},
    "arxiv": {"export.arxiv.org"},
    "reddit": {"oauth.reddit.com", "www.reddit.com"},
    "openalex": {"api.openalex.org"},
    "semantic_scholar": {"api.semanticscholar.org"},
    "wikipedia": {"en.wikipedia.org"},
}

_SAFE_HEADER_NAMES = {
    "content-type",
    "etag",
    "last-modified",
    "retry-after",
    "x-github-api-version-selected",
    "x-github-request-id",
    "x-modelscope-api-name",
    "x-modelscope-api-version",
    "x-powered-by",
    "x-request-id",
}
_SAFE_HEADER_PREFIXES = ("ratelimit", "x-ratelimit")


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with jitter for evidence adapters.

    Defaults satisfy WBS-PERT v0.10 task 62: max_retries 3, base 1.0, factor 2.0.
    Uses stdlib ``time.sleep`` + ``random`` only (no tenacity dep).
    """

    max_retries: int = 3
    base_delay: float = 1.0
    factor: float = 2.0
    jitter: bool = True
    max_delay: float = 30.0
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)

    def __post_init__(self) -> None:
        if (
            self.max_retries < 0
            or self.base_delay <= 0
            or self.factor < 1.0
            or self.max_delay <= 0
        ):
            raise ValueError("invalid retry policy bounds")


DEFAULT_RETRY_POLICY = RetryPolicy()


def is_retryable_status(
    status: int, policy: RetryPolicy = DEFAULT_RETRY_POLICY
) -> bool:
    """Return True when an HTTP status should be retried."""
    return status in policy.retry_on_status


def is_retryable_exception(
    exc: BaseException, policy: RetryPolicy = DEFAULT_RETRY_POLICY
) -> bool:
    """Return True for transient transport errors."""
    # requests exposes these as subclasses of RequestException / IOError.
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(exc, requests.HTTPError):
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
        if isinstance(status, int) and status in policy.retry_on_status:
            return True
    return False


def compute_retry_delay(
    attempt: int,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    response: Any | None = None,
) -> float:
    """Exponential backoff ``base * factor**attempt`` with optional jitter.

    Honors ``Retry-After`` when present on the response (cap at max_delay).
    ``attempt`` is zero-based (0 = first retry after the initial failure).
    """
    raw = None
    if response is not None:
        try:
            headers = getattr(response, "headers", None)
            if headers is not None:
                raw = headers.get("Retry-After")
        except Exception:
            raw = None
    if raw is not None:
        try:
            return min(max(float(raw), 0.0), policy.max_delay)
        except (ValueError, TypeError):
            pass
    delay = policy.base_delay * (policy.factor**attempt)
    if policy.jitter:
        delay += random.random() * policy.base_delay  # nosec B311
    return min(delay, policy.max_delay)


def with_retry(
    policy: RetryPolicy | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[F], F]:
    """Decorator: retry the wrapped callable with exponential backoff.

    Retries on retryable HTTP statuses (via ``requests.HTTPError``) and on
    ``ConnectionError``/``Timeout``. Non-retryable exceptions propagate
    immediately.
    """

    resolved = policy or DEFAULT_RETRY_POLICY

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(resolved.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except BaseException as exc:  # noqa: BLE001 - must classify
                    last_exc = exc
                    if attempt >= resolved.max_retries or not is_retryable_exception(
                        exc, resolved
                    ):
                        raise
                    resp = getattr(exc, "response", None)
                    delay = compute_retry_delay(attempt, resolved, resp)
                    sleep(delay)  # noqa: PLW1510 - intentionally blocking
            assert last_exc is not None  # nosec B101
            raise last_exc  # pragma: no cover - loop always raises earlier

        return wrapper  # type: ignore[return-value]

    return decorator


class RetryMixin:
    """Mixin exposing :meth:`retry_delay` for adapter classes."""

    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY

    def retry_delay(self, attempt: int, response: Any | None = None) -> float:
        return compute_retry_delay(attempt, self.retry_policy, response)


@dataclass(frozen=True)
class DiscoveryPage:
    """One adapter HTTP fetch result (URL, payload, headers, timestamps)."""

    source_kind: str
    method: str
    endpoint: str
    query: Mapping[str, Any]
    final_url: str
    api_version: str | None
    status: int
    response_headers: Mapping[str, str]
    retrieved_at: str
    payload: Any
    media_type: str
    incomplete: bool = False


class MetadataClient:
    """Bounded, retrying client restricted to approved metadata hosts."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 20.0,
        max_response_bytes: int = 8 * 1024 * 1024,
        retries: int = 3,
        retry_policy: RetryPolicy | None = None,
        user_agent: str = "pheno-harness-evidence/1 (+metadata-only)",
    ) -> None:
        if timeout <= 0 or max_response_bytes < 1 or retries < 0:
            raise ValueError("invalid metadata client bounds")
        self.session = session or requests.Session()
        self.timeout = float(timeout)
        self.max_response_bytes = int(max_response_bytes)
        self.retries = int(retries)
        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=self.retries,
            base_delay=DEFAULT_RETRY_POLICY.base_delay,
            factor=DEFAULT_RETRY_POLICY.factor,
            jitter=DEFAULT_RETRY_POLICY.jitter,
            max_delay=DEFAULT_RETRY_POLICY.max_delay,
            retry_on_status=DEFAULT_RETRY_POLICY.retry_on_status,
        )
        self.user_agent = user_agent
        self._last_request_at: dict[str, float] = {}

    @staticmethod
    def _check_url(source_kind: str, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("metadata endpoints must use HTTPS")
        if (parsed.hostname or "").lower() not in _ALLOWED_HOSTS.get(
            source_kind, set()
        ):
            raise ValueError(f"metadata endpoint host is not allowed for {source_kind}")

    @staticmethod
    def _safe_headers(headers: Mapping[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in headers.items():
            normalized = str(key).lower()
            if normalized in _SAFE_HEADER_NAMES or normalized.startswith(
                _SAFE_HEADER_PREFIXES
            ):
                result[normalized] = str(value)
        return result

    def _pace(self, source_kind: str, minimum_interval: float) -> None:
        if minimum_interval <= 0:
            return
        previous = self._last_request_at.get(source_kind)
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0:
                time.sleep(remaining)

    @staticmethod
    def _retry_delay(response: Any, attempt: int) -> float:
        """Compat shim: delegates to :func:`compute_retry_delay`."""
        return compute_retry_delay(attempt, DEFAULT_RETRY_POLICY, response)

    def request(
        self,
        *,
        source_kind: str,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        minimum_interval: float = 0.0,
        api_version: str | None = None,
    ) -> DiscoveryPage:
        """Make one bounded GET/POST request and return a DiscoveryPage."""
        self._check_url(source_kind, url)
        verb = method.upper()
        if verb not in {"GET", "POST"}:
            raise ValueError("metadata client supports GET and OAuth POST only")
        request_headers = {"User-Agent": self.user_agent}
        request_headers.update(dict(headers or {}))
        response: Any = None
        last_exc: Exception | None = None
        for attempt in range(self.retry_policy.max_retries + 1):
            self._pace(source_kind, minimum_interval)
            try:
                response = self.session.request(
                    verb,
                    url,
                    params=dict(params or {}),
                    data=dict(data or {}) if data is not None else None,
                    headers=request_headers,
                    timeout=self.timeout,
                    stream=True,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt >= self.retry_policy.max_retries:
                    raise
                time.sleep(compute_retry_delay(attempt, self.retry_policy, None))
                continue
            self._last_request_at[source_kind] = time.monotonic()
            last_exc = None
            if (
                is_retryable_status(int(response.status_code), self.retry_policy)
                and attempt < self.retry_policy.max_retries
            ):
                try:
                    response.close()
                except Exception:  # nosec B110
                    pass
                time.sleep(compute_retry_delay(attempt, self.retry_policy, response))
                continue
            break
        if response is None:
            assert last_exc is not None  # nosec B101
            raise last_exc
        assert response is not None  # nosec B101
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > self.max_response_bytes:
                response.close()
                raise ValueError(
                    f"metadata response exceeds {self.max_response_bytes} bytes"
                )
            chunks.append(chunk)
        body = b"".join(chunks)
        content_type = str(
            response.headers.get("Content-Type", "application/octet-stream")
        )
        if "json" in content_type.lower():
            try:
                payload: Any = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("metadata endpoint returned invalid JSON") from exc
        else:
            payload = body.decode("utf-8", errors="replace")
        final_url = str(getattr(response, "url", url))
        response.close()
        return DiscoveryPage(
            source_kind=source_kind,
            method=verb,
            endpoint=url,
            query=dict(params or data or {}),
            final_url=final_url,
            api_version=api_version,
            status=int(response.status_code),
            response_headers=self._safe_headers(response.headers),
            retrieved_at=datetime.now(UTC).isoformat(),
            payload=payload,
            media_type=content_type.split(";", 1)[0].strip(),
        )


def normalized_record(
    *,
    page: DiscoveryPage,
    raw_sha256: str,
    canonical_name: str,
    canonical_url: str,
    revision: str,
    mutable: bool,
    evidence_class: str = "V",
    aliases: list[str] | None = None,
    released_at: str | None = None,
    declared_licenses: list[str] | None = None,
    license_urls: list[str] | None = None,
    model: Mapping[str, Any] | None = None,
    notes: list[str] | None = None,
    compliance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a strict registry record from one adapter observation."""

    licenses = [value for value in (declared_licenses or []) if value]
    return {
        "schema_version": "pheno.evidence.v1",
        "record_id": make_record_id(page.source_kind, canonical_name, revision),
        "retrieved_at": page.retrieved_at,
        "source": {
            "kind": page.source_kind,
            "url": canonical_url,
            "revision": revision,
            "evidence_class": evidence_class,
            "raw_sha256": raw_sha256,
        },
        "subject": {
            "canonical_name": canonical_name,
            "aliases": aliases or [],
            "released_at": released_at,
            "license": licenses[0] if licenses else None,
        },
        "model": dict(model) if model is not None else None,
        "artifacts": [],
        "runtime_support": [],
        "benchmark_claims": [],
        "gates": {
            "metadata_only": True,
            "license": "review_required",
            "execution": "blocked",
        },
        "discovery": {
            "method": page.method,
            "endpoint": page.endpoint,
            "query": dict(page.query),
            "final_url": page.final_url,
            "adapter_version": ADAPTER_VERSION,
            "api_version": page.api_version,
            "status": page.status,
            "response_headers": dict(page.response_headers),
            "incomplete": page.incomplete,
        },
        "resolved": {"revision": revision, "mutable": mutable},
        "license": {
            "declared": licenses,
            "source_urls": license_urls or [],
            "verified": False,
            "caveats": [
                "Publisher or repository metadata is not independent legal verification."
            ],
        },
        "quality": {
            "incomplete": page.incomplete or mutable,
            "confidence": "medium" if mutable else "high",
            "needs_revalidation_at": None,
        },
        "compliance": dict(
            compliance
            or {
                "retention_class": "durable_metadata",
                "purge_after": None,
                "tombstoned_at": None,
            }
        ),
        "notes": notes or [],
    }


def payload_items(payload: Any, *paths: tuple[str, ...]) -> list[Mapping[str, Any]]:
    """Extract the first list-of-objects found at one of several API paths."""

    for path in paths:
        value = payload
        for key in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


__all__ = [
    "ADAPTER_VERSION",
    "DEFAULT_RETRY_POLICY",
    "DiscoveryPage",
    "MetadataClient",
    "RetryMixin",
    "RetryPolicy",
    "compute_retry_delay",
    "is_retryable_exception",
    "is_retryable_status",
    "normalized_record",
    "payload_items",
    "with_retry",
]
