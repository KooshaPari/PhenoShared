# Evidence Adapters — Operator Runbook

> v0.10 tasks 69-75 — retry, rate limit, circuit breaker

## Overview

Evidence adapters discover metadata only (no artifact download) via a shared
`MetadataClient` and per-adapter normalization. All adapters share the same
resilience primitives: retry, rate limiting, and circuit breaking.

Adapters (canonical 9 for v0.12 Gate 75 extended):

- `arxiv` — `export.arxiv.org`
- `github` — `api.github.com`
- `huggingface` — `huggingface.co`
- `modelscope` — `modelscope.cn`
- `reddit` — `oauth.reddit.com` / `www.reddit.com`
- `local_corpus` — local filesystem (no network; limit/breaker no-ops but registered for uniformity)
- `openalex` — `api.openalex.org` (v0.12 stub — task 3)
- `semantic_scholar` — `api.semanticscholar.org` (v0.12 stub — task 4)
- `wikipedia` — `en.wikipedia.org` (v0.12 stub — task 4)

## Retry Policy

- **Implementation:** `pheno/evidence/adapters/base.py` — `RetryPolicy`, `with_retry`, `MetadataClient`.
- **Defaults (WBS-PERT v0.10 task 62):** `max_retries=3`, `base_delay=1.0s`, `factor=2.0`, `jitter=True`, `max_delay=30.0s`.
- **Delay:** `base * factor**attempt + jitter` (attempt zero-based, capped at `max_delay`). Honors `Retry-After` header when present (capped).
- **Retry on:** `429, 500, 502, 503, 504` and transient `ConnectionError`/`Timeout`.
- **No retry on:** other `4xx` (e.g. `400, 401, 403, 404`) — fails fast.
- **Decorator:** `@with_retry(policy, sleep=time.sleep)` for ad-hoc functions.
- **Client loop:** `MetadataClient.fetch` / `request` retries inline with `compute_retry_delay`; respects `Retry-After`.

```
attempt 0: 1s (+ jitter)   # e.g. 1.0–2.0s
attempt 1: 2s (+ jitter)   # 2.0–3.0s
attempt 2: 4s (+ jitter)   # 4.0–5.0s  (capped 30s)
```

## Rate Limit

- **Implementation:** `pheno/evidence/adapters/rate_limit.py` — `RateLimiter` (token bucket).
- **Defaults:** `5 req/s`, `burst 10` per adapter.
- **Mechanism:** `time.monotonic` + `threading.Lock`, no external dep. Bucket refills at `rate`; `try_acquire()` is non-blocking, `acquire()` sleeps the deficit (`needed / rate`) outside the lock.
- **Per-adapter instance:** `get_rate_limiter("arxiv")` etc. Registry is process-global and thread-safe. Test helper `_reset_registry()` clears it.
- **Injection for tests:** `RateLimiter(rate, burst, clock=..., sleeper=...)` to mock time.

## Circuit Breaker

- **Implementation:** `pheno/evidence/adapters/circuit_breaker.py` — `CircuitBreaker`.
- **Policy:** `closed → open` on **5 consecutive failures**, `half-open after 30s`, `half-open → open` on failure else `→ closed` on success.
- **Mechanism:** `time.monotonic` + `threading.Lock`.
- **API:** `can_execute()`, `record_success()`, `record_failure()`, `state` (`closed|open|half_open`), `failure_count`.
- **Per-adapter instance:** `get_circuit_breaker("github")` etc. Same registry pattern as rate limit.

## Per-Adapter Config Table

| Adapter | Host(s) | Retry (max/base×factor) | Rate (req/s / burst) | Breaker (failures / window) | Notes |
|---|---|---|---|---|---|
| `arxiv` | `export.arxiv.org` | 3 / 1s×2 | 5 / 10 | 5 / 30s | Atom XML, pacing via client `minimum_interval` |
| `github` | `api.github.com` | 3 / 1s×2 | 5 / 10 | 5 / 30s | `X-GitHub-Api-Version: 2026-03-10`, respects `Retry-After` |
| `huggingface` | `huggingface.co` | 3 / 1s×2 | 5 / 10 | 5 / 30s | Hub search, allowlist host |
| `modelscope` | `modelscope.cn` | 3 / 1s×2 | 5 / 10 | 5 / 30s | CN endpoint |
| `reddit` | `oauth.reddit.com`, `www.reddit.com` | 3 / 1s×2 | 5 / 10 | 5 / 30s | OAuth + public fallback |
| `local_corpus` | (local) | 3 / 1s×2 | 5 / 10 | 5 / 30s | No network; limiter/breaker registered for uniformity |
| `openalex` | `api.openalex.org` | 3 / 1s×2 | 5 / 10 | 5 / 30s | Works API, `search` param, pacing 0.2s |
| `semantic_scholar` | `api.semanticscholar.org` | 3 / 1s×2 | 5 / 10 | 5 / 30s | Graph API, `query/offset/limit` |
| `wikipedia` | `en.wikipedia.org` | 3 / 1s×2 | 5 / 10 | 5 / 30s | MediaWiki `list=search`, pacing 0.5s |

All per-adapter tunables can be overridden at construction:

```python
from pheno.evidence.adapters.rate_limit import get_rate_limiter
from pheno.evidence.adapters.circuit_breaker import get_circuit_breaker
from pheno.evidence.adapters.base import RetryPolicy, MetadataClient

limiter = get_rate_limiter("arxiv", rate=5.0, burst=10)
breaker = get_circuit_breaker("arxiv", failure_threshold=5, recovery_timeout=30.0)

client = MetadataClient(retry_policy=RetryPolicy(max_retries=3, base_delay=1.0, factor=2.0))
```

## Verification (Gate 75)

Gate expects each adapter file to import the three primitives:

```bash
python -c "
import pathlib
for name in ['arxiv','github','huggingface','modelscope','reddit','local_corpus','openalex','semantic_scholar','wikipedia']:
    p = pathlib.Path(f'pheno/evidence/adapters/{name}.py')
    txt = p.read_text()
    print(name, 'retry' in txt.lower(), 'rate_limit' in txt, 'circuit_breaker' in txt)
"
```

Note: As of v0.12 tasks 3-4, `openalex`/`semantic_scholar`/`wikipedia` are stubs that import and wire all three primitives (retry decorator, rate limiter acquire, circuit breaker guard). Earlier tasks 69-75 had standalone modules with deferred wiring; Gate now expects all 9 to pass.

## Tests

- `tests/test_evidence_adapters_retry.py` — retry on 429, retry on 5xx, no retry on 4xx
- `tests/test_evidence_adapters_rate_limit.py` — within limit passes, over limit throttles
- `tests/test_evidence_adapters_circuit_breaker.py` — open after threshold, half-open recovery
- `tests/test_evidence_adapters_tuning.py` — v0.12 overrides for rate/breaker thresholds and openalex/semantic_scholar/wikipedia smoke

Run:

```bash
pytest -q tests/test_evidence_adapters_retry.py tests/test_evidence_adapters_rate_limit.py tests/test_evidence_adapters_circuit_breaker.py
C:\Users\koosh\AppData\Local\Temp\mypy_21_venv\Scripts\python.exe -m mypy --no-incremental --cache-dir=%TEMP%\mypy_p4_69 --error-summary pheno/evidence/adapters/rate_limit.py pheno/evidence/adapters/circuit_breaker.py
```
