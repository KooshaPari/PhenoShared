#!/usr/bin/env python3
"""
OmniRoute - Role-Based LLM Router
=================================
Multi-model routing for multi-agent CLI systems.

Models available:
- Granite 4.1 (IBM) - Best coding model
- Qwen3.6 MoE - Efficient reasoning
- Qwen3.6 REAP - Router-Aware Expert Allocation
- Qwen3.6 Distilled - Claude distilled reasoning
"""

import os
import json
import argparse
from typing import Optional, Dict, List

# Configuration
DESKTOP_URL = os.environ.get("OMNI_URL", "http://100.96.135.160:8080/v1")
MODELS_DIR = os.environ.get("OMNI_MODELS", "/home/kooshapari/llm-models")
SERVICE_BACKEND = os.environ.get("OMNI_BACKEND", "vllm")

# Model registry with all verified variants
MODELS = {
    # ========== Granite 4.1 (IBM) - Best Coding ==========
    "granite_4_1_8b": {
        "repo": "unsloth/granite-4.1-8b-GGUF",
        "default_quant": "IQ4_NL",
        "role": "code",
        "size_gb": 4.8,
        "context": 128000,
        "type": "dense",
        "description": "IBM Granite - BEST coding model ⭐⭐⭐",
        "quants_available": ["IQ4_NL", "IQ4_XS", "Q4_K_M", "Q3_K_M", "Q5_K_M", "Q6_K", "UD-IQ2_M", "UD-IQ3_XXS"],
    },
    "granite_4_1_8b_q4": {
        "repo": "unsloth/granite-4.1-8b-GGUF",
        "default_quant": "Q4_K_M",
        "role": "code",
        "size_gb": 5,
        "context": 128000,
        "type": "dense",
        "description": "Granite Q4_K_M variant",
    },
    "granite_4_1_8b_udq2": {
        "repo": "unsloth/granite-4.1-8b-GGUF",
        "default_quant": "UD-IQ2_M",
        "role": "code",
        "size_gb": 3.2,
        "context": 128000,
        "type": "dense",
        "description": "Granite ultra-low memory",
    },
    "granite_4_1_8b_think": {
        "repo": "mradermacher/granite-4.1-8b-Brainstone-Thinking-i1-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 5.5,
        "context": 128000,
        "type": "dense",
        "description": "Granite with extended thinking",
        "fine_tuned": True,
        "thinking": True,
    },
    
    # ========== Qwen3.6 MoE (35B total, ~3B active) ==========
    "qwen3_6_35b_a3b": {
        "repo": "unsloth/Qwen3.6-35B-A3B-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 21,
        "context": 131072,
        "type": "moe",
        "description": "MoE - 35B total / 3B active (full)",
        "quants_available": ["Q4_K_M", "UD-IQ2_M", "UD-IQ3_S", "UD-IQ4_NL", "UD-IQ1_M", "UD-IQ2_XXS", "UD-IQ3_XXS", "MXFP4_MOE"],
    },
    "qwen3_6_35b_a3b_iq2": {
        "repo": "unsloth/Qwen3.6-35B-A3B-GGUF",
        "default_quant": "UD-IQ2_M",
        "role": "reason",
        "size_gb": 12,
        "context": 131072,
        "type": "moe",
        "description": "MoE ultra-low memory ⭐⭐",
        "quants_available": ["UD-IQ2_M", "UD-IQ3_S"],
    },
    "qwen3_6_35b_a3b_iq4": {
        "repo": "unsloth/Qwen3.6-35B-A3B-GGUF",
        "default_quant": "UD-IQ4_NL",
        "role": "reason",
        "size_gb": 9,
        "context": 131072,
        "type": "moe",
        "description": "MoE lowest memory (9GB)",
    },
    "qwen3_6_35b_a3b_iq3": {
        "repo": "unsloth/Qwen3.6-35B-A3B-GGUF",
        "default_quant": "UD-IQ3_S",
        "role": "reason",
        "size_gb": 15,
        "context": 131072,
        "type": "moe",
        "description": "MoE balanced low memory",
    },
    
    # ========== Qwen3.6 REAP (Router-Aware Expert Allocation) ==========
    "qwen3_6_28b_reap": {
        "repo": "mradermacher/Qwen3.6-28B-REAP-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 18,
        "context": 131072,
        "type": "moe",
        "description": "REAP optimized (28B/3B) ⭐⭐",
        "reap": True,
        "quants_available": ["Q4_K_M", "Q3_K_M", "Q5_K_M", "IQ4_XS", "Q2_K", "Q6_K", "Q8_0"],
    },
    "qwen3_6_28b_reap20": {
        "repo": "barozp/Qwen3.6-28B-REAP20-A3B-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 18,
        "context": 131072,
        "type": "moe",
        "description": "REAP20 (20-expert variant)",
        "reap": True,
        "quants_available": ["Q4_K_M", "Q3_K_M", "Q3_K_L", "Q5_K_M", "Q6_K", "IQ3_XXS", "Q2_K", "Q8_0"],
    },
    "qwen3_6_35b_reap_pruned_02": {
        "repo": "RangerX/Qwen3.6-35B-REAP-Pruned-ratio-0.2",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 28,
        "context": 131072,
        "type": "moe",
        "description": "REAP pruned 20%",
        "reap": True,
    },
    "qwen3_6_35b_reap_pruned_03": {
        "repo": "RangerX/Qwen3.6-35B-REAP-Pruned-ratio-0.3",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 24,
        "context": 131072,
        "type": "moe",
        "description": "REAP pruned 30% (lightest)",
        "reap": True,
    },
    
    # ========== Qwen3.6 Reasoning Distilled ==========
    "qwen3_6_35b_distill": {
        "repo": "mradermacher/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-i1-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 22,
        "context": 131072,
        "type": "moe",
        "description": "Claude 4.7 Opus distilled reasoning ⭐⭐",
        "fine_tuned": True,
        "distilled": True,
    },
    "qwen3_6_35b_apex": {
        "repo": "mudler/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 22,
        "context": 131072,
        "type": "moe",
        "description": "APEX distilled reasoning",
        "fine_tuned": True,
        "distilled": True,
    },
    
    # ========== Qwen3.6 Vision REAP ==========
    "qwen3_6_vl_reap_26b": {
        "repo": "keithnull/Qwen3.6-VL-REAP-26B-A3B-GGUF",
        "default_quant": "Q4_K_M",
        "role": "reason",
        "size_gb": 17,
        "context": 131072,
        "type": "moe",
        "description": "Vision + REAP (26B/3B)",
        "reap": True,
        "vision": True,
    },
}

