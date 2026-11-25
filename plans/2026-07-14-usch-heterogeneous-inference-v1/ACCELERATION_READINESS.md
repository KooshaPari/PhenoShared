# Acceleration readiness and kernel gates

“Lossless” below means the verifier samples from the target distribution under
the method's assumptions. It does not excuse parser bugs, floating-point drift,
seed mismatch, an incompatible draft checkpoint, or a changed target quant.

## Readiness table

| Technique | What it actually does | July 2026 readiness for this fleet | First decision |
|---|---|---|---|
| Prefix/Radix/APC caching, chunked prefill, cache-aware routing | Reuses deterministic prompt/KV prefixes and controls prefill/queue cost | **Production baseline.** Native mechanisms exist in SGLang/vLLM; oMLX provides prefix sharing plus hot RAM/cold SSD KV tiers. | Implement/measure before speculative work. Be explicit that oMLX “SSD cache” means solid-state storage, not Speculative Speculative Decoding. |
| Prompt n-gram/suffix speculation | Reuses prompt-local token sequences with no draft weights | **Production baseline** where runtime supports it; especially useful for code/repetition. | First no-training speculative A/B. Disable when acceptance is low. |
| Native MTP/NextN | Uses model-trained future-token heads | **Production candidate** for Qwen3.6/Gemma 4 and matched models in current runtimes. | First learned speculative A/B because target/draft compatibility is explicit. Batch-1 MoE verification can erase gains; measure. |
| EAGLE/P-EAGLE family | Hidden-state-conditioned autoregressive draft heads | **Mature control** for matched checkpoints, not the whole frontier. Gemma 4 12B now has a published [EAGLE3 drafter](https://huggingface.co/deepseek-ai/eagle3_gemma4_12b_ttt7) at `0bc24c312350910419cf371e54082f040d65cc82`, and [vLLM support](https://github.com/vllm-project/vllm/pull/39450) is merged at `e7cfd7c5b9a18c4fb6eb7dd3108002793989e0eb`. | Establish a known learned-draft baseline before custom research. For Gemma 12B, pin target, Q4/target artifact, drafter, runtime, parser, and combined headroom; absent drafter-license metadata blocks execution. |
| [DFlash](https://arxiv.org/abs/2602.06036) | Lightweight block-diffusion drafter proposes a block in one pass, target verifies | **Current model-specific candidate.** Current paths exist in vLLM (minimum `0.20.1` for this matrix), SGLang, llama.cpp, oMLX, and MNN 3.6.0; TRT-LLM exposes it in the 1.3 RC line rather than the stable line. Laguna's [BF16](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash) and [FP8](https://huggingface.co/poolside/Laguna-XS-2.1-DFlash-FP8) drafters are released, while vLLM [DFlash](https://github.com/vllm-project/vllm/pull/46853) and [tool-parser](https://github.com/vllm-project/vllm/pull/47311) fixes are merged at `4c3c64fcf76450d3d0bbfd3d1725eade0f214710` and `258f8de91f99b40a4dfb234e55a09e9493c6ece8`. Gemma 12B's [DFlash drafter](https://huggingface.co/deepseek-ai/dflash_gemma4_12b_block7) is at `7490ce60c7630107917fe558e2bbe3dcec6195cb`, with [SGLang support](https://github.com/sgl-project/sglang/pull/27471) merged at `5ea0d1d093819213f1953275362029dbc91633be`. | Test only a published matched target/drafter/runtime cell. Laguna still needs an Ampere-fitting target quant plus combined target/draft/KV headroom, parser, acceptance, and quality probes; FP8 is not native tensor compute on SM86. Gemma 12B has the same target/quant/drafter-license/headroom gates. MNN support is not evidence that every mobile model has a compatible drafter. |
| [DSpark](https://github.com/deepseek-ai/DeepSpec) | Confidence-scheduled speculative drafting and adaptive verification | **Released checkpoints, method-specific runtime truth.** DeepSpec is pinned at `005e03b81cec38b7da6399833d609ee89a2587f2`. The merged generic [vLLM integration](https://github.com/vllm-project/vllm/pull/46995), commit `f5a8d73377d0f0a4e00cba172f9fbd0d50471b07`, covers published Qwen3 4B/8B/14B controls and DeepSeek-V4. Gemma 12B has a published [DSpark drafter](https://huggingface.co/deepseek-ai/dspark_gemma4_12b_block7) at `2fa72e765eec2965fc4d86a8663ce6769eba6218`, but its [vLLM integration](https://github.com/vllm-project/vllm/pull/47216) remains open at head `599cd0f51a458e061a257898d0564d54c98d9c40`. No Qwen3.5/3.6 checkpoint was resolved, and public SGLang release/docs do not establish a stable DSpark path. | Use Qwen3 4B/8B/14B and DeepSeek-V4 only as released control lanes. Gemma 12B DSpark remains research-only until the exact PR/commit is accepted and pinned. Drafter license metadata is absent; pin code, target, drafter, license decision, runtime, and headroom before any benchmark. |
| [DFlare](https://arxiv.org/abs/2606.02091) | Scales DFlash capacity via layer-wise target-feature fusion | **Released custom research path, not stock serving support.** [AngelSlim code](https://github.com/Tencent/AngelSlim), [documentation](https://angelslim.readthedocs.io/zh-cn/latest/features/speculative_decoding/dflare.html), and Qwen3-4B/8B plus GPT-OSS-20B heads are public. The released flow remains a custom PyTorch benchmark/training path rather than stock vLLM or SGLang. | Keep it in S7 until DFlash wins locally; then reproduce one exact released head/target pair before considering engine integration. |
| [DDTree](https://arxiv.org/abs/2604.12989) / [CaDDTree](https://arxiv.org/abs/2606.01813) | Builds diffusion candidate trees; CaDDTree chooses structure/budget using measured draft/verify cost | **Research branch.** CaDDTree is a successor, not another name for DDTree. The cost-aware budget is attractive because it matches the harness north star. | Replay recorded per-round distributions/latencies offline before touching an engine. |
| [DominoTree](https://arxiv.org/abs/2607.08642) | Uses conditional tree-structured drafting with Domino for same-request speculative decoding | **Paper/reference-code review only.** Its [reference repository](https://github.com/slin-zhq/Domino-Tree) is a separate method; it is not diffusion DDTree/CaDDTree and is not the unrelated Domino repository. | Keep in the offline trace-simulator lane until exact code/artifacts/runtime support and explicit approval exist. Do not merge its results or name with DDTree. |
| [JetSpec](https://arxiv.org/abs/2606.18394) | Causal parallel draft head creates branch-conditioned trees in one pass | **Research/custom integration.** Paper includes a vLLM integration but not a general released drop-in path for the tournament. | Only after native MTP/EAGLE/DFlash baselines; requires matched training/head artifacts. |
| [Speculative Speculative Decoding](https://arxiv.org/abs/2603.03251) (SSD/Saguaro) | While the target verifies, a drafter anticipates likely verification outcomes and pre-drafts branches, overlapping draft and verify | **Lab only here.** Reference repo is oriented to Python 3.11, CUDA 12.8+, Qwen3/Llama examples and H100-class multi-GPU layouts, including a separate draft GPU. | Do not map it to cache reuse. First build a timing simulator; later a separate-helper prototype. The 1080 Ti reference stack is unsupported. |
| [TurboQuant](https://arxiv.org/abs/2504.19874) | Rotates/low-bit-compresses KV storage, then dequantizes for attention | **Usable but conditional in stock vLLM.** The upstream cells are explicitly `turboquant_k8v4` and `turboquant_4bit_nc`; they are not evidence that a TurboQuant+ codec or llama.cpp CLI is present. | Use only when KV capacity/queueing is measured as the bottleneck. Compare BF16/FP8-storage/stock-TurboQuant on the 3090; H100 conclusions do not transfer to Ampere. |
| [TurboQuant+](https://github.com/TheTom/turboquant_plus) | Community extensions/forks explore asymmetric K/V and additional codecs, kernels, and CUDA/Metal/llama.cpp paths | **Community-fork research, separately pinned.** It is not the stock vLLM TurboQuant implementation. CLI names and codec availability are fork-specific. | Resolve an exact fork commit, build, and supported flags before command generation. Never label stock vLLM results “TQ+” or carry a community codec name into upstream vLLM. |
| [RotorQuant/PlanarQuant/IsoQuant](https://github.com/scrya-com/rotorquant) | Replaces TurboQuant's global transform with small 2D/4D block rotations intended to reduce online transform cost | **Fork-level research comparator.** The repository has CUDA/Metal code but no releases; its headline end-to-end results are creator measurements on RTX 5090. The IsoQuant paper explicitly limits its validation to synthetic stage-1 quantize/dequantize kernels. | Only compare in the same pinned llama.cpp fork, artifact, context, and quality suite after TurboQuant is locally useful. Treat upstream vLLM support as absent while its request remains an issue. |
| [SpectralQuant](https://github.com/Dynamis-Labs/spectralquant) | Fits an offline eigenspectral basis and allocates correction/bit budget to high-information KV dimensions | **Paper/repository watchlist.** The public repo is a NeurIPS 2026 submission with no arXiv identifier, package release, or production serving integration; reported experiments used B200-class infrastructure. | Preserve as a hypothesis from the local ChatGPT corpus. Do not promote until a released runtime path and independent end-to-end agent-quality evidence exist. |
| [OSCAR](https://arxiv.org/abs/2605.17757) | Fits attention-aware K/V covariance rotations offline and stores most cache in INT2 while retaining BF16 sink/recent windows | **Released research system, off the first hardware lane.** The public SGLang fork currently documents H100/CUDA 12.8+ requirements; its llama.cpp Metal work is a separate feature branch. Qwen3.5 hybrid support remains preview. | Consider only after ordinary KV4/TurboQuant tests show a capacity bottleneck and a supported finalist exists. Pin calibration data and rotation hashes; never reuse a rotation across a merely similar checkpoint. |
| [VeriCache](https://arxiv.org/abs/2605.17613) | Drafts with compressed KV, then verifies with full KV to catch divergence that aggregate similarity can miss | **Paper watchlist only.** No public implementation was found, so this is not a runnable integration. Its verification framing is relevant to code/tool workloads where one changed argument or patch token can be catastrophic. | Require released/pinned code first, then greedy-output identity, exact tool-argument match, patch parse/tests, long-generation divergence bounds, deterministic cache correctness, and concurrency/P99/VRAM measurements. |
| [TiDAR](https://arxiv.org/abs/2511.08923) | A single trained hybrid architecture drafts in diffusion and samples autoregressively in one forward pass | **Architecture/training research, not a retrofit.** | Watch available weights/runtime support; no custom training until ordinary serving baselines are stable. |
| [LatentMAS](https://arxiv.org/abs/2511.20639) | Shares last-layer latent working memory between compatible agents instead of serializing all collaboration to text | **Research orchestration A/B.** Creator token/speed/quality gains are [C]; cross-family hidden spaces are not interchangeable. | Same-backbone single vs TextMAS vs LatentMAS only. Keep heterogeneous agents textual. Measure code/tool outcomes, not token reduction alone. |
| [dMoE](https://arxiv.org/abs/2605.30876) | Routes diffusion-model blocks to a coherent expert set to reduce unique expert loads | **Training/architecture research, not post-hoc MoE optimization.** | Watch; do not label it an inference switch for Qwen/Laguna/Gemma checkpoints. |
| [SpecMoE](https://arxiv.org/abs/2604.10152) | Uses self-assisted speculative decoding to accelerate MoE inference | **Paper-only MoE speculation.** No public pinned implementation or exact supported tournament checkpoint has cleared review. It is distinct from expert prefetching. | Consider only if a finalist spills experts, a public implementation supports the exact architecture, and an offload bottleneck is measured; explicit approval remains required. |
| [Speculating Experts](https://arxiv.org/abs/2603.19289) | Predicts and prefetches future MoE experts to overlap CPU→GPU transfer | **Relevant research for offloaded MoE.** Creator reports up to 14% TPOT reduction [C]. | Consider only if a finalist actually spills/offloads experts and transfer stalls dominate its trace. Wrong expert execution can alter quality. |
| Needle | Single-shot function-call specialist; pinned HF artifact totals 30,427,676 parameters while the repository describes it as ~26M | **Mobile/router experiment**, not token speculative decoding. Needle itself is MIT; the Cactus runtime has separate source-available personal/non-commercial and organization-size terms. | Complete the Cactus license gate, then compare router+fallback verified success/cost with direct worker calls. |
| Bonsai low-bit + KV4 | Very low-bit weights with optional low-bit KV | **High-priority experimental artifact path.** Backend support is split between upstream and Prism forks. No Qwen3.6 DSpark checkpoint was resolved, so Qwen ancestry does not make Bonsai a DSpark target. | Reproduce ordinary AR quality first, then KV4. Keep DSpark out unless an exact Bonsai target/drafter artifact is released and verified. |

## TurboQuant-specific decision

The [vLLM May 2026 study](https://vllm.ai/blog/2026-05-11-turboquant)
found that `4bit-nc` can provide up to about 3.4x KV capacity but usually costs
1–4 quality points plus latency/throughput; more aggressive 3-bit modes caused
much larger reasoning/coding degradation. Those performance experiments used
H100s, where native FP8 attention makes FP8 an unusually strong baseline. The
3090 Ti lacks native FP8 tensor cores, so this fleet must measure:

1. BF16 KV storage/attention baseline;
2. any runtime-supported FP8 KV storage path, including dequant overhead;
3. stock-vLLM `turboquant_k8v4` and `turboquant_4bit_nc` only, reported as
   TurboQuant rather than TurboQuant+;
4. coding/tool/retrieval quality at 4K, 16K, and the first context length where
   memory pressure changes queueing;
5. concurrency and P99 TTFT, because TQ's value is capacity under pressure, not
   faster single-request decoding.

Do not run 3-bit modes in production. They may remain a clearly labeled
research cell after 4-bit passes.

## Speculative benchmark cells

For one quality-approved, matched target artifact per runtime, execute:

| Cell | Decode mode | Purpose |
|---|---|---|
| S0 | no speculation | Exact latency/quality/cache baseline. |
| S1 | n-gram/suffix | Weight-free control. |
| S2 | native MTP/NextN | Lowest-friction trained-draft path. |
| S3 | EAGLE/P-EAGLE or other released matched head | Mature learned control. |
| S4 | matched DFlash | Parallel block-draft test. |
| S5 | matched DSpark | Method-specific released controls: Qwen3 4B/8B/14B and DeepSeek-V4 on the merged generic vLLM path. Gemma 12B remains research-only behind its open vLLM PR; no inferred Qwen3.5/3.6 or SGLang support. |
| S6 | Other released family-specific method | Only with an exact target/drafter artifact and supported runtime; no ancestry-based proxy pairing. |

For each cell collect concurrency 1/2/4/8, input/output buckets 256/256,
1K/512, 4K/1K, and representative agent traces. Report accepted tokens per
verification, draft time, verifier time, rejection waste, ITL, TTFT, goodput,
VRAM, and task/tool quality. A speedup measured only on synthetic token streams
does not promote the method.

DDTree/CaDDTree, DominoTree, JetSpec, DFlare, SSD, SpecMoE, Speculating
Experts, Rotor/Planar/IsoQuant, SpectralQuant, and OSCAR enter an isolated S7
research lane only after S0–S6 are reproducible. Distinct methods retain
distinct cells and names.

## Custom kernel language/backend gate

Use the runtime's existing profiler before selecting a language. The work item
must name:

- the operation and exact shape/dtype/layout distribution;
- percentage of end-to-end wall time and memory traffic;
- reference implementation and numeric/error tolerance;
- target platforms and expected maintenance surface;
- a rollback/fallback path and fuzz/differential tests;
- expected improvement to accepted verified steps/s/GB/$.

Backend choice follows the hotspot:

- **CUDA C++/Triton/CUTLASS** for the 3090 Ti hot path when the existing engine
  can load the kernel and Ampere-specific memory/tensor-core behavior matters;
- **Metal/MLX custom kernels or MLX Swift** for Apple hot paths;
- **C++ ARM NEON/Metal** inside Cactus for phones;
- **Vulkan/WGPU** only when cross-device deployment value outweighs lower
  specialization and integration overhead. WGPU is a kernel substrate, not an
  inference runtime; exhaust native MNN/llama.cpp/Cactus backends first;
- **Rust/Zig/C++** for safe, low-overhead runtime/control-plane or portable
  kernels when FFI and ecosystem fit are strong;
- **Mojo/Nim/Vale/Pony/Carbon or other experimental languages** only with a
  demonstrated compiler/runtime advantage, stable interop, reproducible build,
  and no degradation in deployability. Novelty is not a benchmark result.

No kernel project starts before the no-spec serving baseline, cache profile,
and operation-level trace exist.
