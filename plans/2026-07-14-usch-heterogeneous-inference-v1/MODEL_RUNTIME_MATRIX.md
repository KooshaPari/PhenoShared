# Model and runtime matrix

> **2026-07-18 coverage correction:** the configured tournament has 25
> candidates, while the checked-in `2026-07-14-tournament.json` review has only
> 20. Missing review rows are `lfm25-1p2b`, `gemma4-e4b`, `gemma4-12b`,
> `north-mini-code-10`, and `glm47-flash`. The older review is neither complete
> nor a July-18 freshness proof. Run
> `python scripts/audit_tournament_review.py --as-of 2026-07-18`; exit 3 is the
> expected fail-closed result until a new immutable review is generated.

This is a tournament, not a new locked shortlist. Phase 0 keeps ADR 0005's
Qwen3.5-0.8B, LFM2.5-8B-A1B, and Ornith-1.0-9B aliases as controls. A candidate
is admitted only after license, artifact size/hash, parser, and runtime support
are recorded and a metadata-only review approves the download.

## Priority tournament

### Fast/router/specialist tier (roughly 0.02–4B)

| Candidate | Why test | Initial fleet lane | Evidence/risk |
|---|---|---|---|
| [Cactus Needle](https://github.com/cactus-compute/needle), [HF artifact](https://huggingface.co/Cactus-Compute/needle), 30,427,676 artifact parameters (repository describes ~26M) | Single-shot function/tool selection, tiny footprint, local finetuning | Both phones, M1, CPU control | [V] architecture/code; advertised speed/accuracy is [C]. It is not a planner. Needle is MIT, but deploying it through Cactus inherits a separate runtime-license gate. Require strict schema validation and fallback. |
| Qwen3.5-0.8B | Existing locked control and active Mac kernel/eval workstream | M1 and 3090 control | Keep for continuity; do not confuse control status with frontier status. |
| [Nanbeige4.1-3B](https://huggingface.co/Nanbeige/Nanbeige4.1-3B) | Current small reasoning/tool/deep-search candidate | 3090, M1 if a supported quant exists | Creator scores and 500+ tool-round claim are [C]. HF parameter metadata and name differ; resolve exact config before labeling size. |
| [LFM2.5-1.2B-Instruct](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) | Dense 1.2B all-device fast/tool control with publisher [GGUF](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF) and [MLX 4-bit](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-MLX-4bit) artifacts | 3090, M1, Galaxy, and iPhone normal-worker candidate | Exact revisions are `868df74dd56ff8a0c2ac5dbf281690c2dbebe4c9`, `047e06635fbe71469926b35ea414537245218200`, and `c30e30c5efac705771e1f37df38a32115718dd5d`. Exact artifact/runtime/parser, license, phone memory/lifecycle/thermal, and install-authorization gates remain closed. |

Small Bonsai variants remain metadata watchlist items until an exact publisher
artifact resolves. The demo repository is implementation evidence, not a model
artifact identity.

### Worker tier (roughly 4–12B total)

| Candidate | Architecture/fit | Initial fleet lane | Evidence/risk |
|---|---|---|---|
| [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) / [9B](https://huggingface.co/Qwen/Qwen3.5-9B) | Dense MTP controls; exact repository counts are 4,659,865,088 and 9,653,104,368 | 3090 and M1 | Resolve an exact quant, parser, and runtime before execution. Neither is a normal phone worker because both exceed the 4B cap by actual parameter count. |
| [Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B) | Dense 4,539,265,536-parameter compact agent model, 262K context | SGLang/vLLM on 3090; publisher [Q4 GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF) with llama.cpp on M1 | Apache-2.0 is publisher-declared, not locally approved. Tool template/parser and the Q4 quality delta remain execution gates. |
| [Gemma 4 E2B](https://huggingface.co/google/gemma-4-E2B-it) | Sparse model with 5,123,178,051 stored parameters, marketed as about 2.3B effective | 3090/M1; both phones only through the official [LiteRT artifact](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) as a feasibility cell | Do not infer normal phone fit from the E2B name. The `.litertlm` repo is pinned at `9262660a1676eed6d0c477ab1a86344430854664`; its 2,588,147,712-byte blob has SHA-256 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`. Public/ungated Apache-declared metadata still needs ordinary license review plus exact parser/tool, memory, lifecycle, thermal, and runtime probes. |
| [Gemma 4 E4B](https://huggingface.co/google/gemma-4-E4B-it) | Sparse ~8B-total/~4.5B-active edge control | Both phones, official [LiteRT artifact](https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm), feasibility-only | The repo is pinned at `f7ad3343bd6ebc9607f4dc3bc4f2398bd5749bc5`; its 3,659,530,240-byte blob has SHA-256 `0b2a8980ce155fd97673d8e820b4d29d9c7d99b8fa6806f425d969b145bd52e0`. Test only after E2B feasibility, never as a normal phone worker; Swift remains early preview. |
| [Trinity Nano Preview](https://huggingface.co/arcee-ai/Trinity-Nano-Preview) | 6,120,003,328 total/~1B active MoE | M1-only experimental [MLX 5-bit](https://huggingface.co/arcee-ai/Trinity-Nano-Preview-MLX-5bit) | Preview status is an instability gate. No phone lane and no promotion without exact artifact/runtime reproduction. |
| [LFM2.5-8B-A1B](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) | 8.3B total, 1.5B active, 128K; official MLX/GGUF and vLLM/SGLang support | 3090 and M1; no normal phone lane | Best practical edge/worker first pass. Creator says it is not ideal for heavy programming, so test routing/tools rather than assume SWE strength. Custom license needs a gate. |
| [ZAYA1-8B](https://huggingface.co/Zyphra/ZAYA1-8B) | 8.4B total, 760M active; reasoning-focused MoE | 3090 only after the creator-fork/upstream gate | Apache-2.0 is declared, but the official quickstart still requires forks. Do not credit released-wheel or official MLX support yet. |
| Ornith-1.0-9B | Existing locked worker control | 3090/M1 control | Preserve as a regression comparator even if new candidates overtake it. |
| [Gemma 4 12B](https://huggingface.co/google/gemma-4-12B-it) | Dense 11,959,730,224-parameter target with publisher [QAT Q4 GGUF](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf) | SGLang/vLLM/llama.cpp on 3090; M1 feasibility after exact fit | Target revision `0e2b1058541244490925fbacf8972041435691ac`; Q4 revision `2b318d6ebebf093f50ca4376e858325f10703358`, 6,975,877,728 bytes, SHA-256 `faff1a63667fac17ac5e777f47114688fcefea96e220e211aaa8d62c2c4561f1`. SGLang DFlash and vLLM EAGLE3 are released method-specific candidates; Gemma DSpark remains research-only behind its open vLLM PR. Drafter-license and combined-headroom gates remain closed. |

### Escalation tier (roughly 26–35B total)

| Candidate | Architecture/fit | First runtime lane | Decision role |
|---|---|---|---|
| [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | Dense MTP model, 262K native context | SGLang/vLLM language-only INT4 on 3090 | The YAML ceiling uses the publisher's 27B size class; immutable config/artifact metadata is authoritative. No publisher INT4 was assumed, so provenance and reproducibility are gates. Start at 4K–16K. |
| [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | Publisher 35B size class/3B active MoE with MTP; the resolved tensor count is 35,951,822,704 | SGLang/vLLM INT4 on 3090 | This is the explicit boundary case, not permission to admit 36B-labelled families. A provenance-checked third-party INT4 and measured KV headroom are mandatory. |
| [Laguna XS 2.1](https://huggingface.co/poolside/Laguna-XS-2.1) | 33B total/3B active coding MoE, 262K, with released matched [BF16](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash) and [FP8](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash-FP8) DFlash drafters | SGLang language baseline; vLLM `v0.25.1` DFlash candidate; TensorRT-LLM remains on the pinned 1.3 RC research line | vLLM [DFlash support](https://github.com/vllm-project/vllm/pull/46853) and the [tool-parser fix](https://github.com/vllm-project/vllm/pull/47311) are merged. Execution remains blocked: the official INT4/observed ~18.88GiB GGUF leave poor 24GB headroom, BF16 drafting adds pressure, FP8 is not native SM86 compute, and an Ampere target quant plus combined target/draft/KV, parser, acceptance, and quality probes are required. |
| [North Mini Code 1.0](https://huggingface.co/CohereLabs/North-Mini-Code-1.0) | 30,484,303,872 total/~3B active coding MoE, Apache-2.0 declared | SGLang/vLLM on 3090 only after an Ampere-fitting quant resolves | Base revision `d11e61a842617a22dc328552fa5bb86231ee4f37`; official [`w4a16`](https://huggingface.co/CohereLabs/North-Mini-Code-1.0-w4a16) revision `1e55f4aa327aba4c0b7a1da0d0f24626d3af5c90` uses an NVFP4-style path that is not a native SM86 compute win. Require quant provenance, current release, parser/tool, license, and headroom probes. |
| [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash) | 31,221,488,576 total/~3B active agent/coding MoE, MIT declared | SGLang/vLLM on 3090 after an exact released pair resolves | Revision `7dd20894a642a0aa287e9827cb1a1f7f91386b67`. Model-card main-branch instructions do not prove the pinned release, parser, fitting quant, or local headroom; all remain execution gates. |
| [Gemma 4 26B-A4B](https://huggingface.co/google/gemma-4-26B-A4B-it) | 26,544,131,376 total/~3.8B active MoE; official [QAT Q4 GGUF](https://huggingface.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf) | SGLang/vLLM or llama.cpp on 3090 | Declared-license review plus exact artifact/runtime, parser, and headroom remain gates. Google notes batch-1 MoE MTP may not accelerate without enough parallelism. |
| [Agents-A1](https://huggingface.co/InternScience/Agents-A1) | Publisher 35B-A3B long-horizon agent model | Publisher [Q4_K_M GGUF](https://huggingface.co/InternScience/Agents-A1-Q4_K_M-GGUF) with llama.cpp on 3090 | Do not assume a fitting SGLang/vLLM quant. Parser correctness, roughly 20GiB-class weight fit, and local long-horizon reproduction gate execution. |
| [Nex-N2-mini](https://huggingface.co/nex-agi/Nex-N2-mini) | Qwen3.5-35B-A3B derivative with agent/tool post-training | Metadata-only until a publisher quant and exact template resolve | No publisher quant was found in the audit and the template differs from the base family. Creator TB2.1/SWE claims remain [C]. |
| [Bonsai 27B AWQ](https://huggingface.co/prism-ml/Bonsai-27B-AWQ-4bit) / [GGUF](https://huggingface.co/prism-ml/Bonsai-27B-gguf) / [MLX 1-bit](https://huggingface.co/prism-ml/Bonsai-27B-mlx-1bit) | Dense 27,356,728,560-parameter Qwen3.6 derivative with experimental low-bit formats | AWQ/SGLang and GGUF/llama.cpp on 3090; MLX 1-bit on M1 | Publisher artifacts replace the demo-only identity. Custom-format support and vendor quality/speed claims must be reproduced; the GitHub demo remains implementation evidence only. |
| [Ornith-1.0-35B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B) | 35B-A3B MoE, MIT | Canonical metadata cells on pinned SGLang/vLLM; publisher [Q4_K_M GGUF](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B-GGUF) as a separate llama.cpp artifact lane | Publisher SGLang/vLLM commands were demonstrated on 8x80GB, not the 3090 Ti. The GGUF is approximately 19.71GiB, leaving little KV/runtime headroom. All lanes require exact artifact/parser/fit evidence; any admitted 3090 trial begins at concurrency 1. |
| [Trinity Mini](https://huggingface.co/arcee-ai/Trinity-Mini) | 26,123,974,400 total/~3B active MoE | Publisher [GGUF](https://huggingface.co/arcee-ai/Trinity-Mini-GGUF) with llama.cpp on 3090 | OpenMDW 1.1 and custom-architecture/runtime support require review; use as a controlled MoE comparator, not a default. |

Nemotron remains a metadata-only watchlist family; no runnable row is implied.
GLM-4.7-Flash now has a gated tournament row, not execution authorization.
Models labelled above the 35B publisher size class are excluded even
when active parameters are small. Exact tensor counts can exceed a rounded 35B
label (Qwen3.6 is the explicit case), so resolved counts and artifact bytes are
recorded separately and never used to smuggle a larger-labelled family across
the planning ceiling.

## Device/runtime policy

| Device | Default lane | Secondary/control | Explicit exclusions and notes |
|---|---|---|---|
| RTX 3090 Ti 24 GB, WSL2 | SGLang for supported multi-agent/shared-prefix workloads | vLLM for compatibility and controlled A/B; TensorRT-LLM only after a winner; llama.cpp for Bonsai | No native FP8 tensor compute. Use proven AWQ/GPTQ/Marlin/GGUF INT4 artifacts. Do not allocate 262K simply because a card says it exists. |
| M1 Pro 16 GB | oMLX `v0.5.1` for serving/cache/batching; raw MLX for kernels/conversion | llama.cpp Metal for cross-runtime and publisher MLX/GGUF artifacts; LiteRT-LM `v0.14.0` only as an artifact-specific control | Ordinary 27–35B Q4 is not the normal lane. Prefer Needle, Qwen/Agents 4B-class candidates, Trinity Nano, LFM, and only the experimental Bonsai 27B MLX 1-bit exception. Coordinate with the existing Mac owner; no remote mutation from this plan. |
| Galaxy S21 Ultra | No winner before probe: Cactus 2.0.1 CPU vs MNN 3.6.0 CPU/OpenCL/Vulkan/QNN where supported vs llama.cpp CPU vs LiteRT-LM 0.14.0 for exact official artifacts | MLC and ExecuTorch controls; GPU backends only after driver/capability probes | Probe exact SKU, RAM, Snapdragon-vs-Exynos, Android build, OS-available memory, battery health, and sustained thermals. Gemma E2B/E4B LiteRT rows are feasibility-only. Generic inference has no standard foreground-service type: use only a user-started, foreground-visible/kiosk session with short checkpointable leases. |
| iPhone 17 Pro Max | No winner before probe: Cactus 2.0.1 Metal vs MLX Swift LM 3.31.4 vs MNN 3.6.0 Metal vs llama.cpp Metal vs LiteRT-LM 0.14.0 for exact official artifacts | MLC Metal and ExecuTorch/Core ML controls | LiteRT Swift is early preview. Apple publishes no RAM value; query per-process available memory and Metal's recommended working set. Gemma E2B/E4B LiteRT rows are feasibility-only. Cactus 2.0.1 removed Core ML, so its Metal path is not an ANE/Core ML result. Operate foreground/docked and stop on lifecycle, low-power, or thermal signals. |
| Optional GTX 1080 Ti 11 GB | None in Phase 1 | Future independent llama.cpp CUDA-12.x replay, embedding, rerank, draft, or verifier service | Never tensor-parallel with the 3090 Ti. Current vLLM excludes sm_61, modern TRT-LLM is not its lane, and CUDA 13 removed Pascal targeting. Install only after a timing/energy simulation shows positive fleet goodput and PSU/slot/case/thermal checks pass. |

Runtime versions in `config/heterogeneous_tournament.yaml` are reproducibility
pins, not moving “latest” aliases. In particular, llama.cpp `b10012` remains an
intentional frozen candidate even when newer tags exist; refreshing it requires
a new source snapshot, compatibility review, and distinct tournament cell.

The Needle repository is MIT-licensed. The Cactus runtime is source-available
under different terms: personal, educational, research, and non-commercial use
is permitted, while organizations must satisfy both the under-$2M funding and
under-$2M annual-revenue thresholds or obtain a commercial license. Record the
actual deployment context and approve that license separately before a phone
runtime is installed.

Phones are untrusted burst workers, not authoritative agent hosts. The desktop
coordinator owns scheduling and verification; a phone may pull an outbound-only
lease containing separate job, lease, model, artifact, runtime, and config
identifiers/hashes, bounded context and output, deadline, and nonce, but no
workload secrets. Initial tasks are Needle routing, schema/tool
choice validation, deterministic classification/verification, embedding or
reranking, and short 0.5–4B public/synthetic replay. The only larger-model
exception is an explicitly marked, official-artifact Gemma E2B/E4B LiteRT
feasibility cell; it cannot be promoted to the normal worker lane. Phones receive no shell,
side-effecting tools, private ChatGPT corpus, arbitrary downloads, or cloud
handoff. The transport must be authenticated TLS or an authenticated Tailscale
path using device-scoped, short-lived credentials that are not embedded in the
workload lease; lease IDs/nonces provide replay protection. Content hashes are
integrity identifiers, not device authentication. Results return as
content-hashed ATIF/trial bundles with required local latency, memory, thermal,
battery, and lifecycle telemetry and are revalidated centrally. External/vendor
telemetry remains disabled.

The Mac/oMLX endpoint also binds to loopback by default. Any tailnet exposure
requires an API key plus deny-by-default Tailscale Grants restricted by device
tag and port; downloader and administrative surfaces remain unexposed.

## Runtime selection protocol

For each model artifact, run an identical request corpus in this order:

1. Confirm tokenizer/chat template, reasoning parser, tool-call parser, stop
   tokens, and structured-output behavior with a CPU/Transformers reference.
2. Run the lowest-friction supported production engine. On the 3090 Ti this is
   usually SGLang and on the Mac it is oMLX after owner handoff. Phones have no
   default until the Cactus/MNN/llama.cpp/LiteRT-LM/MLX Swift tournament is
   measured on an exact supported artifact.
3. Run the designated control engine on the same artifact/quantization when
   possible. If formats differ, record that as a confound rather than claiming
   an engine-only comparison.
4. Promote to TensorRT-LLM or a custom kernel only when the model is already on
   the quality Pareto frontier and profiles identify recoverable latency.
5. Reject a runtime/model pair on silent parser corruption, invalid tools,
   unstable memory, repeatable OOM, missing license metadata, or a material
   quality loss not offset by the program's north-star metric.

MoE active-parameter counts predict arithmetic per token, not storage fit.
Always budget total weights, quant metadata, vision modules, runtime workspace,
KV cache, draft/MTP weights, and concurrent requests.

## Machine-readable review checkpoint

`config/heterogeneous_tournament.yaml` now encodes the device/runtime policy,
runtime pins, ADR-locked controls, candidate architecture/parameter bounds,
license/execution gates, and acceleration order. It is structurally incapable
of authorizing a download, server, phone/Mac mutation, or 1080 Ti install.

The candidate rows now name exact official Gemma repositories and exact
publisher Bonsai artifacts instead of overview/demo-only keys. The completed
metadata-only refresh resolves immutable revisions for all 25 tournament rows,
including LFM2.5 1.2B, Gemma E2B/E4B/12B, North Mini Code, GLM-4.7-Flash,
Qwen3.5 4B/9B, Agents-A1-4B, Ornith 35B, and Trinity Mini/Nano. The review has
25 immutable rows, zero missing, and zero mutable. The
derived review was regenerated at
`state/evidence_registry/reviews/2026-07-14-tournament.json`; every candidate
remains execution- and license-gated with `promotion_authorized: false`.