# Role routing with default chain
ROLE_MAP = {
    "code": "granite_4_1_8b",           # IBM Granite - best coding
    "reason": "qwen3_6_35b_a3b_iq2",   # MoE ultra-low mem
    "think": "qwen3_6_35b_distill",     # Claude distilled
    "reap": "qwen3_6_28b_reap",         # REAP specialized
    "default": "granite_4_1_8b",         # Default to Granite
}

# Provider routing per role. The desktop OpenAI-compatible endpoint is shared.
ROLE_PROVIDER_MAP = {
    "code": {
        "endpoint": DESKTOP_URL,
        "backend": SERVICE_BACKEND,
    },
    "reason": {
        "endpoint": DESKTOP_URL,
        "backend": SERVICE_BACKEND,
    },
    "think": {
        "endpoint": DESKTOP_URL,
        "backend": SERVICE_BACKEND,
    },
    "reap": {
        "endpoint": DESKTOP_URL,
        "backend": SERVICE_BACKEND,
    },
}




def get_model_for_role(role: str) -> str:
    """Get model key for a role."""
    return ROLE_MAP.get(role, ROLE_MAP["default"])


def get_model_path(model_key: str, quant: Optional[str] = None) -> str:
    """Get local path for a model."""
    model = MODELS.get(model_key)
    if not model:
        raise ValueError(f"Unknown model: {model_key}")
    
    quant = quant or model["default_quant"]
    # Build filename from repo and quant
    repo_short = model["repo"].split("/")[-1]
    filename = f"{repo_short}-{quant}.gguf"
    return os.path.join(MODELS_DIR, model_key, filename)


