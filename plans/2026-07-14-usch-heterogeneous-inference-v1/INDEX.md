# Heterogeneous local-agent inference program — index

Date: 2026-07-14

Status: research plan plus additive offline contract implementation; no model
download, benchmark execution, server launch, kernel build, phone install, Mac
mutation, or GPU installation is authorized by this packet.

This packet refreshes the July 3–4 plan against primary sources available on
2026-07-14. It does not silently replace ADR 0005's three locked local aliases.
New candidates remain a metadata-only tournament until a follow-up ADR admits a
specific artifact, quantization, runtime version, and rollback path.

The bounded metadata refresh completed across Hugging Face, ModelScope,
GitHub, arXiv, and the local corpus. The 2026-07-18 offline coverage audit is
green at 1,087 record events / 656 stable record identities and 634 snapshot
events / 443 unique
snapshots; 269 record events are superseded provenance and the anecdote stream
has zero events. Exact immutable evidence now resolves all 25 tournament rows,
with zero missing and zero mutable. The 49 configured private ChatGPT exports
are represented 49/49 across 47 unique hashes; they remain class-[L] lineage,
and stale claims defer to current primary evidence. Every promotion, license,
download, runtime, device-mutation, and execution gate remains closed.

## Additive evaluator checkpoint

Strict `pheno.eval.trial.v2`, `pheno.eval.aggregate.v2`, and
`pheno.eval.run-provenance.v1` contracts, a Pheno ATIF v1.7 integrity overlay,
and the offline `validate-atif`, `validate-trial`, and `validate-aggregate` JSON
commands have landed additively, together with
`validate-performance-block`, `validate-replay-stability`, and
`validate-telemetry`. The separate
`audit_eval_locks.py` command
strictly audits bounded local YAML locks and exposes a nonzero
`--require-scoreable` gate. Aggregation uses deterministic 10,000-sample
task-cluster bootstrap intervals; run-level makespan, time-aligned attributable
physical-memory peak, and reconciled cost ledger are never summed per request.
`validate-trial --artifact-root` additionally proves declared file hashes,
official Harbor plus Pheno ATIF validity, intent-graph integrity, and verifier
artifact presence. Aggregate latency distinguishes token-endpoint decode
throughput from SSE chunk gaps, and drift uses hashed 1/5/10/25/50-turn
assertion checkpoints.

