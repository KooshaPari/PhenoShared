"""Stock-vs-ours adapter definitions.

Model registry, efficiency constants, configuration, and MLX variant
runners used by the stock-vs-ours comparison matrix.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, cast

from bench.comparison.mlx_direct import MLXDirect

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "Qwen/Qwen3.5-0.8B": {
        "params": 0.8e9,
        "architecture": "dense",
        "max_tokens": 256,
        "size_on_disk_gb": 1.6,
    },
    "Qwen/Qwen3.5-4B": {
        "params": 4e9,
        "architecture": "dense",
        "max_tokens": 512,
        "size_on_disk_gb": 8.0,
    },
    "prism-ml/Ternary-Bonsai-8B-mlx-2bit": {
        "params": 8.19e9,
        "architecture": "ternary",
        "max_tokens": 1024,
        "size_on_disk_gb": 2.3,
    },
}

DEFAULT_MODEL = "Qwen/Qwen3.5-0.8B"


def model_slug(model_id: str) -> str:
    """Convert a HuggingFace model ID to a short slug for filenames.

    ``Qwen/Qwen3.5-4B`` -> ``qwen35-4b``
    ``prism-ml/Ternary-Bonsai-8B-mlx-2bit`` -> ``ternary-bonsai-8b``
    ``Qwen/Qwen3.5-0.8B`` -> ``qwen35-08b``
    """
    name = model_id.rsplit("/", 1)[-1]
    slug = name.lower().replace(".", "")
    slug = re.sub(r"-mlx-\d+bit$", "", slug)
    slug = re.sub(r"-gguf$", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_RESULTS = REPO_ROOT / "bench" / "results"
BENCH_RESULTS.mkdir(parents=True, exist_ok=True)

SUITES = [
    "mmlu-pro",
    "gpqa-diamond",
    "aime",
    "arc-agi-2",
    "livecodebench",
    "aider-polyglot",
    "swe-bench",
    "swe-bench-pro",
    "bfcl",
    "terminal-bench",
]

SUITE_PROMPT_SUFFIX: dict[str, str] = {
    "mmlu-pro": (
        "\n\nReply with ONLY the letter (A, B, C, ...) of the correct answer."
    ),
    "gpqa-diamond": (
        "\n\nReply with ONLY the letter (A, B, C, D) of the correct answer."
    ),
    "aime": ("\n\nReply with ONLY the integer answer (no units, no explanation)."),
    "arc-agi-2": (
        "\n\nProvide the output grid as JSON: {'output': [[row1], [row2], ...]}"
    ),
    "livecodebench": (
        "\n\nWrite a Python solution. Output ONLY the function body, no prose."
    ),
    "aider-polyglot": (
        "\n\nWrite the edit in unified diff format. No prose around the diff."
    ),
    "swe-bench": (
        "\n\nYou are working in a sandboxed git repo. Make the change and confirm it works."
    ),
    "swe-bench-pro": (
        "\n\nYou are working in a sandboxed git repo. Apply the multi-file patch and run tests."
    ),
    "bfcl": (
        "\n\nIf you need to call a function, output ONLY a JSON tool_call block, otherwise output the final answer."
    ),
    "terminal-bench": ("\n\nRun this shell task. Just execute and report success."),
}

DIFFICULTY_MIX = {"easy": 5, "medium": 8, "hard": 7, "ultra": 5}

CODEX = "/opt/homebrew/bin/codex"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
LOCAL_MLX_URL = "http://127.0.0.1:8765/v1"

CODEX_TEST_ROOT = Path(
    "/tmp/codex-stock-vs-ours-probe"
)  # ephemeral test path under /tmp, reviewed false positive # nosec B108
CODEX_TEST_ROOT.mkdir(parents=True, exist_ok=True)

_SYSTEM_MEMORY_BYTES = 16e9
_MEMORY_BANDWIDTH_GBPS = 80.0


# ---------------------------------------------------------------------------
# Efficiency constants
# ---------------------------------------------------------------------------


def _model_efficiency(model_id: str) -> dict[str, float]:
    """Return per-model efficiency constants for metrics computation."""
    meta = MODEL_REGISTRY.get(model_id, {})
    params = meta.get("params", 0.8e9)
    param_bytes = 2
    model_memory_bytes = params * param_bytes
    peak_tps = (
        (_MEMORY_BANDWIDTH_GBPS * 1e9) / model_memory_bytes
        if model_memory_bytes
        else 0.0
    )
    return {
        "model_params": params,
        "param_bytes": param_bytes,
        "model_memory_bytes": model_memory_bytes,
        "system_memory_bytes": _SYSTEM_MEMORY_BYTES,
        "peak_tps": peak_tps,
        "memory_bandwidth_gbps": _MEMORY_BANDWIDTH_GBPS,
    }


# ---------------------------------------------------------------------------
# MLX variant runners
# ---------------------------------------------------------------------------


def _mlx_direct(
    prompt: str,
    model_id: str = DEFAULT_MODEL,
    max_tokens: int = 256,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Run against the local MLX server directly via HTTP."""
    import json as _json

    started = time.monotonic()
    body = _json.dumps(
        {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
            "chat_template_kwargs": {"enable_thinking": False},
        }
    ).encode()
    req = __import__("urllib.request").Request(
        f"{LOCAL_MLX_URL}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with __import__("urllib.request").urlopen(req, timeout=timeout_s) as resp:
            data = _json.loads(resp.read())
            wall = time.monotonic() - started
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "ok": True,
                "wall_clock_s": wall,
                "stdout": text,
                "stderr": "",
                "returncode": 0,
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
            }
    except Exception as e:
        return {
            "ok": False,
            "wall_clock_s": time.monotonic() - started,
            "stdout": "",
            "stderr": f"HTTP_ERROR: {type(e).__name__}: {e}",
            "returncode": -1,
        }


