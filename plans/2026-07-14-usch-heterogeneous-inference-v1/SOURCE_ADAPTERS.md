# Source adapter contract

Cutoff: 2026-07-14. Search is discovery only. Every adapter hydrates a bounded
result where possible, resolves an immutable revision, records the final wire
URL, and leaves mutable observations execution-blocked.

## Hugging Face

- Discovery: `GET https://huggingface.co/api/models`; use the official
  [HfApi search contract](https://huggingface.co/docs/huggingface_hub/main/en/package_reference/hf_api).
- Relevant SDK filters include `author`, `search`, `pipeline_tag`,
  `num_parameters`, inference/provider fields, sort, limit, `expand`, `full`,
  `cardData`, and `fetch_config`. `expand` cannot be combined with the three
  latter expansion modes; record the final SDK-translated URL.
- The implemented bounded hydration calls `/api/models/{owner}/{repo}`, accepts
  only a returned full commit `sha`, then fetches only literal `config.json` at
  that SHA. It rejects cross-host redirects, malformed identities, and
  implausible parameter totals; an HTTP 404 retains the immutable detail as
  incomplete. Repository-tree/card/LICENSE inventory remains a later license
  gate and does not fetch weight blobs.
- Rate limits use five-minute buckets with `RateLimit`, `RateLimit-Policy`, and
  429 reset information; published quotas can change. See the official
  [rate-limit documentation](https://huggingface.co/docs/hub/en/rate-limits).
- Card license tags are publisher metadata. `license: other`, derived quants,
  missing NOTICE files, and gated terms require card plus LICENSE/NOTICE hashes
  and `license.verified: false` until reviewed.

## ModelScope

- Canonical discovery endpoint:
  `GET https://modelscope.cn/openapi/v1/models`.
- Current parameters are `search`, `owner`, `sort`, one-based `page_number`,
  `page_size`, and `filter.task|library|model_type|custom_tag|license|deploy`.
  The official client enforces `page_number * page_size <= 3000`; use `owner`,
  not legacy `author`, and `page_size`, not HF-style `limit`.
- Detail: `/openapi/v1/models/{owner}/{repo_name}`. The official
  [modelscope-hub client](https://github.com/modelscope/modelscope_hub) may fall
  back to legacy APIs, so provenance records the actual URL and method.
- No reliable numeric public quota was found. Honor 429/`Retry-After`, back off
  with jitter, and capture gateway/rate headers rather than inferring a quota.
- A response hash is not a repository revision. If detail/revision APIs do not
  expose an immutable ID, retain `resolved.mutable: true`.

## GitHub

- Discovery: `GET https://api.github.com/search/repositories` with
  `Accept: application/vnd.github+json` and current API header
  `X-GitHub-Api-Version: 2026-03-10`.
- `q` is required; `sort`, `order`, `per_page <= 100`, and `page` are explicit.
  Search exposes at most the first 1,000 results, caps query text/operators,
  and can return `incomplete_results=true`; partition broad queries instead of
  pretending a partial ranking is exhaustive. See the official
  [repository-search endpoint](https://docs.github.com/en/rest/search/search).
- Hydrate repository metadata, resolve `/commits/{ref}` to a commit SHA, then
  hash releases/tags/license/tree metadata. Check recursive-tree truncation.
- Search/core quotas are separate; record `/rate_limit` and response headers
  and honor secondary limits. Stars, ranks, releases, and default branches are
  timestamped observations; the commit SHA is identity.

## arXiv

- Discovery/detail: `GET` or `POST https://export.arxiv.org/api/query` with
  `search_query`, version-aware `id_list`, zero-based `start`, `max_results`,
  `sortBy`, and `sortOrder`. See the official
  [API manual](https://info.arxiv.org/help/api/user-manual.html).
- Audited paper resolution uses one validated modern base/versioned identifier
  per `id_list` request, never guessed title/search syntax. The response must
  contain exactly one entry: a base-ID request may resolve to a version of that
  same base, while a versioned request must return that exact version. Each ID
  is paced and accounted independently, so one missing/mismatched paper cannot
  suppress later resolutions.
- Responses are Atom XML. Capture versioned IDs, authors, categories, DOI,
  dates, and links. An unversioned ID means latest/mutable.
- Across the user's machines, use one connection and at most one request every
  three seconds; cache repeated queries. For bulk metadata, use OAI-PMH.
- Descriptive metadata is CC0, but paper PDF/source copyright and license are
  separate from any associated code/model license.

## Reddit

- Reddit is class **A** anecdotal discovery only. It never changes a benchmark
  score or verified fact.
- OAuth plus a descriptive User-Agent is mandatory. Search uses
  `https://oauth.reddit.com/search` or `/r/{subreddit}/search`; `q <= 512`,
  `limit <= 100`, fullname cursors, and explicit sort/time filters. It searches
  posts, not global comments. See the official [OAuth API](https://www.reddit.com/dev/api/oauth).
- Eligible free clients currently receive 100 QPM averaged over ten minutes;
  consume `X-Ratelimit-*` headers. Unauthenticated use is blocked.
- Reddit requires deletion handling, prompt removal of deleted account/content
  references, and recommends purging stored user data within 48 hours. The
  [Data API terms](https://redditinc.com/policies/data-api-terms) also prohibit
  unlicensed AI training on user content.
- Therefore no immutable raw Reddit snapshot exists. Durable storage contains
  a paraphrased claim, fullname/permalink, observation/revalidation time, and
  tombstone state in a separate anecdote stream. Raw user text may exist only
  in a deletion-reconciled ephemeral cache; the current adapter leaves this
  source disabled.

## Local ChatGPT corpus

- Scan configured `ChatGPT-*.md` paths locally, hash bytes, and persist only
  content digest, basename, byte count, and modified time.
- Raw text and absolute paths remain outside the registry. Records are class
  **L**, useful for lineage and hypothesis generation; fresh primary evidence
  overrides dated factual claims.

## Admission invariant

The adapter layer has no model-download API and cannot mutate ADR 0005's locked
shortlist. Discovery records enter with `metadata_only: true`, license review
required, and execution blocked. A separate reviewed ADR must name the exact
model revision, artifact digest/size, license result, runtime/parser/template,
resource budget, validation subset, and rollback before any artifact is
acquired or served.
