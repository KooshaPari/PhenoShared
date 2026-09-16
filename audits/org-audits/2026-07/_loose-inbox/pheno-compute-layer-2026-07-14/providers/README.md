# OmniRoute - Model Provider System

Role-based LLM routing for multi-agent CLI systems with support for MoE, REAP, and thinking models.

## Managed Desktop Service

The router is wired to the desktop Tailscale endpoint:

- **Base URL:** `http://100.96.135.160:8080/v1`
- **Preferred backend:** vLLM
- **Fallback backend:** SGLang
- **Access path:** Tailscale / `ssh-desk`
- **Primary coding model:** Granite 4.1 8B
- **Primary reasoning models:** Qwen3.6 MoE + REAP variants

## Quick Start

```bash
# Show current endpoint/config
python3 providers/omni_route.py --config

# List models
./scripts/download-model.sh list

# List REAP models
python3 providers/omni_route.py --reap

# List roles
python3 providers/omni_route.py --roles
```

## Available Models

### ⭐ Core Models (Recommended)

| Model | Size | Role | Description |
|-------|------|------|-------------|
| **granite_4_1_8b** | 4.8GB | code | IBM Granite - BEST coding ⭐⭐⭐ |
| **qwen3_6_35b_a3b_iq2** | 12GB | reason | MoE ultra-low mem ⭐⭐ |
| **qwen3_6_28b_reap** | 18GB | reason | REAP optimized ⭐⭐ |
| **qwen3_6_35b_distill** | 22GB | reason | Claude distilled ⭐⭐ |

### REAP Variants

| Model | Size | Description |
|-------|------|-------------|
| qwen3_6_28b_reap | 18GB | REAP 28B/3B |
| qwen3_6_28b_reap20 | 18GB | REAP20 (20-expert) |
| qwen3_6_35b_reap_pruned_02 | 28GB | REAP pruned 20% |
| qwen3_6_35b_reap_pruned_03 | 24GB | REAP pruned 30% |

### Granite 4.1 Variants

| Model | Size | Description |
|-------|------|-------------|
| granite_4_1_8b | 4.8GB | IQ4_NL quant (best) |
| granite_4_1_8b_q4 | 5GB | Q4_K_M quant |
| granite_4_1_8b_udq2 | 3.2GB | Ultra-low memory |
| granite_4_1_8b_think | 5.5GB | Thinking variant |

### Qwen3.6 MoE Variants

| Model | Size | Description |
|-------|------|-------------|
| qwen3_6_35b_a3b | 21GB | Full MoE (35B/3B) |
| qwen3_6_35b_a3b_iq2 | 12GB | Ultra-low memory |
| qwen3_6_35b_a3b_iq4 | 9GB | Lowest memory |
| qwen3_6_35b_a3b_iq3 | 15GB | Balanced low |

## Role Mappings

| Role | Model | Description |
|------|-------|-------------|
| code | granite_4_1_8b | IBM Granite - best coding |
| reason | qwen3_6_35b_a3b_iq2 | MoE ultra-low mem |
| think | qwen3_6_35b_distill | Claude distilled |
| reap | qwen3_6_28b_reap | REAP specialized |

## Quantization Options

### Granite 4.1
- **IQ4_NL** - Best quality/size ratio
- IQ4_XS, Q4_K_M, Q3_K_M, Q5_K_M, Q6_K
- UD-IQ2_M (ultra-low), UD-IQ3_XXS

### Qwen3.6 MoE
- **UD-IQ2_M** - Ultra-low memory (12GB)
- UD-IQ4_NL (9GB), UD-IQ3_S (15GB)
- MXFP4_MOE (mixed precision)

### REAP Models
- Q4_K_M, Q3_K_M, Q5_K_M
- IQ4_XS, Q2_K, Q6_K, Q8_0

## REAP (Router-Aware Expert Allocation)

REAP optimizes MoE models by improving router accuracy for expert selection. Variants:
- **Qwen3.6-28B-REAP** - Standard REAP
- **Qwen3.6-28B-REAP20** - 20-expert variant
- **Qwen3.6-VL-REAP-26B** - Vision + REAP

## Quants Comparison

| Quant | Quality | Size | Speed |
|-------|---------|------|-------|
| Q8_0 | Highest | Large | Slow |
| Q6_K | High | Medium | Medium |
| Q4_K_M | Good | Small | Fast |
| IQ4_NL | Good+ | Small | Fast |
| UD-IQ2_M | Good | Tiny | Fastest |

## Environment Variables

```bash
export OMNI_URL="http://100.96.135.160:8080/v1"
export OMNI_BACKEND="vllm"
export OMNI_MODELS="/home/kooshapari/llm-models"
```

