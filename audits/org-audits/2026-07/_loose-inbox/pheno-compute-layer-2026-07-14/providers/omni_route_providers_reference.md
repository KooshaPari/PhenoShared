# OmniRoute Provider Reference Compilation

## 1. KV Cache Compression Tools
| Name | Type | Reference | Notes |
|------|------|-----------|-------|
| RotorQuant | Tool / Paper | `scrya-com/rotorquant` (GitHub) | Block-diagonal rotation for KV-cache compression |
| SpectralQuant | Tool / Paper | `Dynamis-Labs/spectralquant` (GitHub) | "3% Is All You Need: Breaking TurboQuant" |
| TurboQuant | Paper / Method | Google / arXiv:2504.19874 | Online vector quantization baseline |
| PagedAttention | Engine Feature | vLLM (`vllm.entrypoints.openai.api_server`) | KV cache management |
| RadixAttention | Engine Feature | SGLang (`sglang.launch_server`) | Prefix/KV caching |
| HiCache | KV System | Mentioned only | Hierarchical KV cache |
| Automatic Prefix Caching | Serving Optimization | Mentioned only | Reuse shared prefixes |
| IceCache | KV System | Mentioned only | Memory-efficient KV cache management |
| OrbitFlow | Research Method | Mentioned only | KV offloading / tiered memory |
| HillInfer | Research Method | Mentioned only | KV offloading / tiered memory |
| ParisKV | Research Method | Mentioned only | KV offloading / tiered memory |
| H2O | Method | Mentioned only | Additional KV method |
| SnapKV | Paper / Method | Mentioned only | KV pruning/compression method |
| StreamingLLM | Method | Mentioned only | Long-context KV handling |
| GEAR | Method | Mentioned only | KV-related method |
| DynamicKV | Method | Mentioned only | KV cache method |
| KIVI | Method | Mentioned only | KV cache method |

## 2. Training Stacks
| Name | Type | Reference | Notes |
|------|------|-----------|-------|
| axolotl | Training Stack | `OpenAccess-AI-Collective/axolotl` | Fine-tuning pipeline |
| trl | Training Stack | `huggingface/trl` | SFT / RLHF tooling |
| peft | Training Stack | `huggingface/peft` | Adapter fine-tuning / LoRA |
| LlamaFactory | Training Stack | Mentioned only | Referenced, no repo link given |
| Transformers | Library | HuggingFace `transformers` | Core model loading / inference |
| LoRA | Technique | Mentioned only | Adapter composition / fine-tuning |
| QLoRA | Technique | Mentioned only | Quantized LoRA |
| unsloth | Fine-tuning Stack | Mentioned only | Memory-efficient fine-tuning |

## 3. Inference Engines / Serving
| Name | Type | Reference | Notes |
|------|------|-----------|-------|
| vLLM | Inference Engine | `vllm-project/vllm` | Primary serving runtime |
| SGLang | Inference Engine | `sgl-project/sglang` | Agentic / long-context serving |
| llama.cpp | Inference Engine | `ggerganov/llama.cpp`, later `ggml-org/llama.cpp` | GGUF / local inference |
| exllama | Inference Engine | Mentioned only | EXL2 / optimized decode |
| TensorRT-LLM | Inference Engine | NVIDIA | Optimized inference stack |
| Ollama | Inference Engine | Mentioned only | Local deployment |
| MLX | Inference Engine | Apple | Apple Silicon inference |
| MLX LM | Tool / Runtime | Mentioned only | Apple-optimized local inference |
| LMDeploy | Inference Engine | Mentioned only | Serving stack |
| TGI | Inference Engine | Hugging Face Text Generation Inference | Serving stack |
| Ray Serve | Orchestration | Mentioned only | Multi-engine orchestration |
| FlashML | Optimization | DeepSeek | MLA attention optimization |

## 4. MoE Tools and MoE-Specific Methods
| Name | Type | Reference | Notes |
|------|------|-----------|-------|
| MoEQuant | Tool / Paper | Mentioned only | MoE quantization |
| Mixture Compressor | Tool / Paper | Mentioned only | MoE compression |
| MoE-Pruner | Tool / Paper | Mentioned only | MoE pruning |
| REAM | Tool / Method | Mentioned only | MoE-specific / router-aware method |
| MoE-Spec | Speculative Decoding Method | Mentioned only | Expert budgeting for MoE |
| REAP | MoE Variant Family | Mentioned only | Router-aware expert allocation |
| Qwen3.6-28B-REAP | Model Variant | Mentioned only | Standard REAP variant |
| Qwen3.6-28B-REAP20 | Model Variant | Mentioned only | 20-expert variant |
| Qwen3.6-VL-REAP-26B | Model Variant | Mentioned only | Vision + REAP |
| Qwen3.6-35B-REAP-Pruned-ratio-0.2 | Model Repo | Mentioned only | REAP-pruned variant |
| Qwen3.6-35B-REAP-Pruned-ratio-0.3 | Model Repo | Mentioned only | REAP-pruned variant |

## 5. Benchmark Tools
| Tool | Type | Explicit Reference | Notes |
|------|------|------------------|-------|
| aider | Benchmark Tool | Mentioned only | CLI coding benchmarks |
| SWE-bench | Benchmark Tool | Mentioned only | Software engineering benchmark |

