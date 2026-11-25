"""Stability metrics: intent drift, dead-end detection, semantic drift (spec §4.6).

All metrics are computed lazily post-run if `--stability-metric` is set
(spec rule §8). Embeddings use `sentence-transformers` if available, falling
back to a deterministic character-trigram hash fingerprint so the harness can
run unit tests in any environment.

Public surface:

* `intent_drift(conversation, *, embed_fn=None)` — cosine distance from the
  initial user-intent embedding to subsequent user intents. Lower = more
  consistent across turns.
* `dead_end_count(conversation, *, max_repeats=3)` — count of turns whose
  tool-call/assistant-response text matches a preceding turn within the last
  `max_repeats` turns.
* `semantic_drift_score(conversation)` — long-horizon drift via embedding
  cosine to the first assistant message (or hash fingerprinted cosine if the
  embedding model is unavailable).
* `embed_texts(texts, *, model=None, fallback_dim=64)` — main embedding
  entry point; chooses sentence-transformers vs hash fallback automatically.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Sequence
from typing import Any

from bench.metric import cosine_similarity, semantic_drift

# ---------------------------------------------------------------------------
# Public embedding helper
# ---------------------------------------------------------------------------


DEFAULT_FALLBACK_DIM = 64


def _hash_embed(text: str, dim: int = DEFAULT_FALLBACK_DIM) -> list[float]:
    """Deterministic trigram-hash embedding.

    Each trigram `t` hashes to an index `i` in `[0, dim)`; we accumulate
    +1 in that slot. The result is L2-normalized so cosine makes sense.
    """
    if not text:
        return [0.0] * dim
    s = re.sub(r"\s+", " ", text.lower()).strip()
    if not s:
        return [0.0] * dim
    vec = [0.0] * dim
    grams = [s[i : i + 3] for i in range(max(0, len(s) - 2))]
    if not grams:
        grams = [s]
    for g in grams:
        digest = hashlib.blake2b(g.encode("utf-8"), digest_size=4).digest()
        idx = int.from_bytes(digest, "big") % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def embed_texts(
    texts: Sequence[str],
    *,
    model: str | None = None,
    fallback_dim: int = DEFAULT_FALLBACK_DIM,
) -> list[list[float]]:
    """Compute embeddings for each text using sentence-transformers if present.

    Args:
        texts: Text inputs.
        model: HuggingFace model id (default `all-MiniLM-L6-v2` if available).
        fallback_dim: Hash-vector width when sentence-transformers unavailable.

    Returns:
        One embedding vector per text, all the same length.

    Behavior:
        - If sentence-transformers import succeeds, returns its numpy arrays
          converted to Python lists.
        - Otherwise returns hash fingerprints (`len(texts)` x `fallback_dim`).
    """
    if not texts:
        return []
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return [_hash_embed(t, fallback_dim) for t in texts]
    name = model or "all-MiniLM-L6-v2"
    try:
        st = SentenceTransformer(name)
        arrays = st.encode(
            list(texts), show_progress_bar=False, normalize_embeddings=True
        )
        return [list(map(float, a)) for a in arrays]
    except Exception:
        # The model may not be downloadable in CI; still degrade gracefully.
        return [_hash_embed(t, fallback_dim) for t in texts]


# ---------------------------------------------------------------------------
# Per-turn conversation structure
# ---------------------------------------------------------------------------


class Turn:
    """One turn in a multi-turn conversation.

    `role` is free-form ("user", "assistant", "tool"). `tool_calls` is the
    list of tool names invoked (used by the dead-end detector).
    """

    __slots__ = ("role", "content", "tool_calls")

    def __init__(
        self, role: str, content: str, tool_calls: Sequence[str] | None = None
    ) -> None:
        self.role = role
        self.content = content
        self.tool_calls: tuple[str, ...] = tuple(tool_calls or ())

    def __repr__(self) -> str:
        return f"Turn(role={self.role!r}, len={len(self.content)}, tools={list(self.tool_calls)})"


# ---------------------------------------------------------------------------
# Intent drift
# ---------------------------------------------------------------------------


def _user_intents(conversation: Sequence[Turn]) -> list[str]:
    """Extract the strings of consecutive user turns."""
    return [t.content for t in conversation if t.role == "user"]


def intent_drift(
    conversation: Sequence[Turn],
    *,
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> dict[str, Any]:
    """Compute multi-turn intent drift.

    Definition: average of 1 - cosine(initial_user_intent_embedding, others).

    Returns a dict so the executor can plug individual values into the
    RunReport:

        {
          "drift_mean": float,
          "drift_p50": float,
          "drift_p99": float,
          "embeddings_source": "sentence-transformers"|"hash",
          "n_user_turns": int,
        }
    """
    intents = _user_intents(conversation)
    if len(intents) < 2:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "embeddings_source": "hash" if embed_fn is None else "custom",
            "n_user_turns": len(intents),
        }
    embed = embed_fn or embed_texts
    try:
        embeds = embed(intents)
    except Exception:
        embeds = [_hash_embed(t) for t in intents]
    if not embeds or len(embeds[0]) == 0:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "embeddings_source": "hash",
            "n_user_turns": len(intents),
        }
    base = embeds[0]
    drifts = []
    for vec in embeds[1:]:
        if len(vec) != len(base):
            continue
        drifts.append(1.0 - cosine_similarity(base, vec))
    if not drifts:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "embeddings_source": "hash",
            "n_user_turns": len(intents),
        }
    sorted_d = sorted(drifts)
    return {
        "drift_mean": float(sum(drifts) / len(drifts)),
        "drift_p50": sorted_d[(len(sorted_d) - 1) * 50 // 100],
        "drift_p99": sorted_d[(len(sorted_d) - 1) * 99 // 100],
        "embeddings_source": "hash" if embed_fn is None else "custom",
        "n_user_turns": len(intents),
    }


# ---------------------------------------------------------------------------
# Dead-end detection
# ---------------------------------------------------------------------------


def dead_end_count(
    conversation: Sequence[Turn],
    *,
    max_repeats: int = 3,
    min_chars: int = 8,
) -> int:
    """Count "dead-end" turns: identical-or-near-identical assistant content.

    For each `assistant` turn we look at the previous `max_repeats - 1`
    assistant turns; if the *current* content normalizes equal (case-insensitive
    whitespace-collapsed) to any of them and exceeds `min_chars`, we count +1.
    """
    if not conversation or max_repeats < 1:
        return 0

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    history: list[str] = []
    repeats = 0
    for turn in conversation:
        if turn.role != "assistant":
            continue
        norm = _norm(turn.content)
        if len(norm) >= min_chars:
            for prev in history[-max(0, max_repeats - 1) :]:
                if prev == norm:
                    repeats += 1
                    break
        history.append(norm)
    return int(repeats)


# ---------------------------------------------------------------------------
# Semantic drift (long-horizon)
# ---------------------------------------------------------------------------


def semantic_drift_score(
    conversation: Sequence[Turn],
    *,
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> dict[str, float]:
    """Long-horizon drift: cosine distance from the first assistant message.

    Symmetric to `intent_drift` but uses assistant messages instead of user
    intents. Per spec §4.6 we report the p99 of `1 - cos(...)`.
    """
    if not conversation:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "n_assistant_turns": 0.0,
        }
    assistants = [t.content for t in conversation if t.role == "assistant"]
    n = len(assistants)
    if n < 2:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "n_assistant_turns": float(n),
        }
    embed = embed_fn or embed_texts
    try:
        embeds = embed(assistants)
    except Exception:
        embeds = [_hash_embed(t) for t in assistants]
    base = embeds[0]
    drifts: list[float] = []
    for vec in embeds[1:]:
        if len(vec) != len(base):
            continue
        drifts.append(semantic_drift(base, vec))
    if not drifts:
        return {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "n_assistant_turns": float(n),
        }
    sorted_d = sorted(drifts)
    return {
        "drift_mean": float(sum(drifts) / len(drifts)),
        "drift_p50": sorted_d[(len(sorted_d) - 1) * 50 // 100],
        "drift_p99": sorted_d[(len(sorted_d) - 1) * 99 // 100],
        "n_assistant_turns": float(n),
    }


# ---------------------------------------------------------------------------
# Aggregate helper
# ---------------------------------------------------------------------------


def analyze_conversation(
    conversation: Sequence[Turn],
    *,
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
    stability_metric: bool = True,
) -> dict[str, Any]:
    """Compute the full stability triple (drift, dead-ends, semantic_drift).

    When `stability_metric=False` we still produce the cheap structure-derived
    stats (`dead_end_count`, `n_user_turns`) but skip embedding cosine (it is
    O(N²) and only meaningful for the §4.6 spec metric).
    """
    out: dict[str, Any] = {
        "dead_end_count": dead_end_count(conversation),
    }
    out["intent_drift"] = (
        intent_drift(conversation, embed_fn=embed_fn)
        if stability_metric
        else {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "embeddings_source": "skipped",
            "n_user_turns": sum(1 for t in conversation if t.role == "user"),
        }
    )
    out["semantic_drift"] = (
        semantic_drift_score(conversation, embed_fn=embed_fn)
        if stability_metric
        else {
            "drift_mean": 0.0,
            "drift_p50": 0.0,
            "drift_p99": 0.0,
            "n_assistant_turns": float(
                sum(1 for t in conversation if t.role == "assistant")
            ),
        }
    )
    return out


__all__ = [
    "Turn",
    "embed_texts",
    "intent_drift",
    "dead_end_count",
    "semantic_drift_score",
    "analyze_conversation",
    "DEFAULT_FALLBACK_DIM",
]
