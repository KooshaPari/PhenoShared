# OKF Wiki — ChatGPT Corpus Distillation

Wiki root for pheno-harness **Organizational Knowledge Framework (OKF)**. Source material lives at `D:\koosh\Downloads\ChatGPT-*.md` (50 exports); this tree holds distilled, reviewable knowledge—not raw exports.

**Manifest:** [`corpus_manifest.json`](corpus_manifest.json)  
**Evidence registry:** `config/evidence_registry.yaml` → `local_corpus` (class **L**, hash-only, no paths in durable store)  
**Adapter:** `pheno/evidence/adapters/local_corpus.py`

## Corpus snapshot

| Root | Files | Notes |
|------|------:|-------|
| `D:/koosh/Downloads` | 50 | Primary corpus; pattern `ChatGPT-*.md` |
| `C:/Users/koosh/Downloads` | 0 | Empty for this pattern |

50 files → **48 unique SHA-256** (one duplicate triplet: Pairwise Test Case Generation ×3; other near-duplicates differ by export revision).

## Category taxonomy

Each category gets `docs/okf/<category>/` pages distilled from corpus titles + evidence-class-L claims. Stale or unverified ChatGPT assertions must be overridden by primary sources (HF, arXiv, GitHub) before promotion to class **P**.

| Category | Scope | Priority corpus (basename prefix `ChatGPT-`) |
|----------|-------|-----------------------------------------------|
| **inference** | Serving, VRAM/KV, MoE/dense scaling, runtime costs, caching, tiered memory | VRAM and Scaling Factors, Efficiency Evolutions Post-MoE, Compression Pruning Review, LLM Architectures Discussion, Small MoEs Use Cases, User-level Deterministic Cache, Kimi DeepSeek MoE Cost, Model Inference Costs 2026, API vs Local Compute, **Modding 3090 Ti VRAM** (tiered memory / MoE staging — mislabeled title) |
| **kernels** | Custom decode, CUDA/Metal/WGPU substrate, throughput on 3090, memory-tier schedulers | RTX 3090 Throughput Analysis, RLVR-AF Optimization Proposal, **Modding 3090 Ti VRAM** (cross-tag: inference+kernels) |
| **agents** | Intent graphs, orchestration, tool-call stability, harness design | Coding Agents and Intent Graphs, Agent Flow Optimization, Feature graph system design, Concurrent Lint Command Handling, Agent Setup Cost Analysis, Software Project Traceability Tools, Incorporation as Agent |
| **hardware** | Machine/GPU selection, rental safety, $/TFLOP, local vs cloud | Machine Comparison for AI, AI Inference Hardware Costs, Model improvements under $500, GPU Rentals Safety Review |
| **benchmarks** | Eval methodology, cost/latency tradeoffs, test generation | Model Inference Costs 2026, Pairwise Test Case Generation, Agent Setup Cost Analysis |
| **routing** | Multi-agent routing, MAS architectures, needle/work routing | LatentMAS vs TextMAS comparison, Agent Flow Optimization, Feature graph system design |
| **speculative-decode** | JetSpec, DDTree, PEAGLE, agent-aware draft trees | Agent-Aware Speculative Decoding |

### Out of scope (retain in manifest only)

Gaming/modding and career threads are not distilled into pheno-harness OKF: 3D God-Game Simulation Design, Star Wars *, Futuristic Warfare Modding, Best Modding DX/UX Games, Enterprise Tech Job Search, Agent Orchestration Game Concept.

## Distillation plan

### Phase 0 — Inventory (done)

1. Enumerate corpus with SHA-256 → `corpus_manifest.json`.
2. Align with evidence registry `local_corpus` scan (`ChatGPT-*.md` under `D:/koosh/Downloads`).
3. Map each in-scope file to exactly one primary category (+ optional cross-tags in front matter).

### Phase 1 — Skeleton pages

For each category, create:

- `docs/okf/<category>/README.md` — charter, open questions, links to source basenames (not full paths in git).
- `docs/okf/<category>/claims.md` — bullet claims tagged `[L]` from exports; each claim cites `local://sha256/<digest>` from manifest.

### Phase 2 — Verification loop

1. For each `[L]` claim, attach at least one primary-source counterpoint or confirmation in `docs/okf/<category>/evidence-links.md`.
2. Promote verified items to tournament configs / `docs/specs/` only after class **P** evidence exists.
3. Re-run `scripts/evidence_registry.py plan --sources local_corpus` after corpus moves; update manifest mtime/sha256.