This is implementation plumbing only. The fixtures are offline/synthetic; the
lock audit reports both candidate locks structurally valid but zero scoreable,
and no Harbor, Pier, model, runtime,
or device benchmark was executed. Harbor's official
[ATIF validator](https://www.harborframework.com/docs/agents/trajectory-format)
remains the schema authority and must precede the local overlay. Methodology is
anchored to the pinned [DeepSWE protocol](https://arxiv.org/html/2607.07946v1),
the [Terminal-Bench paper](https://arxiv.org/html/2601.11868), and its
[leaderboard integrity policy](https://www.tbench.ai/news/leaderboard-integrity-update).
Newly landed implementation files remain untracked and post-date the original
verified packet. They require a fresh delta capture after writers quiesce,
before no-loss reconciliation.

The current offline verification checkpoint is 275 passing tests plus 54
subtests; the focused acceleration/tournament slice is 26 passing tests plus
three subtests. This verifies contract/configuration consistency only and does
not make either candidate lock scoreable or authorize execution.

## Reading order

| File | Purpose |
|---|---|
| `RECOVERY.md` | Exact unarchive result, moving local/remote divergence, preservation state, GET-only remote snapshot acquisition, and the non-mutating reconciliation preflight. |
| `RESEARCH_AUDIT.md` | Evidence labels, current runtime/eval facts, local ChatGPT corpus synthesis, and stale-claim corrections. |
| `MODEL_RUNTIME_MATRIX.md` | Model tournament and device-specific runtime policy for the 3090 Ti, M1 Pro, phones, and optional 1080 Ti. |
| `FLEET_READINESS.md` | Offline device-capability manifests, owner/headroom/thermal gates, heterogeneous telemetry handoff, and conservative optional-1080 simulation. |
| `ACCELERATION_READINESS.md` | What is usable now versus research-only across caches, MTP, DFlash, method-specific DSpark, DDTree versus DominoTree, SpecMoE, JetSpec, SSD, TurboQuant+, TiDAR, LatentMAS, and dMoE. |
| `SOURCE_ADAPTERS.md` | Exact HF/ModelScope/GitHub/arXiv/Reddit/local-corpus discovery, revision, rate, license, and retention rules. |
| `EVALUATOR_CONTRACT.md` | Immutable TB2.1/DeepSWE pins, landed offline trial/aggregate/ATIF/performance/replay/telemetry contracts, scoreability semantics, remaining gaps, and hard promotion gates. |
| `EXPERIMENT_AND_DISCOVERY_PLAN.md` | Reproducible source discovery, evaluation ladder, metrics, gates, and staged work packets. |

## Outcome-first decisions

1. **Preserve before integrating.** GitHub is unarchived, but the local checkout
   and live remote have diverged from a shallow common boundary. Do not pull,
   rebase, reset, clean, or push this worktree.
2. **Keep the north-star vector:** compare accepted verified steps per second,
   per second per peak-active GB, and per dollar—not raw tokens/s or vendor
   leaderboard scores. The combined AVS/(s·GB·$) value is reporting-only.
3. **Measure state management first.** Prefix reuse, exact cache accounting,
   chunked prefill, and multi-agent concurrency precede custom decode kernels.
4. **Use a tiered model tournament.** Tiny router/tool specialists, 8B-class
   workers, and 26–35B escalation models get different jobs and budgets.
5. **Choose engines per artifact, not by brand.** SGLang and vLLM form the 3090
   Ti A/B baseline; TensorRT-LLM is a finalist-only lane; oMLX/MLX own the M1
   lane after owner handoff. Mobile has no winner before Cactus/MNN/llama.cpp/
   LiteRT-LM/MLX Swift tests on exact artifacts; llama.cpp is also the low-bit
   portability control.
6. **Do not install the GTX 1080 Ti yet.** Current vLLM requires NVIDIA compute
   capability 7.5+, while Pascal is 6.1. The card becomes relevant only as a
   separate llama.cpp/CUDA-12.x draft, embed, rerank, or verifier service after
   a measured helper-lane experiment justifies power, thermal, and legacy-stack
   cost.
7. **Phones are opportunistic edge workers.** They are best used for Needle or
   LFM2.5-1.2B routing/tool controls, schema validation, embeddings, retrieval,
   and short foreground model bursts—not as assumed 24/7 GPU servers. Official
   Gemma E2B/E4B LiteRT artifacts are feasibility-only exceptions, with E2B
   first; they do not change the four-billion-parameter normal-worker ceiling.
8. **Do not touch the Mac workstream in this phase.** Another agent owns the
   Qwen3.5-0.8B kernel/eval lane. This packet defines compatible interfaces and
   experiments only.
9. **Keep evidence plumbing distinct from evidence.** A fixture can prove that
   the trial, aggregate, ATIF-overlay, and CLI contracts reject malformed
   inputs; it cannot prove model quality, latency, stability, or scoreability.

## Evidence labels

- **[V]** verified in a primary source or live repository metadata on 2026-07-14.
- **[C]** creator/vendor/model-card claim; useful for prioritization, not accepted
  as a local result.
- **[L]** conclusion from the user's local ChatGPT conversation corpus.
- **[I]** inference or proposed experiment; must be tested locally.
- **[A]** community anecdote, including Reddit; discovery signal only.

Every result row produced from this plan must preserve the evidence class and
the exact model revision, runtime revision, artifact hash, configuration hash,
and evaluator revision. A vendor score never becomes a verified local score by
being copied into a table.

## Scope boundaries inherited from the repo

- Risky-action verification remains enabled for every shell-capable agent.
- Credentials remain runtime-only and must never enter artifacts or logs.
- ADR 0005's “no weight download or server start” consequence still applies.
- SWE-bench Verified remains a plumbing/debug signal, not the quality north
  star. Terminal-Bench 2.1, DeepSWE, tool-call exactness, and replayed local
  trajectories form the primary quality ladder.
- The only trial outcome states are `passed`, `model_failure`, and
  `infrastructure_exclusion`. Verifier rejection, timeout, context exhaustion,
  OOM, and unsafe behavior are model failures; they are not discarded as
  infrastructure exclusions.
- Harbor's official ATIF validation must run before the local closed-artifact
  overlay. Passing `validate-atif` alone is not scoreability evidence.
- Custom CUDA, Metal, Vulkan/WGPU, Rust, Zig, C++, Mojo, Nim, Vale, Pony,
  Carbon, or other kernel work begins only after a profiler identifies a stable
  operation, shape distribution, and measurable end-to-end ceiling.
