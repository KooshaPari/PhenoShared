"""L2 — Verifier: normalised pass/fail + reward ∈ [0,1].

The verifier converts raw suite-run output into `JudgeVerdict` instances.
It normalises across all 17 suite types so L3 (Critic) and L4 (Optimizer)
operate on a uniform reward signal.

From the RLVR-AF spec:
  "Verifier: a component that examines a Trail and emits rewards. It
   converts raw pass/fail → normalised ∈ [0,1], handles partial credit,
   and attaches debug metadata."
"""

from __future__ import annotations

import math

from bench.rlvr_af.trace import JudgeVerdict, Transition

# ---------------------------------------------------------------------------
# Base verifier
# ---------------------------------------------------------------------------


class BaseVerifier:
    """Verifier base. Subclass per-suite or use a universal heuristic."""

    def __call__(self, t: Transition) -> JudgeVerdict:
        """Inspect a transition and return a verdict (reward ∈ [0,1])."""
        return self.verify(t)

    def verify(self, t: Transition) -> JudgeVerdict:
        """Verify a transition (subclasses implement)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Universal heuristic verifier (works with any suite)
# ---------------------------------------------------------------------------


class HeuristicVerifier(BaseVerifier):
    """Universal verifier that assigns reward based on simple heuristics.

    Reward rules (applied in order):
      1. 0.0 if empty completion or starts with "[error]"/"error:".
      2. 1.0 if completion contains the expected string (case-insensitive).
      3. 0.5 if completion is non-empty but doesn't match expected.
      4. 0.0 as fallback.
    """

    def verify(self, t: Transition) -> JudgeVerdict:
        """Compute a heuristic reward based on completion vs expected."""
        comp = (t.artifact.completion or "").strip()
        exp = t.artifact.expected
        reward = 0.0
        passed = False
        reason = ""

        if not comp or comp.startswith("[error]") or comp.startswith("error:"):
            reward = 0.0
            passed = False
            reason = "empty or error completion"
        elif exp is not None:
            if str(exp).strip().lower() in comp.lower():
                reward = 1.0
                passed = True
                reason = "expected string found"
            else:
                reward = 0.5 if len(comp) > 10 else 0.0
                passed = False
                reason = f"expected '{exp}' not found in '{comp[:60]}'"
        else:
            # No expected — reward = length-based heuristic
            reward = min(1.0, len(comp) / 64)
            passed = reward > 0.5
            reason = "length-based heuristic"

        return JudgeVerdict(
            passed=passed,
            reward=reward,
            reason=reason,
            meta={
                "completion_len": len(comp),
                "expected": str(exp) if exp else "",
            },
        )


# ---------------------------------------------------------------------------
# MLX-native verifier (uses MLX's fast.norms if available)
# ---------------------------------------------------------------------------


class MLXVerifier(BaseVerifier):
    """Verifier that uses MLX to compare embeddings.

    Falls back to HeuristicVerifier when mlx is unavailable or the
    completion/expected pair doesn't yield meaningful embeddings.
    """

    def __init__(self) -> None:
        """Initialize the MLX verifier; lazily import sentence-transformers."""
        self._heuristic = HeuristicVerifier()
        self._mlx = None
        try:
            import mlx.core as mx

            self._mlx = mx
        except ImportError:
            pass

    def verify(self, t: Transition) -> JudgeVerdict:
        """Compute a cosine-similarity reward via sentence-transformers; fallback to heuristic."""
        if self._mlx is None:
            return self._heuristic.verify(t)
        comp = (t.artifact.completion or "").strip()
        exp = t.artifact.expected
        if not comp or not exp:
            return self._heuristic.verify(t)
        # Use MLX cosine similarity as reward signal
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")
            vecs = model.encode([comp, str(exp)])
            sim = sum(a * b for a, b in zip(vecs[0], vecs[1])) / (
                math.sqrt(sum(a * a for a in vecs[0]))
                * math.sqrt(sum(b * b for b in vecs[1]))
                + 1e-12
            )
            reward = max(0.0, min(1.0, sim))
            passed = reward > 0.75
            return JudgeVerdict(
                passed=passed,
                reward=reward,
                reason=f"cosine_similarity={sim:.4f}",
                meta={"cosine_sim": sim},
            )
        except ImportError:
            return self._heuristic.verify(t)


# ---------------------------------------------------------------------------
# Verifier factory
# ---------------------------------------------------------------------------

_VERIFIERS: dict[str, type[BaseVerifier]] = {}


def register_verifier(key: str, cls: type[BaseVerifier]) -> None:
    """Register a verifier class under a string key (used by tests + suites)."""
    _VERIFIERS[key] = cls


def get_verifier(key: str = "heuristic") -> BaseVerifier:
    """Look up a verifier by key; falls back to ``HeuristicVerifier``."""
    cls = _VERIFIERS.get(key, HeuristicVerifier)
    return cls()


# Register defaults
register_verifier("heuristic", HeuristicVerifier)
register_verifier("mlx", MLXVerifier)


__all__ = [
    "BaseVerifier",
    "HeuristicVerifier",
    "MLXVerifier",
    "register_verifier",
    "get_verifier",
]