## 6. macOS MLX Tools
| Name | Type | Reference | Notes |
|------|------|-----------|-------|
| MLX | Runtime | Apple | Apple Silicon inference stack |
| MLX LM | Tool / Runtime | Mentioned only | Apple-optimized local inference |
| dflash | Optimization Tool | Mentioned only | MLX-specific optimization |
| llama.ml | Tool / Serving Layer | Mentioned only | Mac-optimized serving |
| TurboQuant MLX 3-bit | Model / Quant Variant | Mentioned only | MLX quantized variant of Qwen3.6 |

## 7. Other ML/LLM Tools & Concepts
| Name | Type | Explicit Reference | Notes |
|------|------|------------------|-------|
| TiDAR | Speculative Decoding Method | Mentioned only | Diffusion + autoregressive drafting |
| DFlash | Speculative Decoding Method | Mentioned only | Block diffusion for flash speculative decoding |
| DDTree | Speculative Decoding Method | Mentioned only | Draft tree + verification |
| EAGLE / EAGLE-2 / EAGLE-3 | Speculative Decoding Methods | Mentioned only | Draft-model speculative decoding |
| Medusa | Speculative Decoding Method | Mentioned only | Multi-token prediction |
| SDAR | Speculative Decoding Method | Mentioned only | Speculative decoding variant |
| LongSpec | Speculative Decoding Method | Mentioned only | Long-context speculative decoding |
| QuantSpec | Speculative Decoding Method | Mentioned only | Hierarchical quantized KV cache |
| n-gram / suffix decoding | Method | Mentioned only | Lightweight speculative decoding |
| Blackboard pattern | Orchestration Pattern | Mentioned only | Shared memory + task slots |
| AgentServe | Orchestration Concept | Mentioned only | Cold/resume/short decode classification |
| BERT | Embedding / Preprocessing | Mentioned only | Semantic preprocessing |
| SentenceTransformers | Embedding Library | Mentioned only | Similarity / clustering / dedup |
| Rerankers | Retrieval Component | Mentioned only | Candidate ranking |
| Embedding Models | Model Class | Mentioned only | Pre-merge clustering / scoring |
| Phi-3-mini | Model | Mentioned only | Lightweight draft candidate |
| Llama-Guard | Model | Mentioned only | Safety / draft filter |
| DeepSeek | Model Family | Mentioned only | Architecture comparison |
| Gemma 4 26B A4B | Model Family | Mentioned only | MoE / 256K context |
| Gemma 4 31B | Model Family | Mentioned only | Dense variant |
| Gemma 3 27B | Model Family | Mentioned only | Previous generation multimodal |
| Llama 3.2 1B / 3B | Model Family | Mentioned only | Benchmark comparison pair |
| ChatGPT-5.1 | API / Proprietary Model | Mentioned only | Root verifier / synthesizer |
| Claude Haiku/Sonnet/Opus | API / Proprietary Model Family | Mentioned only | Capability tier analogies |

## H. Explicit GitHub Repositories Mentioned
| Repo | Type | Notes |
|------|------|-------|
| `scrya-com/rotorquant` | GitHub Repo | RotorQuant |
| `Dynamis-Labs/spectralquant` | GitHub Repo | SpectralQuant |
| `OpenAccess-AI-Collective/axolotl` | GitHub Repo | Training stack |
| `huggingface/trl` | GitHub Repo | Training stack |
| `huggingface/peft` | GitHub Repo | Training stack |
| `vllm-project/vllm` | GitHub Repo | Inference engine |
| `sgl-project/sglang` | GitHub Repo | Inference engine |
| `ggerganov/llama.cpp` | GitHub Repo | llama.cpp (earlier reference) |
| `ggml-org/llama.cpp` | GitHub Repo | llama.cpp (later reference) |

## I. Explicit Hugging Face Model Repositories Mentioned
| Repo / Model Repo | Type | Notes |
|------|------|-------|
| `unsloth/granite-4.1-8b-GGUF` | HF Model Repo | Granite 4.1 8B GGUF |
| `mradermacher/granite-4.1-8b-Brainstone-Thinking-i1-GGUF` | HF Model Repo | Granite thinking variant |
| `unsloth/Qwen3.6-35B-A3B-GGUF` | HF Model Repo | Qwen3.6 MoE |
| `mradermacher/Qwen3.6-28B-REAP-GGUF` | HF Model Repo | REAP variant |
| `barozp/Qwen3.6-28B-REAP20-A3B-GGUF` | HF Model Repo | REAP20 variant |
| `RangerX/Qwen3.6-35B-REAP-Pruned-ratio-0.2` | HF Model Repo | REAP pruned |
| `RangerX/Qwen3.6-35B-REAP-Pruned-ratio-0.3` | HF Model Repo | REAP pruned |
| `mradermacher/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-i1-GGUF` | HF Model Repo | Distilled reasoning |
| `mudler/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-GGUF` | HF Model Repo | Distilled APEX |
| `keithnull/Qwen3.6-VL-REAP-26B-A3B-GGUF` | HF Model Repo | Vision + REAP |

## J. Local Project / Module References Mentioned
| Name | Type | Notes |
|------|------|-------|
| `pheno-compute-layer` | Project / Module | Compute layer for desktop access |
| `omni_route.py` | Python Module | Role-based router |
| `download-model.sh` | Script | Model download helper |
| `deploy-desktop.sh` | Script | Desktop deployment script |
| `start-multi-vllm.sh` | Script | Multi-model vLLM server launcher |
| `desk` | Script / CLI | SSH utility |
| `pheno_client.py` | Python Client | Inference SDK |
| `pheno` | CLI | Compute-layer CLI (`pheno status`, `pheno gpu`, `pheno wsl-ssh`, etc.) |