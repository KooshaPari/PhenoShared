# RLVR-AF Optimization Proposal

**Source:** `ChatGPT-RLVR-AF Optimization Proposal (1).md` (81,401 bytes, 2026-07-04) — sha `6276ce0c…` — class **L**.

RLVR-AF (Reinforcement Learning with Verifiable Rewards + Agentic Flow) kernels/inference optimization for heterogeneous inference. Couples verifier rewards (`verifier/`) with agentic workflow scheduling (`agent/`), targeting Metal-on-M1-Pro (`kernels/qwen3.5-0.8b/metal/`) and SGLang/triton on `tb2-30000-sglang.service`.

## Distilled claims (class **[L]** — from `ChatGPT-RLVR-AF Optimization Proposal (1).md`)

### 1. Reward = verified pass with evidence class promotion

- **[L]** `verifier/` returns a structured `EvaluationReport v0.5` with `gen_ok / verified_pass_at_1 / evidence_label`. RLVR converts `verified_pass_at_1` to a reward signal — `1.0` for [P] evidence, `0.5` for [L], `0.0` for [N] (none/foreign).
- **[L]** Reward shaping adds a small penalty for evidence-class **L** claims (0.05) but not **P** (1.0); this biases the policy toward promoting claims with primary sources rather than free-riding on ChatGPT export quality.
- **[L]** AF (Agentic Flow) couples trace placement: each agent step annotates the trail with `[L]` cites; the verifier reward aggregates across steps so a single bad cite doesn't zero out an otherwise good episode.

### 2. Tiered Metal kernel schedule (Apple Silicon primary path)

- **[L]** On M1 Pro, RLVR-AF runs Metal kernels (`kernels/qwen3.5-0.8b/metal/`) for `Qwen3.5-0.8B`; reward is shaped higher when run-time < 1.5× MoE/M dense baseline.
- **[L]** Kernel fusion reduces ~3 separate launches (`q_proj`, `kv_proj`, `rotary_emb`) into 1 launch on Metal; observed ~12% decode throughput lift on M1 Pro per source.
- **[L]** Speculative-decode (JetSpec-style) cuts another ~30% wall-clock at concurrency 4-8 with trivial draft cost on 0.8B target.

### 3. Trace placement & heterogeneous worker routing

- **[L]** RLVR-AF maps to `plans/2026-07-14-usch-heterogeneous-inference-v1/` and `config/heterogeneous_tournament.yaml` worker tiers; the system scores Mobile (M1 Pro) vs WSL2 (3090 Ti + 1080 Ti) lanes and picks the cheapest `[L]`-verifiable run.
- **[L]** Pairwise sampling reduces the RLVR × model × hardware matrix 70% (per `benchmarks/pairwise-test-case-generation.md`). RLVR-AF builds on this — only 30% of the matrix needs verifiable runs to bound the rest.
- **[L]** AFL (Agentic Flow Loop) budget: `max_turns=8`, `summarize=false`; above that the policy decays reward because the verifier accumulates penalty. Maps to N06/N09 precedent in granite checkpoints.

### 4. Sglang triton optimization (dual-harness path)

- **[L]** When running on `tb2-30000-sglang.service` (RTX 3090 Ti), RLVR-AF uses triton `attention-backend` instead of CUDA graph; the watchdog unit already enforces this (`--attention-backend triton --disable-cuda-graph`).
- **[L]** `mem-fraction-static 0.92` is fine for 9B (Qwen3.5-9B at `/home/<REDACTED>/models/Qwen3.5-9B`); above 0.93 leaves <50 MB headroom for `cpu_scheduler` overlap.

### 5. Pheno-harness linkage

- `verifier/` RLVR gate must implement the `EvaluationReport v0.5` schema (`gen_ok / verified_pass_at_1 / evidence_label`) before any RLVR-AF run is valid.
- `bench/contracts/EVAL_RESULT_CONTRACT.md` is the source-of-truth for the reward shape; promote to [P] only after the contract is reference-implemented in `bench/runners/runner.py`.
- `pheno/serve/serve.py` exposes `--rlvr-af` flag (TBD); when present, uses metal kernel schedule on M1 Pro lanes, triton elsewhere.

## Architectural sketch (claim class [L])

```
                   ┌───────────────────────┐
   prompt   ───►   │ RLVR-AF orchestrator  │
                   │  • tokenize           │
                   │  • metal / sglang     │   (lane picks per:
                   │  • draft / verify     │    • gpu budget
                   └───────────┬───────────┘    • evidence class target)
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     M1 Pro lane       tb2-30000-sglang       verifier gate
     (Qwen3.5-0.8B      (Qwen3.5-9B            (eval-report v0.5
      metal kernels)    triton, 8192 ctx)       pass_at_1)
            │                  │                  │
            └──────────────────┼──────────────────┘
                               ▼
                     reward signal → policy update
```

All labels class **[L]** — verify with HF / arXiv / GitHub sources.

## Verification targets (before promotion to [P])

- [ ] **RLVR seminal paper** (DeepSeekMath, arXiv 2402.14900, 2024) — verify reward = verified_pass_at_1 + class weighting.
- [ ] **JetSpec paper / repo** (spec-decode GitHub, 2024) — verify 30% decode lift claim.
- [ ] **Triton attention-backend reference impl** in `sgl-kernel` — verify triton alternative to CUDA graph.
- [ ] **Local Metal benchmark** `kernels/qwen3.5-0.8b/metal/bench_run.py` — actually measure 12% lift on M1 Pro.
- [ ] `bench/contracts/EVAL_RESULT_CONTRACT.md` reference impl in `bench/runners/runner.py` — make contract enforceable.

## Cross-links

- `inference/agent-aware-speculative-decoding.md` — JetSpec / DDTree / PEAGLE compound report; speculative-decode primer.
- `kernels/tiered-memory-hierarchy.md` — Modding 3090 Ti VRAM; tiered memory applies when MoE experts are paged.
- `agents/coding-agents-intent-graphs.md` — agentic workflow representation.
- `benchmarks/pairwise-test-case-generation.md` — 70% matrix reduction technique.
- `plans/2026-07-14-usch-heterogeneous-inference-v1/` — original heterogeneous inference plan; mentions RLVR-AF as future cell.
- `config/heterogeneous_tournament.yaml` — worker tier config (mobile / WSL / forbidden sets).

**Evidence:** `local://sha256/6276ce0c35b6254dabb971dc5e379a0134bffca3242ebf9011f68448ee2fb271` (class **L**). Promote to class **P** after primary-source verification.
