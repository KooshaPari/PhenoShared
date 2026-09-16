# Phase 4 Adapter Audit — Tasks 61–62 (WBS-PERT v0.10)

> **Scope:** task 61 audit across adapters under `pheno/evidence/adapters/`.
> HEAD `81cd975` (branch `wip/2026-07-28-pheno-harness-m80-d76`), `base.py` at `7/14 9906 B`.
> Does **not** block on Phase 3 gate (task 60); Phase 3 worker `63acef34` runs 41–60 concurrently.

## Inventory (actual disk, 2026-08-19)

`Glob pheno/evidence/adapters/*.py` returns 8 files:

| Adapter file | `kind` | HTTP? | Lines | Endpoint |
|---|---|---|---|---|
| `base.py` | — | shared | 206 | — |
| `arxiv.py` | `arxiv` | GET | 163 | `https://export.arxiv.org/api/query` |
| `github.py` | `github` | GET | 131 | `https://api.github.com/search/repositories` + `/repos/{owner}/{repo}/commits/{ref}` |
| `huggingface.py` | `hf` | GET | ~420 | `https://huggingface.co/api/models` + `/resolve/{sha}/config.json` |
| `modelscope.py` | `modelscope` | GET | 163 | `https://modelscope.cn/openapi/v1/models` |
| `reddit.py` | `reddit` | GET | 130 | `https://oauth.reddit.com/search` |
| `local_corpus.py` | `local_corpus` | local scan | 84 | `local://corpus-scan` |
| `__init__.py` | — | — | 14 | re-exports |

**DAG v0.10 spec lists** `arxiv, github, hf, openalex, semantic_scholar, wikipedia` (6). Disk diverges:
- `huggingface.py` == `hf` (name mismatch only).
- `modelscope.py` + `reddit.py` + `local_corpus.py` exist on disk but are not in the DAG’s 6.
- `openalex.py`, `semantic_scholar.py`, `wikipedia.py` do **not** exist on disk — gap noted for tasks 66–68 (they will be created or scoped out).

Audit covers the 6 HTTP adapters on disk: **arxiv, github, huggingface(hf), modelscope, reddit** + base; `local_corpus` is local-only and assessed separately.

## Error-handling matrix

| Concern | `base.MetadataClient` | `arxiv` | `github` | `huggingface` | `modelscope` | `reddit` | `local_corpus` |
|---|---|---|---|---|---|---|---|
| **Timeout** | `timeout=20.0` passed to `session.request(..., timeout=...)`, validated `>0` | delegates | delegates | delegates | delegates | delegates | N/A (local) |
| **Max response** | `max_response_bytes=8 MiB`, streamed `iter_content(64K)` + hard fail | delegates | delegates | delegates | delegates | delegates | N/A |
| **Retry count** | `retries=3` field, loop `range(retries+1)` | inherits | inherits | inherits | inherits | inherits | none |
| **Retry trigger** | **429 only** (`status_code != 429 → break`) | — | — | only 404 swallowed in `hydrate_config` | — | — | — |
| **5xx / 502/503/504** | **no retry** | — | — | — | — | — | — |
| **ConnectionError / Timeout** | **no retry**, exception propagates unhandled | — | — | — | — | — | — |
| **Retry backoff** | `_retry_delay`: `Retry-After` (cap 30s) else `min(2**attempt + random(), 30)` (429 only) | — | — | — | — | — | — |
| **Jitter** | `random.random()` additive in `_retry_delay` | — | — | — | — | — | — |
| **Pacing / min_interval** | `_pace` via `time.monotonic` + `time.sleep(remaining)` | `minimum_interval=3.0` | default 0 | default 0 | default 0 | default 0 | — |
| **Host allowlist** | `_ALLOWED_HOSTS` + `_check_url` enforces HTTPS + hostname | inherits | inherits | inherits | inherits | inherits | — |
| **Header filtering** | `_safe_headers` allowlist + prefix | — | — | — | — | — | — |
| **try/except at adapter** | — | validation raises `ValueError` only; no `try/except` around `client.request` | same | `hydrate_config` catches `requests.HTTPError` only for 404, re-raises rest | validation only | `access_token` check only | `ValueError` if not a dir |
| **normalize errors** | — | `_root` catches `ParseError → ValueError`, skips empty ids | returns `[]` on non-Mapping payload | skips non-matching `model_id`, `model_anomaly` flag | skips empty canonical_name | skips missing fullname/permalink | raises on non-dict payload |
| **`incomplete` semantics** | `DiscoveryPage.incomplete` bool | `totalResults` check / exact-one entry check | `incomplete_results` flag | `sha` pinning | always `True` (needs hydration) | always `True` (needs revalidation, 48h) | always `False` |

### Inconsistencies (actionable)

