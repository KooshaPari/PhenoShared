"""LLM-as-judge wrapper for MT-Bench (and any other suite needing a judge).

Supports Claude Sonnet 5 by default via the Anthropic SDK; falls back to
stub-mode when `ANTHROPIC_API_KEY` is missing or the SDK is unavailable.

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2 row 5
(MT-Bench) and §3.2 (judge port).
"""

from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any

# Optional SDKs — imported lazily so the module is importable without them.
try:  # pragma: no cover - exercised by integration tests only
    import anthropic

    _HAS_ANTHROPIC = True
except Exception:  # pragma: no cover
    anthropic = None
    _HAS_ANTHROPIC = False


DEFAULT_JUDGE_MODEL = "claude-sonnet-5"
JUDGE_TIMEOUT_S = 60.0
MAX_RETRIES = 3


class JudgeError(RuntimeError):
    """Raised when the judge backend fails after retries."""


@dataclass
class JudgeVerdict:
    """Single judge decision on a (prompt, response) pair."""

    score: float  # in [0, 10] for MT-Bench; arbitrary for general judges
    rationale: str = ""
    raw: str = ""
    judge_model: str = DEFAULT_JUDGE_MODEL
    judge_stub: bool = False
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the JudgeResult to a JSON-friendly dict."""
        return {
            "score": self.score,
            "rationale": self.rationale,
            "raw": self.raw,
            "judge_model": self.judge_model,
            "judge_stub": self.judge_stub,
            "latency_ms": self.latency_ms,
        }


@dataclass
class JudgeRequest:
    """A single judging request: system + user prompt + the response to grade."""

    system_prompt: str = "You are an impartial judge evaluating a model's response."
    user_prompt: str = ""
    response: str = ""
    reference: str = ""
    rubric: str = ""
    max_score: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMJudge:
    """LLM-as-judge wrapper with retry + temperature=0 + stub fallback.

    Spec rule 4: if `ANTHROPIC_API_KEY` env var is missing OR the SDK isn't
    installed, fall back to stub-mode that returns a random verdict in [0,10]
    with `judge_stub=True`. This keeps the bench harness testable in CI.
    """

    def __init__(
        self,
        model: str = DEFAULT_JUDGE_MODEL,
        *,
        api_key: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = JUDGE_TIMEOUT_S,
        max_retries: int = MAX_RETRIES,
        force_stub: bool = False,
        seed: int | None = None,
    ) -> None:
        self.model = model
        self.api_key = (
            api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        )
        self.temperature = float(temperature)
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self.force_stub = bool(force_stub)
        self.seed = seed
        self._stub_mode = self.force_stub or not (self.api_key and _HAS_ANTHROPIC)

    @property
    def is_stub(self) -> bool:
        """True if judge is running in stub mode (no live API call)."""
        return self._stub_mode

    def judge(self, req: JudgeRequest) -> JudgeVerdict:
        """Return a `JudgeVerdict` for the given request."""
        if self._stub_mode:
            return self._stub_verdict(req)
        return self._live_verdict(req)

    # ------------------------------------------------------------------
    # Stub mode — deterministic-by-seed random verdict
    # ------------------------------------------------------------------

    def _stub_verdict(self, req: JudgeRequest) -> JudgeVerdict:
        random.Random(self.seed) if self.seed is not None else random.Random()  # nosec B311
        # Stable hash of request content so repeated calls on the same task
        # return the same verdict (important for deterministic --seed runs).
        seed_src = f"{req.user_prompt[:200]}|{req.response[:200]}".encode()
        digest = sum(seed_src) % (2**32)
        rng2 = random.Random(digest)  # nosec B311
        score = rng2.uniform(0.0, req.max_score)
        rationale = (
            f"[stub judge — model={self.model} stub=True] "
            f"scored {score:.2f}/{req.max_score:.0f} (no API key / SDK)"
        )
        return JudgeVerdict(
            score=round(score, 4),
            rationale=rationale,
            raw="",
            judge_model=self.model,
            judge_stub=True,
            latency_ms=0.0,
        )

    # ------------------------------------------------------------------
    # Live mode — Anthropic SDK with retry + temperature=0
    # ------------------------------------------------------------------

    def _live_verdict(
        self, req: JudgeRequest
    ) -> JudgeVerdict:  # pragma: no cover - integration path
        if not _HAS_ANTHROPIC or anthropic is None:
            raise JudgeError("anthropic SDK not installed but live judge requested")
        assert self.api_key, "api_key must be set for live judge"  # nosec B101
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start = time.time()
            try:
                client = anthropic.Anthropic(
                    api_key=self.api_key, timeout=self.timeout_s
                )
                prompt = self._compose_user_prompt(req)
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    temperature=self.temperature,
                    system=req.system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = self._extract_text(resp)
                elapsed_ms = (time.time() - start) * 1000.0
                score = self._parse_score(text, max_score=req.max_score)
                return JudgeVerdict(
                    score=score,
                    rationale=text.strip(),
                    raw=text,
                    judge_model=self.model,
                    judge_stub=False,
                    latency_ms=elapsed_ms,
                )
            except Exception as exc:  # noqa: BLE001 — judge may fail many ways
                last_err = exc
                # Linear backoff: 0.5s, 1.0s, 1.5s, ...
                time.sleep(0.5 * attempt)
        raise JudgeError(f"judge failed after {self.max_retries} attempts: {last_err}")

    @staticmethod
    def _extract_text(resp: Any) -> str:
        """Extract a flat text string from an Anthropic `messages` response."""
        # SDK >= 0.30 returns `resp.content` as a list of content blocks.
        try:
            blocks = getattr(resp, "content", None) or []
            parts: list[str] = []
            for block in blocks:
                text = getattr(block, "text", None)
                if text is None and isinstance(block, dict):
                    text = block.get("text")
                if text:
                    parts.append(str(text))
            return "\n".join(parts)
        except Exception:  # pragma: no cover - defensive
            return str(resp)

    @staticmethod
    def _compose_user_prompt(req: JudgeRequest) -> str:
        """Compose the user-side prompt sent to the judge model."""
        parts: list[str] = []
        if req.rubric:
            parts.append(f"## Rubric\n{req.rubric}\n")
        parts.append("## Prompt\n" + req.user_prompt.strip() + "\n")
        if req.reference:
            parts.append("## Reference answer\n" + str(req.reference).strip() + "\n")
        parts.append("## Response to grade\n" + req.response.strip() + "\n")
        parts.append(
            f"\nReply with a single integer score in [0, {int(req.max_score)}] on the "
            "first line, followed by a one-paragraph justification."
        )
        return "\n".join(parts)

    _SCORE_LINE_RE = re.compile(r"^\s*(?:score\s*[:=]?\s*)?(-?\d+(?:\.\d+)?)")

    @classmethod
    def _parse_score(cls, text: str, max_score: float = 10.0) -> float:
        """Pull the first numeric score out of a judge response text.

        Defaults to 0.0 if parsing fails (so the calling suite can still
        aggregate; degraded judges shouldn't crash the whole harness).
        """
        if not text:
            return 0.0
        for line in text.splitlines():
            m = cls._SCORE_LINE_RE.match(line)
            if m:
                try:
                    score = float(m.group(1))
                except ValueError:
                    return 0.0
                return max(0.0, min(score, max_score))
        return 0.0


__all__ = [
    "DEFAULT_JUDGE_MODEL",
    "JUDGE_TIMEOUT_S",
    "JudgeError",
    "JudgeRequest",
    "JudgeVerdict",
    "LLMJudge",
    "MAX_RETRIES",
]