### Phase 3 — Chunking (optional)

When stable, mirror HexaKit OKF pattern: chunk to `docs/okf/wiki/chunks/{artifact-id}-{slug}.okf.md` for RAG injection. Injection order: this INDEX → category README → claims → cross-links to `plans/2026-07-14-usch-heterogeneous-inference-v1/`.

## Distilled articles (Phase 1 sample)

Six highest-value inference/kernels/hardware/agent/routing exports distilled into reviewable wiki pages (class **L** until primary-source verification):

| Article | Source basename | Category |
|---------|-----------------|----------|
| [`inference/agent-aware-speculative-decoding.md`](inference/agent-aware-speculative-decoding.md) | Agent-Aware Speculative Decoding | inference / speculative-decode |
| [`inference/vram-scaling-factors.md`](inference/vram-scaling-factors.md) | VRAM and Scaling Factors (1) | inference |
| [`kernels/tiered-memory-hierarchy.md`](kernels/tiered-memory-hierarchy.md) | Modding 3090 Ti VRAM | inference + kernels (tiered memory, MoE staging — not GDDR modding) |
| [`agents/coding-agents-intent-graphs.md`](agents/coding-agents-intent-graphs.md) | Coding Agents and Intent Graphs (1) | agents |
| [`hardware/rtx-3090-throughput.md`](hardware/rtx-3090-throughput.md) | RTX 3090 Throughput Analysis | hardware / kernels |
| [`routing/latentmas-vs-textmas.md`](routing/latentmas-vs-textmas.md) | LatentMAS vs TextMAS comparison (1) | routing |

## Sample exports (structure)

All exports share ChatGPT markdown export headers (`User`, `Created`, `Exported`, `Link`) then `## Prompt` / `## Response` turns. Representative samples used for taxonomy:

| File | First-line topic | Category |
|------|------------------|----------|
| Agent-Aware Speculative Decoding | JetSpec, DDTree, PEAGLE compound report | speculative-decode → [`inference/agent-aware-speculative-decoding.md`](inference/agent-aware-speculative-decoding.md) |
| VRAM and Scaling Factors (1) | HF VRAM assumptions, MoE concurrency scaling | inference → [`inference/vram-scaling-factors.md`](inference/vram-scaling-factors.md) |
| Coding Agents and Intent Graphs (1) | Intent graphs / task DAG for weak executors | agents → [`agents/coding-agents-intent-graphs.md`](agents/coding-agents-intent-graphs.md) |
| Machine Comparison for AI | Vast.ai GPU listings, $/DLP tradeoffs | hardware |
| LLM Architectures Discussion | Frontier vs OSS architecture R&D | inference |
| RTX 3090 Throughput Analysis | tok/hour, multi-GPU scaling | kernels → [`hardware/rtx-3090-throughput.md`](hardware/rtx-3090-throughput.md) |
| Modding 3090 Ti VRAM | Tiered memory, MoE expert staging, vLLM/SGLang offload (title misleads) | inference + kernels → [`kernels/tiered-memory-hierarchy.md`](kernels/tiered-memory-hierarchy.md) |
| LatentMAS vs TextMAS comparison (1) | KV-sharing MAS vs API TextMAS | routing → [`routing/latentmas-vs-textmas.md`](routing/latentmas-vs-textmas.md) |

## Pheno-harness references

| Location | Reference |
|----------|-----------|
| `config/evidence_registry.yaml` | `local_corpus.roots`, `pattern: ChatGPT-*.md` |
| `config/heterogeneous_tournament.yaml` | `private_chatgpt_corpus` forbidden on mobile workers |
| `docs/specs/003-model-engine-matrix.md` | Agent-Aware Speculative Decoding corpus cite |
| `pheno/evidence/adapters/local_corpus.py` | Hash-only LOCAL_SCAN adapter |
| `plans/2026-07-14-usch-heterogeneous-inference-v1/` | Prior 49-export registry narrative (current scan: 50 files, 48 unique hashes) |

## OKF dirs elsewhere (depth ≤ 3)

No `okf/` under pheno-harness yet (this tree is the wiki root). Peer patterns:

- `C:\Users\koosh\AgilePlus\okf\manifest.okf.yaml`
- `C:\Users\koosh\ecosystem\repos\HexaKit\okf\` (+ phenotype-* repos, worktrees)

Consider adding `docs/okf/manifest.okf.yaml` in a follow-up to align with ecosystem OKF tooling.