1. **Narrow retry.** Only 429 is retried. Transient 500/502/503/504 and `ConnectionError`/`Timeout` are not — the most common flake on Hub/GitHub.
2. **No exponential backoff for non-429.** Task 62 asks for `max_retries 3, base 1.0, factor 2.0` with jitter for all retryable failures. The current `_retry_delay` is 429-only.
3. **No per-adapter policy.** All adapters share one `retries` int; there is no `RetryPolicy` dataclass, no decorator/mixin, no per-kind interval/RetryPolicy override.
4. **No `Retry-After` for 5xx / connection errors.** Only read from 429 responses; new policy must fall back to `base*factor**attempt`.
5. **Inconsistent `minimum_interval`.** Only `arxiv` paces (3.0s, per arXiv ToS); GitHub/Hub/ModelScope/Reddit use 0. No `rate_limit.py` yet (task 69).
6. **Inconsistent error surfaces.** Adapters raise `ValueError` for bad inputs but do not wrap/normalize transport errors. A unified `AdapterError` / `RetryExhausted` would aid callers.
7. **No circuit breaker.** No `circuit_breaker.py` (task 72); repeated failures do not open a breaker.
8. **No timeout overrides.** `MetadataClient.timeout` is global; adapters cannot request a tighter/looser timeout per endpoint.
9. **Missing adapters.** `openalex`, `semantic_scholar`, `wikipedia` absent — tasks 66–68 will either add them or formally descope in `docs/EVIDENCE_ADAPTERS.md` (task 74).

## Mypy baseline (pinned venv, `pheno` slice)

Command (per task spec):

```
C:\Users\koosh\AppData\Local\Temp\mypy_21_venv\Scripts\python.exe -m mypy --no-incremental --cache-dir=%TEMP%\mypy_p4 --error-summary pheno
```

From repo root `C:\Users\koosh\pheno-harness` at this HEAD:

- **Before tasks 61–62:** `9 errors in 3 files (checked 35 source files)` — far lower than the `185` quoted in the parent-task context because that 185 aggregates the broader `mypy-inventory.md` (371 across `bench/ pheno/ verifier/ eval/`) and the task’s “pheno/* rest” bucket. The 9 break down as:
  - `pheno/model_manager.py:18` — `pheno.runtime_admission has no attribute validate_runtime_admission` (1)
  - `pheno/evidence/telemetry.py:800/802/809/811/812` — `arg-type` / `list-item` / `return-value` on `int | str | None` (7)
  - `pheno/evidence/aggregate_contracts.py:1540` — `Any | None → dict[str,Any]` (1)
- `pheno/evidence/adapters/*` is **0 errors** in this slice at HEAD (adapters are clean; the pheno 185/92 bucket in the task description reflects the pre-Phase-3 inventory before tasks 41–60 narrowed `eval/`/`verifier/` — not a regression).

Touched-file delta for 61–62 will be measured on `pheno/evidence/adapters/base.py` + new `docs/plans/phase4-adapter-audit.md` only; full-pheno re-baseline is reported in the commit note.

## Task 62 design (what this commit adds to `base.py`)

Constraint: prefer stdlib (`time.sleep + random`) over `tenacity`; `tenacity` is not in `pyproject.toml` deps.

Added (no new dep):

- `RetryPolicy` (frozen dataclass): `max_retries=3, base_delay=1.0, factor=2.0, jitter=True, max_delay=30.0, retry_on_status=(429,500,502,503,504)`. Frozen so adapters can share a global default.
- `compute_retry_delay(attempt, policy, response=None)` — respects `Retry-After` when present, else `min(base*factor**attempt + jitter, max_delay)`. Jitter is `random.uniform(0, base)`-style via `random.random()` additive, matching the existing helper.
- `is_retryable_status(status, policy)` / `is_retryable_exception(exc, policy)` — `ConnectionError`/`Timeout` + `HTTPError` with retryable status.
- `with_retry(policy)` decorator and `RetryMixin` for adapter classes that want method-level retry without touching `MetadataClient`.
- `MetadataClient` extended: `retry_policy: RetryPolicy | None = None` ctor arg, `retries` stays for compat (when `retry_policy is None` it synthesizes one). `request()` now retries on 429 **and** 5xx and on `ConnectionError`/`Timeout`, using `compute_retry_delay`. `response.close()` is guarded. `_retry_delay` is retained as a thin shim over `compute_retry_delay` for compat.
- `__all__` gains `RetryPolicy`, `compute_retry_delay`, `with_retry`.

Out of scope for 61–62 (follow-ups 63–75): applying the policy per adapter file (63–68), `rate_limit.py` (69), `circuit_breaker.py` (72), adapter tests (70–71,73), `docs/EVIDENCE_ADAPTERS.md` (74), gate (75). Those will land in subsequent atomics.

## Commit

- `docs/plans/phase4-adapter-audit.md` (this file) — task 61.
- `pheno/evidence/adapters/base.py` — task 62 (retry policy).
- Commit subject: `feat(evidence): Phase 4 adapter audit + base retry policy tasks 61-62`.

## Follow-ups

- Tasks 63–68: wire `RetryPolicy` + `minimum_interval` per adapter; add missing `openalex`/`semantic_scholar`/`wikipedia` or descope with rationale.
- Tasks 69/72: `rate_limit.py` + `circuit_breaker.py`.
- Re-baseline `mypy --no-incremental` on `pheno` after 61–62; target is `9 → 9` (no new errors) — the broader `185 → lower` will come from adapter wiring + `pheno/preservation.py` etc. in later phases.

*Generated for WBS-PERT v0.10 Phase 4, branch `wip/2026-07-28-pheno-harness-m80-d76`.*
