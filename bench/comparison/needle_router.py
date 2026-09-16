"""Needle router — lightweight pre-filter for benchmark task routing.

Two modes:
  - **Heuristic** (default, zero deps): keyword-based classification.
  - **Needle** (optional, requires ``needle`` pip package): contrastive-head
    tool selection via the Cactus runtime.

Usage::

    from bench.comparison.needle_router import route_task
    result = route_task("Fix the off-by-one error in process()", "swe-bench", mode="heuristic")
    # result = {"tool": "code_generation", "confidence": 0.9, "routing_time_ms": 0.12, ...}
"""

from __future__ import annotations

import json
import time
from typing import Any, cast

# ---------------------------------------------------------------------------
# Routing table: suite → (category, keywords)
# ---------------------------------------------------------------------------

ROUTING_TABLE: dict[str, dict[str, Any]] = {
    "arc-agi-2": {
        "category": "grid_transform",
        "keywords": ["grid", "pattern", "transform", "matrix", "2D"],
    },
    "gpqa-diamond": {
        "category": "question_answering",
        "keywords": ["which", "what", "how", "choose", "A.", "B.", "C.", "D."],
    },
    "mmlu-pro": {
        "category": "question_answering",
        "keywords": ["which", "what", "the answer", "option"],
    },
    "deep-swe": {
        "category": "code_generation",
        "keywords": ["fix", "implement", "function", "class", "bug", "error"],
    },
    "terminal-bench": {
        "category": "shell_command",
        "keywords": ["command", "run", "execute", "terminal", "shell", "bash"],
    },
    "livecodebench": {
        "category": "code_generation",
        "keywords": ["function", "algorithm", "leetcode", "solve", "return"],
    },
    "aider-polyglot": {
        "category": "code_generation",
        "keywords": ["implement", "write", "code", "function", "def ", "fn "],
    },
    "swe-bench": {
        "category": "code_generation",
        "keywords": ["fix", "bug", "patch", "pull request", "issue"],
    },
    "swe-bench-pro": {
        "category": "code_generation",
        "keywords": ["fix", "bug", "refactor", "implement"],
    },
    "bfcl": {
        "category": "function_calling",
        "keywords": ["call", "function", "tool", "API", "invoke"],
    },
}

# Reverse map: category → list of suite names (for ground-truth lookup).
_CATEGORY_SUITES: dict[str, list[str]] = {}
for _suite, _entry in ROUTING_TABLE.items():
    _CATEGORY_SUITES.setdefault(_entry["category"], []).append(_suite)


def _ground_truth_category(suite: str) -> str:
    """Return the expected category for a suite name (deterministic)."""
    entry = ROUTING_TABLE.get(suite)
    if entry:
        return cast(str, entry["category"])
    return "unknown"


# ---------------------------------------------------------------------------
# Heuristic router (zero dependencies)
# ---------------------------------------------------------------------------


def _heuristic_route(prompt: str, suite: str) -> dict[str, Any]:
    """Classify a prompt into a tool category using keyword matching.

    Returns dict with keys: tool, confidence, routing_time_ms, method.
    """
    t0 = time.perf_counter()

    # Prefer suite-level routing (100% deterministic for known suites).
    entry = ROUTING_TABLE.get(suite)
    if entry:
        prompt_lower = prompt.lower()
        matched = sum(1 for kw in entry["keywords"] if kw.lower() in prompt_lower)
        total = len(entry["keywords"])
        confidence = min(1.0, matched / max(total, 1)) if matched > 0 else 0.5
        return {
            "tool": entry["category"],
            "confidence": round(confidence, 4),
            "routing_time_ms": round((time.perf_counter() - t0) * 1000, 4),
            "method": "heuristic_suite",
        }

    # Fallback: scan all categories for keyword hits.
    prompt_lower = prompt.lower()
    best_category = "unknown"
    best_score = 0.0
    for cat_entry in ROUTING_TABLE.values():
        cat = cat_entry["category"]
        hits = sum(1 for kw in cat_entry["keywords"] if kw.lower() in prompt_lower)
        if hits > best_score:
            best_score = hits
            best_category = cat
    confidence = min(1.0, best_score / 5.0) if best_score > 0 else 0.1

    return {
        "tool": best_category,
        "confidence": round(confidence, 4),
        "routing_time_ms": round((time.perf_counter() - t0) * 1000, 4),
        "method": "heuristic_fallback",
    }


