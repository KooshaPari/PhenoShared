# Research audit

Base cutoff: 2026-07-14 (America/Los_Angeles)

Runtime delta checked: 2026-07-19 (America/Los_Angeles)

## Method

This audit used creator model cards, official runtime documentation/releases,
paper and project repositories, arXiv, and live GitHub metadata. Model cards and
papers establish what to test; they do not establish performance on the local
fleet. Reddit and similar community sources belong in a separate anecdote index
and cannot promote a model or optimization without primary evidence and local
reproduction.

The most time-sensitive facts were read on the cutoff date. Store a retrieval
timestamp and content/revision hash when turning any source into a registry row.

## Runtime snapshot [V]

| Runtime | Current verified release | Planning consequence |
|---|---:|---|
| [SGLang](https://github.com/sgl-project/sglang/releases/tag/v0.5.15.post1) | `v0.5.15.post1`, 2026-07-14 | Current code/release line, not the repo's stale `0.5.14` assumption. Primary 3090 Ti multi-agent candidate. |
| [vLLM](https://github.com/vllm-project/vllm/releases/tag/v0.25.1) | `v0.25.1`, commit `752a3a504485790a2e8491cacbb35c137339ad34`, 2026-07-14 | Reference/control engine and active DFlash/speculator lane. |
| [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v1.2.1) | stable `v1.2.1`, 2026-04-20; DFlash research pin `1.3.0rc20` | Stable lacks some launch-day models. The **TensorRT-LLM** Laguna/DFlash lane requires at least the audited 1.3 RC feature line and remains pre-release; this does not describe the separate released vLLM lane. |
| [MLX](https://github.com/ml-explore/mlx/releases/tag/v0.32.0) | `v0.32.0`, 2026-07-07 | Raw Metal/kernel lane on Apple Silicon. |
| [mlx-lm](https://github.com/ml-explore/mlx-lm/releases/tag/v0.31.3) | `v0.31.3`, 2026-04-22 | Baseline MLX generation library. |
| [oMLX](https://github.com/jundot/omlx/releases/tag/v0.5.1) | `v0.5.1`, 2026-07-12 | Preferred Mac serving lane: continuous batching, OpenAI/Anthropic APIs, prefix sharing, and RAM/SSD KV tiers. |
| [Cactus](https://github.com/cactus-compute/cactus/releases/tag/v2.0.1) | `v2.0.1`, commit `7e7eada40c387736dec138db003ab38f028f3a15`, 2026-07-09 | Mobile runtime candidate, not the preselected phone winner. This release explicitly removed Core ML, so its iOS path must not be credited to ANE/Core ML. |
| [MNN](https://github.com/alibaba/MNN/releases/tag/3.6.0) | `v3.6.0`, commit `cc20f672af9e177e2fa338c332dc097de2fc9264`, 2026-06-16 | Major missing mobile comparator: ARM low-bit kernels plus OpenCL/Metal/Vulkan, QNN work, Qwen3.5/Gemma4 support, and a DFlash path. Exact device/model support still requires a probe. |
| [ExecuTorch](https://github.com/pytorch/executorch/releases/tag/v1.3.1) | `v1.3.1`, commit `e2f18eb23c45bd22ca332b0b8b49a81de304b472`, 2026-05-29 | Mobile integration control spanning XNNPACK, Vulkan, QNN, Metal, and Core ML, with experimental/model-specific MLX-delegate work; release support is not equivalent to a tuned artifact on either phone. |
| [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM/releases/tag/v0.14.0) | `v0.14.0`, commit `80f301ff9a3b02c2c1e7be2dd1a567752f7b51b6`, 2026-07-08 | Official Google mobile-artifact lane. Kotlin/C++ are stable while Swift is an early preview, so Android and iOS remain distinct feasibility cells with foreground, lifecycle, memory, and thermal gates. |
| [MLX Swift](https://github.com/ml-explore/mlx-swift/releases/tag/0.31.6) / [MLX Swift LM](https://github.com/ml-explore/mlx-swift-lm/releases/tag/3.31.4) | `0.31.6` / `3.31.4` | Native Apple control for foreground iPhone inference and artifact-specific Mac tests. |

Current [vLLM GPU requirements](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
say NVIDIA compute capability 7.5 or newer. The RTX 3090 Ti (8.6) qualifies;
the GTX 1080 Ti (6.1) does not. vLLM is also Linux-native, so the desktop lane
runs under WSL2/Linux rather than native Windows. [I]

[TensorRT-LLM's current speculative-decoding documentation](https://nvidia.github.io/TensorRT-LLM/1.3.0rc20/features/speculative-decoding.html)
includes a DFlash configuration, but that URL is an `1.3.0rc` line, not stable
`1.2.1`. Treat the exact model/parser/runtime combination as pre-release until
tested. [V]

### 2026-07-19 append-only delta [V]

- No release newer than `v0.5.15.post1` for SGLang or `v0.25.1` for vLLM was
  present on their official release pages.
- TensorRT-LLM [`v1.3.0rc21`](https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v1.3.0rc21),
  commit `1662a87`, was released 2026-07-15. It adds Qwen3.5/3.6 MoE piecewise
  CUDA graphs, broadens dynamic speculation, and includes EAGLE correctness
  fixes. It remains pre-release and lists a Qwen3.5 FP4 failure on 8xB200. The
  isolated research pin advances to rc21, but the stable comparison line and
  SGLang/vLLM-first trial order do not change; none of these release notes prove
  SM86 performance.
- [`prism-ml/Bonsai-27B-gguf`](https://huggingface.co/prism-ml/Bonsai-27B-gguf)
  advanced from audited head `0cf7e3d21581b169b4df1de8bf01316000e2fbb7`
  to `f10afb355f104535e3e3e98cf7ab7795c72bd292` on 2026-07-17. The publisher
  commit adds community-evaluation YAML (AIME 2026, GSM8K, and MMMU-Pro), not a
  declared weight/runtime change. Classify it as metadata/eval-only and require
  artifact-identity re-verification before use; retain the historical pin above.
- The checked Qwen3.6, Ornith, Bonsai AWQ, ZAYA1, Nanbeige4.1, and Needle
  publisher heads did not move. No new official <=12B or <=35B checkpoint
  changed the July-18 shortlist or its ordering.

## Model/artifact correction snapshot [V]

Repository identity is exact below. A full immutable revision is recorded only
when the audit captured all 40 hexadecimal characters; abbreviated card/API
prefixes remain resolution-required and were not expanded by guesswork.

| Family | Publisher artifacts and audited identity | Planning consequence |
|---|---|---|
| Agents-A1-4B | [`InternScience/Agents-A1-4B`](https://huggingface.co/InternScience/Agents-A1-4B) at `945c40a4aa6f534d434a353207b8d42ecf7a5293`; publisher [`Q4_K_M GGUF`](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF) at `d92b02e27074b27542384f72bc0e72203c970f0f` | Dense 4,539,265,536 parameters, 262K context, Apache-2.0 declared. SGLang/vLLM and llama.cpp Q4 are separate artifact/runtime cells; it exceeds the normal 4B phone cap. |
| Ornith 35B | [`deepreinforce-ai/Ornith-1.0-35B`](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B) at `5df2ed3f675c7beaa490328cc70bb573b65fb660`; publisher [`GGUF`](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B-GGUF) at `c2e1703039380de4ce6820e97afd185682d3c16c` | 35B-A3B MoE, MIT declared. The publisher provides SGLang >=0.5.9 and vLLM >=0.19.1 recipes for the canonical model, and the pinned current releases contain its exact `Qwen3_5MoeForConditionalGeneration` architecture. The demonstrated recipe is TP8 on 8x80GB, not a 3090 fit result. The separate Q4_K_M is about 19.71GiB, so every 3090 cell retains exact quant, parser, and measured KV-headroom gates. |
| Bonsai 27B | [`AWQ 4-bit`](https://huggingface.co/prism-ml/Bonsai-27B-AWQ-4bit) at `8baf59aa28757e62fd4ada0600b70de3a10b4e78`; publisher [`GGUF`](https://huggingface.co/prism-ml/Bonsai-27B-gguf) at `0cf7e3d21581b169b4df1de8bf01316000e2fbb7`; [`MLX 1-bit`](https://huggingface.co/prism-ml/Bonsai-27B-mlx-1bit) at `ef22f239c670078e1507f9769bcaa66657332b96` | Dense 27,356,728,560 parameters, Apache-2.0 declared. Use AWQ/SGLang, custom GGUF/llama.cpp, and MLX as distinct cells. The demo repo is implementation evidence only. |
| LFM2.5 1.2B | [`LiquidAI/LFM2.5-1.2B-Instruct`](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) at `868df74dd56ff8a0c2ac5dbf281690c2dbebe4c9`; publisher [`GGUF`](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF) at `047e06635fbe71469926b35ea414537245218200`; publisher [`MLX 4-bit`](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-MLX-4bit) at `c30e30c5efac705771e1f37df38a32115718dd5d` | All-device fast/tool-control candidate, including the normal phone lane. Exact artifact/runtime/parser support, license review, device memory, lifecycle, and thermal probes remain closed gates. |
| Gemma 4 edge | [`E2B`](https://huggingface.co/google/gemma-4-E2B-it) at `9dbdf8a839e4e9e0eb56ed80cc8886661d3817cf`; Google [E2B mobile-training artifact](https://huggingface.co/google/gemma-4-E2B-it-qat-mobile-transformers) at `9fcec64df66cb1e4d972fc5cdc142afb25b2362c`; official [E2B LiteRT artifact](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) at `9262660a1676eed6d0c477ab1a86344430854664`; [`E4B`](https://huggingface.co/google/gemma-4-E4B-it) at `a4c2d58be94dda072b918d9db64ee85c8ed34e3f`; Google [E4B mobile-training artifact](https://huggingface.co/google/gemma-4-E4B-it-qat-mobile-transformers) at `9a78a5adac7bca7a9e421634e4b58f41ca7cbca3`; official [E4B LiteRT artifact](https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm) at `f7ad3343bd6ebc9607f4dc3bc4f2398bd5749bc5` | E2B stores 5,123,178,051 parameters despite its effective-size label. Its 2,588,147,712-byte `.litertlm` blob is pinned by SHA-256 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`; E4B's 3,659,530,240-byte blob is pinned by `0b2a8980ce155fd97673d8e820b4d29d9c7d99b8fa6806f425d969b145bd52e0`. These public, ungated Apache-declared artifacts replace a terms-acceptance assumption with ordinary license review, but both phone lanes are explicit feasibility-only exceptions, not normal-worker admission. |
| Gemma 4 12B | [`google/gemma-4-12B-it`](https://huggingface.co/google/gemma-4-12B-it) at `0e2b1058541244490925fbacf8972041435691ac`; publisher [`QAT Q4 GGUF`](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf) at `2b318d6ebebf093f50ca4376e858325f10703358` | Dense 11,959,730,224-parameter target. The Q4 blob is 6,975,877,728 bytes with SHA-256 `faff1a63667fac17ac5e777f47114688fcefea96e220e211aaa8d62c2c4561f1`. Released drafters exist, but runtime support is method-specific and drafter license metadata is absent; exact target/quant/draft license, parser, and combined-headroom gates remain closed. |
| Gemma 4 26B | [`26B`](https://huggingface.co/google/gemma-4-26B-A4B-it) at `5305c1e72ea29c01f31a81230d52b375ba88b409`; publisher [`26B QAT Q4 GGUF`](https://huggingface.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf) at `21bfe2a8c89118c9a1a2aa242934fc4d1c0fff15` | Stores 26,544,131,376 parameters with about 3.8B active. Declared-license review, parser, exact artifact/runtime, and measured headroom remain gates; no terms-acceptance prerequisite is inferred. |
| North Mini Code 1.0 | [`CohereLabs/North-Mini-Code-1.0`](https://huggingface.co/CohereLabs/North-Mini-Code-1.0) at `d11e61a842617a22dc328552fa5bb86231ee4f37`; official [`w4a16`](https://huggingface.co/CohereLabs/North-Mini-Code-1.0-w4a16) at `1e55f4aa327aba4c0b7a1da0d0f24626d3af5c90` | 30,484,303,872 total/~3B active, Apache-2.0 declared. The official NVFP4-style artifact is not a native SM86 compute advantage; a provenance-checked Ampere-fitting quant, current runtime, parser, and headroom probe are required. |
| GLM-4.7-Flash | [`zai-org/GLM-4.7-Flash`](https://huggingface.co/zai-org/GLM-4.7-Flash) at `7dd20894a642a0aa287e9827cb1a1f7f91386b67` | 31,221,488,576 total/~3B active, MIT declared. The card's SGLang/vLLM main-branch instructions are claims, not a released local cell; require a fitting quant, current-release/runtime probe, exact parser/tool-template validation, and headroom. |
| Laguna XS 2.1 | [`poolside/Laguna-XS-2.1`](https://huggingface.co/poolside/Laguna-XS-2.1) at `5e82aa8f740e86e9898e1f13a2a02683d167b8c7`; matched [BF16 DFlash](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash) at `2e783135b1590c16c392ad9613e427f1090daa48`; matched [FP8 DFlash](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash-FP8) at `546b72f86fc6733913fec0cb8a5d6c1cd4ce2895` | The model-specific DFlash pair is released and [vLLM support](https://github.com/vllm-project/vllm/pull/46853) plus the [tool-parser fix](https://github.com/vllm-project/vllm/pull/47311) are merged. This only opens a metadata candidate: the 3090 Ti still needs a provenance-checked Ampere target quant, combined target/draft/KV headroom, exact parser, acceptance, quality, and local runtime probe. FP8 draft weights do not create native FP8 tensor compute on SM86. |
| Qwen3.5 | [`4B`](https://huggingface.co/Qwen/Qwen3.5-4B) at `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`; [`9B`](https://huggingface.co/Qwen/Qwen3.5-9B) at `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | Exact audited counts are 4,659,865,088 and 9,653,104,368. Both are dense/MTP/262K candidates; neither belongs in a normal phone-worker lane. |
| Trinity | [`Mini`](https://huggingface.co/arcee-ai/Trinity-Mini) at `cdb81e8130815fec299cccc8f8700004b8366e1e` plus publisher [`GGUF`](https://huggingface.co/arcee-ai/Trinity-Mini-GGUF) at `a11737ef4b6f89d958d3f6ab670a9aa26e4b8ad7`; [`Nano Preview`](https://huggingface.co/arcee-ai/Trinity-Nano-Preview) at `b576b32b8bba7f5218312c9509e494537f8d282d` plus publisher [`MLX 5-bit`](https://huggingface.co/arcee-ai/Trinity-Nano-Preview-MLX-5bit) at `126a80bd8f729a016c9e994316a46c1e79d63282` | Mini is 26,123,974,400/~3B active and OpenMDW 1.1; Nano Preview is 6,120,003,328/~1B active and unstable. Mini is a 3090 control, Nano an M1-only experiment. |

The Qwen3.6 publisher size classes remain the 27B and 35B tournament boundary.
The 35B repository resolves to 35,951,822,704 tensor parameters. This is a
documented rounding case, not a change to the rule excluding families marketed
above 35B. A third-party INT4 cannot execute until its publisher/provenance,
conversion recipe, parser, and quality delta are recorded.

## Evaluation snapshot [V]

- [Terminal-Bench 2.1](https://www.tbench.ai/news/terminal-bench-2-1) was
  released 2026-05-06 and keeps 89 tasks. Official release material says 28
  tasks changed while the current repository README says 26; do not encode
  either prose count as evaluator truth. Pin and hash the actual task manifest
  at `harbor-framework/terminal-bench-2-1@36d417f56c293b8271b306a0e4c566f58e98c153`.
  Version 2.1 replaces 2.0 for primary measurement; 2.0 is historical only.
- [DeepSWE](https://github.com/datacurve-ai/deep-swe) has 113 original,
  long-horizon tasks across TypeScript, Go, Python, JavaScript, and Rust. It
  uses Harbor format and, since v1.1, a separate verifier environment requiring
  Pier 0.3.0+. Pin the current corpus at
  `datacurve-ai/deep-swe@6db64a40f3318d8659238ff34a8cc4b491c49205` and
  hash every selected task plus its verifier outputs.
- Terminal-Bench 3's repository is accepting/curating the next benchmark; keep
  it on a watchlist rather than pretending it is a stable primary suite.
- OpenAI's July 8 audit reports that about 30% of SWE-bench Pro is broken and
  reiterates that SWE-bench Verified no longer gives meaningful frontier SWE
  signal: [audit](https://openai.com/index/separating-signal-from-noise-coding-evaluations/).
  This supports the repository's existing decision to use SWE-bench only for
  harness regression/debugging.

## Local conversation corpus [L]

The configured Windows corpus contains 49 exports under
`D:\koosh\Downloads\ChatGPT-*.md` (the actual prefix is `ChatGPT-`, not
uppercase `CHATGPT-`). Reconciliation found 47 unique cryptographic hashes and
two duplicate groups; all 49 configured files are represented by the existing
50 local-corpus files representing 48 unique hashes, with no configured file
missing. These are
private class-[L] lineage inputs only. They guide hypotheses and evaluator
shape, while any time-sensitive model/runtime claim defers to the current
primary sources and immutable revisions in this audit. The high-value review
order is:

1. `ChatGPT-Agent-Aware Speculative Decoding.md`
2. `ChatGPT-Machine Comparison for AI.md`
3. `ChatGPT-VRAM and Scaling Factors (1).md`
4. `ChatGPT-Compression Pruning Review (2).md`
5. `ChatGPT-User-level Deterministic Cache.md`
6. `ChatGPT-Model Inference Costs 2026.md`
7. `ChatGPT-LatentMAS vs TextMAS comparison (1).md`
8. `ChatGPT-Agent Flow Optimization.md`
9. `ChatGPT-RLVR-AF Optimization Proposal (1).md` and
   `ChatGPT-Coding Agents and Intent Graphs (1).md`

Numbered newest variants should be preferred during eventual review. Deduplicate
by cryptographic hash before indexing, and do not copy raw private
conversations into public artifacts.

Durable corpus conclusions retained here:

- Instrument the gateway/replay/evaluator before choosing kernels. Log route,
  role, fresh/cached tokens, TTFT/inter-token latency distributions, validator
  result, repair attempts, fallback, final verified success, KV occupancy,
  cache hits, and speculative acceptance.
- Treat long context as a state-management problem: deterministic prefix reuse,
  Radix/APC/HiCache-style caching, hot-context reduction, chunked prefill, and
  prefill/decode isolation come before speculative decoding.
- Keep three capability tiers: 0.5–4B router/specialist, 8–12B worker, and
  26–35B escalation. Large models are scarce resources.
- Compare SGLang, vLLM, and TensorRT-LLM on identical traces. The corpus's
  disagreement over engine primacy is a reason for an A/B test, not a reason to
  choose by narrative.
- Custom CUDA/Metal/WGPU or exotic-language work must be triggered by a stable
  profiler hotspot, not curiosity alone.

## Fresh corrections to existing repository/corpus claims

| Existing claim/shape | Correction on 2026-07-14 |
|---|---|
| SSD is cache reuse across requests. | **False conflation.** Speculative Speculative Decoding overlaps drafting and verification and prepares branches for likely verifier outcomes, commonly on separate hardware. oMLX's “SSD cache” means solid-state-drive KV caching and is unrelated. |
| DFlash/DSpark/JetSpec are all absent from current serving engines. | DFlash is now documented or present in current vLLM/SGLang lines, and TRT-LLM exposes it in 1.3 RC docs. DSpark is method- and architecture-specific: the generic vLLM integration covers published Qwen3 4B/8B/14B controls and DeepSeek-V4, while Gemma 12B's DSpark runtime PR remains open. No Qwen3.5/3.6 DSpark checkpoint was resolved. JetSpec remains a research/custom integration lane. |
| Any DFlash draft can be paired with a nearby target. | Draft/target conditioning, tokenizer, hidden-state interface, vocabulary, and checkpoint compatibility are model-specific. Proxy pairings in the current YAML are hypotheses, not valid configurations. |
| TurboQuant is “zero loss.” | The paper reports quality neutrality at one setting, while current runtime measurements show quality/throughput trade-offs at more aggressive settings. Every bit width needs local coding/tool validation. |
| FP8 weights are a normal 3090 Ti optimization. | Ampere 3090 Ti has no native FP8 tensor cores. FP8 KV storage may still be testable through dequantizing kernels, but FP8 weight compute is not the default lane. |
| M1 Pro 16 GB can routinely host ordinary 27–35B Q4 models. | Ordinary 27–35B Q4 weights plus runtime/KV overhead are too tight. Bonsai's special 1/ternary-bit artifacts are an explicit experimental exception. |
| Phone “idle” means continuous background GPU inference. | iOS rejects new Metal work after backgrounding and may suspend the app. Android also restricts background foreground-service starts and requires declared service types; generic inference has no standard type. Use user-started foreground-visible, docked, checkpointable bursts with thermal/lifecycle cancellation. |
| `Vulkan`, `Metal`, `ONNX`, or `wgpu` is a serving runtime. | These are backends, formats/APIs, or kernel substrates. Compare actual runtimes—Cactus, MNN, llama.cpp, MLX Swift LM, MLC, or ExecuTorch—and record the backend separately. |
| A 1080 Ti can simply join the main serving stack or tensor parallel group. | Current vLLM excludes compute capability 6.1, TensorRT-LLM's modern path targets newer architectures, CUDA 13 removed Pascal compilation/library targets, and mixed 3090/1080 tensor parallelism would inherit the slow/unsupported path. Keep it absent; a future separate service requires isolated CUDA 12.x and a positive timing/energy model. |
| Needle is a generic 600M “failure gap” planner. | [Cactus Needle](https://github.com/cactus-compute/needle) is a tiny Simple Attention Network specialized for single-shot function calling. Its pinned HF artifact reports 30,427,676 parameters while the repository describes roughly 26M. It is a router/validator candidate, not a conversational planner or speculative decoder. |
| Needle and the Cactus phone runtime share one permissive license. | Needle is MIT, but the Cactus runtime uses separate source-available terms. Personal/educational/research/non-commercial use is permitted; organizations must be below both the stated $2M funding and $2M annual-revenue thresholds or obtain a commercial license. Deployment therefore needs its own license gate. |
| Bonsai 27B is an MoE because it is unusually small on disk. | The pinned Bonsai AWQ config proves a dense `Qwen3_5` architecture, but neither Qwen3.5 nor Qwen3.6 base ancestry is proven by the audited publisher metadata. Its experimental low-bit representations do not make it an MoE. |
| Gemma E2B is a sub-4B phone worker because of its name. | The official E2B checkpoint stores 5,123,178,051 parameters, so it remains excluded from normal phone lanes. Google now publishes exact E2B/E4 LiteRT-LM artifacts; those rows are narrow feasibility-only exceptions requiring the pinned `.litertlm` blob, LiteRT-LM `v0.14.0`, parser/tool, foreground/lifecycle, memory, and sustained-thermal probes. E2B is first; E4 is feasibility-only, not a fallback normal worker. |
| ZAYA has an official MLX path and works in a released SGLang wheel. | The audited publisher instructions still require creator forks. Keep ZAYA on the 3090 fork/upstream-release gate and do not claim an official MLX artifact. |
| Laguna's model-specific DFlash and fitting production INT4 are ready. | The BF16 and FP8 model-specific DFlash drafters are now released, and vLLM PRs `#46853` (DFlash) and `#47311` (tool parser) are merged. The fitting-production conclusion is still false: the official INT4 is too tight for useful 24GB headroom, the observed GGUF is about 18.88GiB before KV/runtime overhead, the BF16 draft adds pressure, FP8 is not native compute on SM86, and exact parser/acceptance/local-quality probes remain mandatory. |
| Any Agents-A1/Nex base-family quant and template can be reused. | Agents-A1 has publisher Q4 GGUF artifacts that should be tested with llama.cpp. Nex-N2-mini has no audited publisher quant and a template mismatch, so it stays metadata-only/execution-blocked. |

## Primary source set for model and mobile claims

- [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) and
  [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- [Laguna XS 2.1](https://huggingface.co/poolside/Laguna-XS-2.1), its
  [BF16](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash) and
  [FP8](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash-FP8) DFlash
  drafters, and vLLM [DFlash](https://github.com/vllm-project/vllm/pull/46853)
  and [tool-parser](https://github.com/vllm-project/vllm/pull/47311) merges
- [LFM2.5-1.2B-Instruct](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct)
  and [LFM2.5-8B-A1B](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B)
- [ZAYA1-8B](https://huggingface.co/Zyphra/ZAYA1-8B)
- [Agents-A1](https://huggingface.co/InternScience/Agents-A1),
  [Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B),
  [Nex-N2-mini](https://huggingface.co/nex-agi/Nex-N2-mini), and
  [Nanbeige4.1-3B](https://huggingface.co/Nanbeige/Nanbeige4.1-3B)
- [Gemma 4 E2B](https://huggingface.co/google/gemma-4-E2B-it), official
  [E2B](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) and
  [E4B](https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm)
  LiteRT-LM artifacts, [Gemma 4 12B](https://huggingface.co/google/gemma-4-12B-it),
  [Gemma 4 26B-A4B](https://huggingface.co/google/gemma-4-26B-A4B-it),
  [overview](https://ai.google.dev/gemma/docs/core),
  [MTP](https://ai.google.dev/gemma/docs/mtp/overview), and
  [function calling](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)
- [DeepSpec](https://github.com/deepseek-ai/DeepSpec/commit/005e03b81cec38b7da6399833d609ee89a2587f2),
  Gemma 12B [DFlash](https://huggingface.co/deepseek-ai/dflash_gemma4_12b_block7),
  [EAGLE3](https://huggingface.co/deepseek-ai/eagle3_gemma4_12b_ttt7), and
  [DSpark](https://huggingface.co/deepseek-ai/dspark_gemma4_12b_block7)
  drafters, SGLang's merged [Gemma DFlash](https://github.com/sgl-project/sglang/pull/27471),
  vLLM's merged [Gemma EAGLE3](https://github.com/vllm-project/vllm/pull/39450)
  and generic [DSpark](https://github.com/vllm-project/vllm/pull/46995), and the
  still-open [Gemma DSpark](https://github.com/vllm-project/vllm/pull/47216)
- [North Mini Code 1.0](https://huggingface.co/CohereLabs/North-Mini-Code-1.0)
  and [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash)
- [Bonsai 27B AWQ](https://huggingface.co/prism-ml/Bonsai-27B-AWQ-4bit),
  [GGUF](https://huggingface.co/prism-ml/Bonsai-27B-gguf),
  [MLX 1-bit](https://huggingface.co/prism-ml/Bonsai-27B-mlx-1bit), and
  [demo/runtime implementation](https://github.com/PrismML-Eng/Bonsai-demo)
- [Ornith-1.0-35B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B)
  and [publisher GGUF](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B-GGUF)
- [Trinity Mini](https://huggingface.co/arcee-ai/Trinity-Mini) and
  [Trinity Nano Preview](https://huggingface.co/arcee-ai/Trinity-Nano-Preview)
- [Cactus mobile runtime](https://github.com/cactus-compute/cactus),
  [Needle source](https://github.com/cactus-compute/needle), and its
  [HF artifact](https://huggingface.co/Cactus-Compute/needle)
- [LiteRT-LM `v0.14.0`](https://github.com/google-ai-edge/LiteRT-LM/releases/tag/v0.14.0)
- Apple's [background Metal guidance](https://developer.apple.com/documentation/metal/preparing-your-metal-app-to-run-in-the-background),
  [per-process available-memory API](https://developer.apple.com/documentation/os/os_proc_available_memory),
  and [recommended Metal working set](https://developer.apple.com/documentation/metal/mtldevice/recommendedmaxworkingsetsize)
- Android's [foreground-service overview](https://developer.android.com/develop/background-work/services/fgs),
  [background-start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start),
  and [thermal API](https://developer.android.com/games/optimize/adpf/thermal)
- [TensorRT-LLM support matrix](https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html)
  and [CUDA 13 release notes](https://docs.nvidia.com/cuda/archive/13.0.1/pdf/CUDA_Toolkit_Release_Notes.pdf)

All benchmark numbers from these pages retain evidence label **[C]** until the
same model revision, prompt template, parser, runtime, and evaluator are run by
this harness.