def list_providers(category: Optional[str] = None) -> Dict:
    """List all available providers, optionally filtered by category."""
    if category:
        return {k: v for k, v in MODELS.items() if v.get(category)}
    return MODELS


def list_roles() -> Dict[str, str]:
    """List role mappings."""
    return ROLE_MAP


def route(prompt: str, role: str = "default", **kwargs) -> Dict:
    """Route a prompt to the appropriate model."""
    model_key = get_model_for_role(role)
    model = MODELS[model_key]

    provider = ROLE_PROVIDER_MAP.get(role, ROLE_PROVIDER_MAP["code"])

    return {
        "model_key": model_key,
        "model_config": model,
        "endpoint": provider["endpoint"],
        "backend": provider["backend"],
        "prompt": prompt,
        **kwargs,
    }


def main():
    parser = argparse.ArgumentParser(description="OmniRoute - LLM Router")
    parser.add_argument("--list", "-l", action="store_true", help="List all providers")
    parser.add_argument("--moe", "-m", action="store_true", help="List MoE models only")
    parser.add_argument("--reap", "-r", action="store_true", help="List REAP models only")
    parser.add_argument("--thinking", "-t", action="store_true", help="List thinking models only")
    parser.add_argument("--roles", action="store_true", help="List roles")
    parser.add_argument("--role", help="Role for prompt")
    parser.add_argument("--model", "-M", help="Model key (overrides role)")
    parser.add_argument("--prompt", "-p", help="Prompt text")
    parser.add_argument("--config", "-c", action="store_true", help="Show config")
    
    args = parser.parse_args()
    
    if args.list or args.moe or args.reap or args.thinking:
        # Filter by category
        if args.moe:
            models = {k: v for k, v in MODELS.items() if v.get("type") == "moe"}
            print("MoE Models:")
        elif args.reap:
            models = {k: v for k, v in MODELS.items() if v.get("reap")}
            print("REAP Models:")
        elif args.thinking:
            models = {k: v for k, v in MODELS.items() if v.get("thinking")}
            print("Thinking Models:")
        else:
            models = MODELS
            print("All Providers:")
        
        for key, config in models.items():
            tags = []
            if config.get("type") == "moe":
                tags.append("MoE")
            if config.get("reap"):
                tags.append("REAP")
            if config.get("thinking"):
                tags.append("Thinking")
            if config.get("distilled"):
                tags.append("Distilled")
            if config.get("vision"):
                tags.append("Vision")
            if config.get("fine_tuned"):
                tags.append("Fine-tuned")
            
            tags_str = ",".join(tags) or "Dense"
            print(f"\n  {key}")
            print(f"    Repo: {config['repo']}")
            print(f"    Size: {config['size_gb']}GB, Context: {config['context']}")
            print(f"    Role: {config['role']} | {tags_str}")
            print(f"    Desc: {config['description']}")
            if "quants_available" in config:
                print(f"    Quants: {', '.join(config['quants_available'])}")
    
    elif args.roles:
        print("Role Mappings:")
        for role, model in ROLE_MAP.items():
            print(f"  {role} -> {model}")
            provider = ROLE_PROVIDER_MAP.get(role)
            if provider:
                print(f"    endpoint: {provider['endpoint']}")
                print(f"    backend: {provider['backend']}")
    
    elif args.config:
        print(f"DESKTOP_URL={DESKTOP_URL}")
        print(f"MODELS_DIR={MODELS_DIR}")
        print(f"SERVICE_BACKEND={SERVICE_BACKEND}")
        print("ROLE_PROVIDER_MAP:")
        for role, provider in ROLE_PROVIDER_MAP.items():
            print(f"  {role}: {provider['endpoint']} ({provider['backend']})")

    
    else:
        print(__doc__)
        print("\nUsage:")
        print("  omni_route --list              # List all models")
        print("  omni_route --moe               # List MoE models")
        print("  omni_route --reap              # List REAP models")
        print("  omni_route --thinking          # List thinking models")
        print("  omni_route --roles             # List role mappings")
        print("  omni_route --role <role>       # Show model for role")
        print("  omni_route --config            # Show endpoint/config")


if __name__ == "__main__":
    main()