# ---------------------------------------------------------------------------
# Needle router (requires ``needle`` pip package)
# ---------------------------------------------------------------------------

_NEEDLE_AVAILABLE: bool | None = None


def _is_needle_available() -> bool:
    global _NEEDLE_AVAILABLE
    if _NEEDLE_AVAILABLE is None:
        try:
            import needle  # noqa: F401

            _NEEDLE_AVAILABLE = True
        except ImportError:
            _NEEDLE_AVAILABLE = False
    return _NEEDLE_AVAILABLE


def _build_tools_json() -> str:
    """Build the JSON tools list that Needle expects."""
    tools = []
    seen: set[str] = set()
    for cat_entry in ROUTING_TABLE.values():
        cat = cat_entry["category"]
        if cat in seen:
            continue
        seen.add(cat)
        tools.append(
            {
                "name": cat,
                "description": f"Benchmark tool category: {cat}",
                "parameters": {"prompt": {"type": "string"}},
            }
        )
    return json.dumps(tools)


def _needle_route(prompt: str, suite: str) -> dict[str, Any]:
    """Route via Needle's contrastive head.

    Falls back to heuristic if needle fails at runtime.
    """
    t0 = time.perf_counter()
    try:
        import needle

        tools_json = _build_tools_json()
        # Needle API: needle.generate(query=..., tools=...) returns a JSON
        # function call string. Parse it to extract the selected tool.
        raw = needle.generate(query=prompt, tools=tools_json)
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        tool_name = (
            parsed.get("name") or parsed.get("tool") or parsed.get("function", "")
        )
        confidence = parsed.get("confidence", 0.8)
        return {
            "tool": tool_name,
            "confidence": round(float(confidence), 4),
            "routing_time_ms": round((time.perf_counter() - t0) * 1000, 4),
            "method": "needle",
        }
    except Exception:
        # Graceful fallback to heuristic on any Needle failure.
        result = _heuristic_route(prompt, suite)
        result["method"] = "needle_fallback"
        return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route_task(
    prompt: str,
    suite: str,
    mode: str = "heuristic",
) -> dict[str, Any]:
    """Route a benchmark task prompt to a tool category.

    Parameters
    ----------
    prompt:
        The task prompt text.
    suite:
        Suite name (e.g. ``"swe-bench"``) — used for deterministic routing
        and ground-truth comparison.
    mode:
        ``"heuristic"`` (default), ``"needle"``, or ``"none"``.

    Returns
    -------
    dict with keys: tool, confidence, routing_time_ms, method, correct.
    """
    if mode == "none":
        return {
            "tool": "none",
            "confidence": 0.0,
            "routing_time_ms": 0.0,
            "method": "none",
            "correct": True,
        }

    if mode == "needle" and _is_needle_available():
        result = _needle_route(prompt, suite)
    else:
        result = _heuristic_route(prompt, suite)

    gt = _ground_truth_category(suite)
    result["correct"] = result["tool"] == gt
    return result


def route_task_batch(
    tasks: list[tuple[str, str]],
    mode: str = "heuristic",
) -> list[dict[str, Any]]:
    """Route multiple tasks. Each element is (prompt, suite)."""
    return [route_task(prompt, suite, mode=mode) for prompt, suite in tasks]


__all__ = [
    "ROUTING_TABLE",
    "route_task",
    "route_task_batch",
    "_ground_truth_category",
]