_mlx_direct_adapter: MLXDirect | None = None


def _get_mlx_direct_adapter(model_id: str = DEFAULT_MODEL) -> MLXDirect:
    global _mlx_direct_adapter
    if _mlx_direct_adapter is None or _mlx_direct_adapter.model_id != model_id:
        _mlx_direct_adapter = MLXDirect(model_id)
    return _mlx_direct_adapter


def _mlx_generate_direct(
    prompt: str,
    model_id: str = DEFAULT_MODEL,
    max_tokens: int = 256,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Run inference via MLXDirect — bypasses the HTTP server entirely."""
    adapter = _get_mlx_direct_adapter(model_id)
    started = time.monotonic()
    try:
        # `MLXDirect.generate` returns the completion as a plain `str`
        # (it does not expose a structured result object). Token-level
        # metrics (`prompt_tokens`, `completion_tokens`,
        # `first_token_latency_ms`, `tokens_per_second`) are not
        # available through this path; the analysis layer treats them
        # as 0 when the dict key is missing.
        text = adapter.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=0.0,
            enable_thinking=False,
        )
        wall = time.monotonic() - started
        return {
            "ok": True,
            "wall_clock_s": wall,
            "stdout": text,
            "stderr": "",
            "returncode": 0,
        }
    except Exception as e:
        return {
            "ok": False,
            "wall_clock_s": time.monotonic() - started,
            "stdout": "",
            "stderr": f"DIRECT_ERROR: {type(e).__name__}: {e}",
            "returncode": -1,
        }


def _is_mlx_server_alive() -> bool:
    try:
        with __import__("urllib.request").urlopen(
            f"{LOCAL_MLX_URL}/models", timeout=2
        ) as r:
            return cast(bool, r.status == 200)
    except Exception:
        return False


__all__ = [
    "MODEL_REGISTRY",
    "DEFAULT_MODEL",
    "model_slug",
    "REPO_ROOT",
    "BENCH_RESULTS",
    "SUITES",
    "SUITE_PROMPT_SUFFIX",
    "DIFFICULTY_MIX",
    "CODEX",
    "CODEX_CONFIG",
    "LOCAL_MLX_URL",
    "CODEX_TEST_ROOT",
    "_model_efficiency",
    "_mlx_direct",
    "_get_mlx_direct_adapter",
    "_mlx_generate_direct",
    "_is_mlx_server_alive",
]
