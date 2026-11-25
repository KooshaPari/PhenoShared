# Experiment and discovery plan

## 1. Reproducible discovery pipeline

The existing repository mainly scrapes Hugging Face and OpenRouter snapshots.
The replacement design is a normalized evidence registry, not one giant search
script and not an unversioned list of links.

### Source adapters

| Source | Acquisition | Accepted role |
|---|---|---|
| Hugging Face | Hub API/search, model files/config, commit SHA, card, siblings/artifact sizes | Primary model/artifact registry. Use the official [Hub search guide](https://huggingface.co/docs/huggingface_hub/en/guides/search). |
| ModelScope | Official model search/API/docs, repository revision and license | Independent China-first discovery and artifact mirror. Start with [ModelScope model documentation](https://www.modelscope.cn/docs/models/intro). |
| GitHub | REST/GraphQL releases, tags, commit/code search, issues/PRs for current support | Runtime and implementation truth. Pin release/commit; an open PR is not support. |
| arXiv | Export API by category/query/author, version history, linked code | Paper discovery and revision tracking. Follow the official [API manual](https://info.arxiv.org/help/api/user-manual.html). |
| Reddit | OAuth/API and terms-compliant search into a separate anecdote store | Failure reports, thermals, odd hardware, and candidate discovery only. Never use votes or anecdotes as benchmark evidence; observe [Data API terms](https://redditinc.com/policies/data-api-terms). |
| Local ChatGPT exports | Hash, deduplicate, locally index metadata/sections; retain raw files outside public artifacts | Design lineage and hypothesis generation. Fresh primary sources override dated factual claims. |

### Canonical evidence record

Every observation should serialize the following fields; use append-only raw
snapshots plus derived normalized tables:

```yaml
record_id: <source>:<stable-id>:<revision>
retrieved_at: <UTC timestamp>
source:
  kind: hf|modelscope|github|arxiv|reddit|local_corpus
  url: <canonical URL>
  revision: <commit/tag/arxiv-version/content-hash>
  evidence_class: V|C|L|A
subject:
  canonical_name: <owner/name or paper id>
  aliases: []
  released_at: <known date or null>
  license: <SPDX/name/unknown>
model:
  architecture: <declared config>
  total_parameters: <integer or null>
  active_parameters: <integer or null>
  context_tokens: <integer or null>
  modalities: []
  mtp_or_draft: <description/null>
artifacts:
  - format: safetensors|gguf|mlx|onnx|engine
    quantization: <exact scheme>
    bytes: <integer>
    sha256_or_etag: <value>
runtime_support:
  - runtime: <name>
    version_or_commit: <pin>
    state: released|main|open_pr|fork|claimed|unsupported
    parser: <reasoning/tool parser/null>
benchmark_claims:
  - suite: <name+revision>
    score: <value>
    harness: <name/revision>
    attempts: <count/null>
    evidence_class: C|V
notes: []
```

The implemented `pheno.evidence.v1` envelope additionally requires the exact
request method, endpoint, ordered query, final wire URL, adapter/API version,
safe response/rate headers, HTTP status, immutable-or-mutable resolution flag,
publisher-declared license sources and verification state, completeness, and
retention class. These fields distinguish an SDK call from what actually
crossed the wire and prevent a response hash from masquerading as a repository
revision.

Reddit is a compliance exception. Raw title/body/comment content is never
written to the content-addressed store. Only allowlisted, paraphrased citation
metadata may enter the separate anecdote stream, with a live fullname/link,
observation time, 48-hour revalidation deadline, and tombstone state. The
adapter remains disabled until operator OAuth and deletion reconciliation are
configured.

Implementation checkpoint on 2026-07-14:

- `pheno/evidence/` contains strict contracts, secret redaction, bounded
  content-addressed storage, stale-lock recovery, separate anecdote events,
  benchmark gates, candidate evaluator locks, and six source adapters;
- `scripts/evidence_registry.py` defaults to planning, requires an explicit
  remote-metadata flag, and exposes no weight-download or shortlist-mutation
  operation;
- discovery reports use stable per-source operation IDs and partition every
  planned operation into `completed`, `failed`, or `skipped`; an individual
  resolution, search, hydration, or local scan failure cannot suppress later
  configured work. Reports classify errors without echoing raw exception text,
  credentials, or private local-corpus roots;
- `config/evidence_registry.yaml` defines versioned queries for Hugging Face,
  ModelScope, GitHub, arXiv, disabled Reddit, and the local corpus;
- audited arXiv IDs are also resolved directly with the API's `id_list`
  parameter. Exact-ID resolution is independent of broad/title search recall,
  validates returned base/version identity, and remains metadata-only;
- the validated metadata store includes all 49 configured local-corpus files,
  representing 47 unique cryptographic hashes, plus
  bounded HF/ModelScope/GitHub/arXiv observations and immutable detail/commit
  pins where the source returned them. Mutable search records remain visibly
  incomplete and execution-blocked.

The registry is an append-only observation history, not a set with one blob per
logical source revision. Validation therefore reports stable `record_id`
identities separately from immutable normalized-content versions. After the
metadata-only refresh completed on 2026-07-14 LA (2026-07-15 UTC), the store has
1,087 primary record events/content versions representing 656 stable record
identities; 269 events are superseded historical normalizations retained for
provenance. It also has 634 snapshot events representing 443 unique snapshots
and zero anecdote events. The derived tournament review resolves 25 immutable
rows, with zero missing and zero mutable. These are metadata facts only: every
license, artifact download, runtime, device mutation, and execution gate stays
closed. `latest_records()` selects the greatest timezone-normalized
`retrieved_at` for each identity, so a later-appended historical backfill cannot
replace a newer observation. Event-envelope `raw_sha256` and `retrieved_at`
must match their referenced record.

### Pipeline invariants

1. Discovery produces candidates; a resolver joins aliases and revisions.
2. A license gate precedes download or execution.
3. Artifact size is read from repository metadata/file manifests, not estimated
   from active parameters.
4. Runtime support requires a released version, exact main commit, or explicit
   fork/PR label. Model-card “supported” text alone is `claimed`.
5. Cards, code, and benchmark claims are separately versioned.
6. Reddit/community data never merges into the primary-evidence table.
7. Daily deltas produce a review queue; they do not automatically mutate the
   locked serving shortlist.
8. Snapshot filenames are content-addressed, and secrets/authorization headers
   are removed before persistence.

### Candidate admission accounting

- The machine-readable tournament admits publisher size classes no larger than
  35B. It does not infer fit from active parameters or a marketing nickname.
- Resolved tensor counts and file bytes remain separate evidence. Qwen3.6-35B's
  35,951,822,704 tensors are an explicit rounded-label boundary case; they do
  not admit a family marketed above 35B.
- Every candidate lane must intersect an actual pinned runtime on that device.
  Backends such as Metal/Vulkan and formats such as GGUF are not runtimes.
- Normal phone workers stop at four billion actual parameters. Anything larger
  has no phone lane unless a row is explicitly marked feasibility-only, remains
  foreground/checkpointable, and passes exact artifact/runtime probes. The
  official Gemma E2B/E4B LiteRT-LM rows are the current narrow exceptions; they
  do not change the normal-worker ceiling.
- Overview pages and implementation demos are not artifact identities. Exact
  official Gemma and publisher Bonsai repositories are now resolver inputs;
  abbreviated revision prefixes are never expanded by guesswork.

## 2. Evaluation ladder

Do not begin with a full 89-task Terminal-Bench or 113-task DeepSWE run. Cheap
gates catch parser, template, quantization, and stability failures first.

### L0 — static and protocol gates

- Exact publisher repository, immutable revision, artifact manifest/hash,
  resolved parameter count, load config, declared license, and independent
  license decision recorded.
- Chat template, stop tokens, reasoning and tool parsers round-trip.
- JSON Schema exactness: missing/extra keys, types, enums, parallel tools,
  multiple calls, no-call, invalid-tool, Unicode, streaming fragmentation.
- Needle-specific fallback: only execute a call after allowlist + schema +
  confidence/consistency checks; otherwise escalate to the worker.
- Risky-action gate remains enabled.

### L1 — deterministic local replay

- Fixed 100–300 trace stratification across router, search, code edit, test,
  review, summarization, and recovery roles.
- Five seeds for sampled modes; deterministic replay for greedy modes.
- Short, medium, and long multi-turn traces with identical truncation rules.
- A/B single agent, ordinary text multi-agent, and cached multi-agent runs.
- Record semantic success and harness validity separately.

### L2 — tool and agent stability

- BFCL-style simple, multiple, parallel, and parallel-multiple function calls.
- Invalid-call rate, argument exactness, repair count, fallback rate, and
  schema-valid-but-wrong-call rate.
- Drift probes at turns 1/5/10/25/50: instruction retention, tool vocabulary,
  duplicated work, loop detection, and recovery after an injected failure.
- Same-backbone single/TextMAS/LatentMAS A/B/C only; keep heterogeneous family
  boundaries textual until a trained alignment path proves otherwise.

### L3 — current terminal tasks

- Terminal-Bench 2.1 stratified smoke set spanning changed and unchanged task
  categories from an immutable task-manifest pin. Official prose disagrees on
  whether 26 or 28 tasks changed, so the pinned manifest/diff is authoritative.
- Escalate to the full 89 only for models that pass L0–L2 and fit the resource
  budget.
- Run at least five independent attempts per task for Terminal-Bench finalists
  and report task-cluster bootstrap confidence intervals; one lucky pass does
  not promote a model.

### L4 — long-horizon SWE

- DeepSWE deterministic 10-task subset (`sample-seed 0`) for integration.
- Expand to a language/length/failure-mode-balanced 16–24 task set.
- Full 113 only for the final Pareto set, with Pier 0.3.0+ and the separate
  verifier environment pinned.
- Use roughly four independent DeepSWE rollouts per finalist task. Report
  macro-average task pass fraction for pass@1, solved-at-least-once pass@4,
  and every infrastructure exclusion separately.
- SWE-bench Verified/Pro only when debugging evaluator behavior or comparing
  historical results, with the known broken-task caveat attached.

## 3. Metrics

### Quality and stability

- verified task success, pass fraction, and accepted verified steps;
- exact tool selection and exact argument match;
- invalid tool/schema, retry, repair, fallback, loop, and timeout rates;
- success after failure injection and success at turn-depth buckets;
- output variance and pass@k/pass^k over seeds;
- risky-action verifier precision/recall and bypass count (must remain zero).

### Latency, capacity, and efficiency

- TTFT and inter-token latency p50/p95/p99;
- prefill and decode tokens/s, end-to-end wall time, and queue delay;
- concurrency 1/2/4/8 (and higher only when memory permits), goodput, and
  fairness/starvation;
- GPU/CPU utilization, peak and steady VRAM/RAM, KV bytes/token, cache occupancy,
  prefix hit rate, eviction/restoration volume, and OOM/restart count;
- power/energy where measurable, phone temperature/thermal state, throttling,
  battery delta, and performance after 5/15/30 minutes;
- speculative acceptance length/rate, draft latency, verifier latency, wasted
  branches, and net end-to-end speedup versus the exact no-spec baseline.

Primary derived vector:

```text
AVS goodput       = accepted_verified_steps / measured_wall_seconds
AVS memory rate   = accepted_verified_steps / measured_wall_seconds / peak_active_GB
AVS cost yield    = accepted_verified_steps / amortized_dollars
```

The repository shorthand `accepted verified steps / sec / GB / $` refers to
this vector and its Pareto frontier. A combined
`AVS/(wall_seconds*peak_GB*amortized_dollars)` diagnostic may be published only
when amortized cost is positive, but it is dimensionally awkward and must not
be the sole rank. Quality, safety, and integrity gates precede every efficiency
comparison; publish all components so a composite cannot hide quality collapse
or an unsafe parser.

## 4. Factorial discipline

The full conceptual cell is:

```text
model revision x artifact/quant x runtime revision x parser/template
x context/cache mode x decode method x concurrency x role x seed x device
```

Do not run the Cartesian explosion. Use sequential elimination:

1. Hold model/artifact fixed and choose a correct runtime/parser baseline.
2. Hold correctness fixed and sweep context/concurrency/cache.
3. Add one decode method at a time against the exact baseline.
4. Run quality drift gates before scaling concurrency.
5. Compare engines on equivalent artifact formats where possible; label format
   confounds when impossible.
6. Promote only a Pareto frontier, not a single weighted-rank winner.

## 5. Fleet scheduling

- **3090 Ti:** verifier/escalation model and primary controlled serving runs.
- **M1 Pro:** the existing owner continues Qwen3.5-0.8B work; later oMLX lanes
  take router/worker/cache jobs after an interface handoff.
- **Galaxy:** user-started foreground-visible/kiosk, charging-policy opt-in, and
  thermal-budget queue. Generic inference has no standard Android foreground
  service type. Probe exact SoC/RAM/build, OS-available memory, battery health,
  and backend capabilities rather than assume a regional SKU.
- **iPhone:** foreground/docked, short checkpointable tasks; stop new Metal work
  when the app deactivates. Apple publishes no RAM figure, so record
  per-process available memory and the recommended Metal working set. It is a
  routing/validation burst worker, not a background daemon.
- **1080 Ti:** absent until the separate-helper prototype has a remote-latency
  model and estimated speedup. Before asking for installation, collect PSU
  model/wattage, case/slot clearance, connector availability, and exact card
  variant; then run a power/thermal risk review.

Every device result requires an authenticated device identity plus a signed or
content-hashed manifest of OS/build,
SoC/GPU, runtime and backend revisions, artifact/config hashes, power mode,
available-memory probe, and thermal/battery state. Mobile acceptance includes a
5-minute peak cell plus 15- and 30-minute sustained cells, performance-decay
curves, forced lifecycle cancellation/recovery, and low-memory handling. Phones
pull outbound-only, replay-protected leases with no workload secrets, private
corpus, shell, side effects, automatic downloads, or cloud handoff. Transport
uses device-scoped short-lived credentials outside the lease over authenticated
TLS or an authenticated tailnet path. External/vendor telemetry is disabled;
required local latency, memory, thermal, battery, and lifecycle observability is
included in the result bundle. Their ATIF/trial bundles are revalidated by the
desktop coordinator; phones never authoritatively score a Terminal-Bench or
DeepSWE outcome.

## 6. Staged work packets

### P0 — preservation and measurement contract

- Quiesce/recover the diverged repository in a sibling clone.
- Freeze trace/result/evidence schemas and environment manifests.
- Add no model weights yet.

Exit: manifest-verified recovery, repeatable synthetic run, no secret in
artifacts, all current work preserved.

### P1 — existing controls

- Qwen3.5-0.8B, LFM2.5-8B-A1B, and Ornith controls.
- SGLang/vLLM on 3090 where supported; existing Mac owner's oMLX/MLX results
  imported through the result schema, not by touching that workspace.
- L0–L2 plus cache/concurrency baseline.

Exit: stable parser/tool metrics and an honest no-spec performance profile.

### P2 — small/mobile specialization

- Needle versus the existing sub-1B router plan and a larger fallback;
  LFM2.5-1.2B is the normal all-device fast/tool-control candidate after exact
  artifact, parser, license, device-memory, lifecycle, and thermal gates.
- Cactus 2.0.1 versus MNN 3.6.0 and llama.cpp on Android; Cactus versus MLX
  Swift LM, MNN, and llama.cpp Metal on iOS, with MLC/ExecuTorch controls.
  LiteRT-LM `v0.14.0` is added only for an exact supported artifact; its Kotlin/
  C++ lane is stable while Swift remains early preview.
- Phone execution remains Needle and other exact <=4B public/synthetic replay;
  Qwen3.5-4B (4.66B), Agents-A1-4B (4.54B), and Trinity Nano (6.12B) are not
  normal phone workers. Gemma E2B (5.12B stored) and E4B get only explicit
  official-`.litertlm` feasibility cells: E2B first, E4B only after E2B, with
  exact blob/hash, tool/parser, foreground/lifecycle, memory, and sustained-
  thermal gates. Neither can promote to the normal phone-worker lane.
- On 3090/M1, compare Qwen3.5-4B/9B, Agents-A1-4B, Gemma E2B, Trinity Nano,
  Nanbeige, and both LFM sizes. ZAYA remains 3090-only behind its creator-fork/upstream
  release gate. Small Bonsai variants remain metadata-only until a publisher
  artifact resolves.

Exit: measured router precision/recall, fallback economics, and sustained mobile
performance. Do not promote on peak tokens/s.

### P3 — 12–35B worker/escalation tournament

- Start Gemma 4 12B as the dense, matched-drafter control; then Qwen3.6-27B,
  Qwen3.6-35B-A3B, Laguna XS 2.1, Gemma 4 26B-A4B, and Bonsai 27B. Add North
  Mini Code 1.0 and GLM-4.7-Flash as gated coding/agent challengers, with
  Ornith-1.0-35B and Trinity Mini as controlled comparators.
- Agents-A1-35B uses its publisher Q4_K_M GGUF/llama.cpp cell unless another
  fitting publisher quant resolves. Nex-N2-mini remains metadata-only until a
  publisher quant and exact non-base template resolve.
- Qwen3.6 third-party INT4 artifacts require provenance and reproducible
  conversion. North's official NVFP4-style `w4a16` artifact is not a native
  SM86 compute advantage; it requires an Ampere-fitting quant. GLM's main-
  branch instructions require a current-release/parser/quant probe.
- Laguna's matched BF16/FP8 DFlash drafters and vLLM DFlash/tool-parser fixes
  are released/merged. Execution is still blocked on a fitting Ampere target
  quant, combined target/draft/KV headroom, exact parser, acceptance, and local
  quality. FP8 is not native compute on SM86; TensorRT-LLM remains on the exact
  1.3 RC research gate rather than being assumed runnable.
- Start language-only at 4K/16K and concurrency 1; increase one dimension at a
  time.
- L0–L3, then DeepSWE subset only for finalists.

Exit: quality/latency/memory Pareto set, not a permanent winner.

### P4 — acceleration

- Prefix/cache improvements, then n-gram/native MTP, then supported DFlash or
  DSpark.
- Exact first method cells are Laguna XS 2.1 plus its released BF16/FP8 DFlash
  drafter on pinned vLLM, and Gemma 4 12B plus its released DFlash drafter on
  SGLang or EAGLE3 drafter on vLLM. Each retains target quant, draft-license,
  parser, combined-headroom, acceptance, quality, and rollback gates.
- DSpark's released generic vLLM controls are exact Qwen3 4B/8B/14B and
  DeepSeek-V4 pairs. Gemma 12B's drafter exists but stays research-only until
  its still-open vLLM integration is accepted and pinned; no Qwen3.5/3.6 or
  SGLang support is inferred.
- TurboQuant/TQ+ only when KV capacity is a measured constraint. Rotor/Iso,
  SpectralQuant, and OSCAR remain separately pinned research comparisons.
- JetSpec, diffusion DDTree/CaDDTree, the distinct DominoTree method, SSD,
  SpecMoE, Speculating Experts, custom heads, and kernels remain isolated
  research branches until they beat native baselines end to end. Method names
  and result cells are not merged.

Exit: statistically repeatable goodput or latency gain with no unacceptable
quality/tool regression and a maintained rollback path.

### P5 — optional second GPU

- Build a network/IPC simulator for separate drafting/verification using
  measured 1080-class latency assumptions.
- Ask for installation only if the projected helper lane remains positive after
  communication, idle power, heat, and unsupported-runtime costs.

Exit: an explicit install/no-install decision. Current decision is **no install
yet**.
