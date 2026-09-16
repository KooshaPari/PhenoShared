"""LLM-judge orchestration for the runner (spec §4.7 + rule §9).

The judge runner reads `TaskResult` rows whose suite uses the LLM-judge mode
(spec rule §8), batches them in groups of `batch_size` (default 8 per spec),
and posts the batches to a judge model (default Claude) via the configured
`AnthropicAdapter`. Verdicts are attached as `TaskResult.reward` and as an
extra dict under `metrics["judge"]`.

Batching rules:

* Batches are sized so a single API call carries up to `batch_size` prompts
  rendered as a numbered list. The judge is asked to reply with one JSON
  line per prompt: `{"i": 0, "verdict": "PASS|FAIL", "score": 0..1}`.
* The default judge model is `claude-sonnet-5` per AGENTS.md spec Q10.
* When the suite declares `judge_mode=DETERMINISTIC`, the judge runner
  is a no-op (verdicts are determined by the verifier, not an LLM).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from bench.model_adapter import AnthropicAdapter, Completion, ModelAdapter
from bench.types import JudgeMode, TaskResult, TaskStatus

DEFAULT_BATCH_SIZE = 8
DEFAULT_JUDGE_MODEL = "claude-sonnet-5"


@dataclass
class JudgeVerdict:
    """Result of a single LLM-judge call for one task."""

    task_id: str
    verdict: str  # "PASS" | "FAIL" | "UNKNOWN"
    score: float
    reasoning: str = ""
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize the JudgeVerdict to a JSON-friendly dict."""
        return {
            "task_id": self.task_id,
            "verdict": self.verdict,
            "score": self.score,
            "reasoning": self.reasoning,
        }


@dataclass
class JudgeBatch:
    """A single batch of task prompts to be judged in one API call."""

    batch_idx: int
    task_ids: list[str]
    prompts: list[str]
    verdict: JudgeVerdict | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the JudgeBatch to a JSON-friendly dict."""
        return {
            "batch_idx": self.batch_idx,
            "task_ids": list(self.task_ids),
            "prompts": list(self.prompts),
            "verdict": self.verdict.to_dict() if self.verdict else None,
        }


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


JUDGE_SYSTEM = (
    "You are a strict evaluator for benchmark outputs. For each numbered "
    "prompt below, read it together with the model's answer and decide "
    "PASS/FAIL. Reply ONLY with a JSON array of objects, one per prompt, in "
    'this shape: [{"i": 0, "verdict": "PASS", "score": 0.9, '
    '"reasoning": "..."}, ...]. Do not include any other text.'
)


def _render_batch_prompt(prompts: Sequence[str]) -> str:
    """Build the user-side prompt that asks the judge for N verdicts.

    Each prompt in `prompts` is treated as already containing both the original
    question and the model's answer (caller encodes them as e.g.
    ``"PROMPT: ... \\n ANSWER: ..."``). The judge returns one verdict per item.
    """
    sections: list[str] = []
    for i, prompt in enumerate(prompts):
        sections.append(f"[{i}]\n{prompt}")
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


_VERDICT_RE = re.compile(r"\"verdict\"\s*:\s*\"(PASS|FAIL|UNKNOWN)\"", re.IGNORECASE)
_SCORE_RE = re.compile(r"\"score\"\s*:\s*([0-9]+(?:\.[0-9]+)?)")


def _parse_verdicts(raw: str, expected: int) -> list[dict[str, Any]]:
    """Robust parse of one or more judge verdicts from a single response."""
    text = raw.strip()
    # First try strict JSON.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [_normalize_verdict(item, i) for i, item in enumerate(parsed)]
    except Exception:  # nosec B110
        pass
    # Try to find a JSON array inside a markdown block.
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                return [_normalize_verdict(item, i) for i, item in enumerate(parsed)]
        except Exception:  # nosec B110
            pass
    # Last-resort regex sweep per known line.
    findings: list[dict[str, Any]] = []
    for i in range(expected):
        window_start = raw.find(f"[{i}]")
        window_end = (
            raw.find(f"[{i + 1}]", window_start + 1) if window_start >= 0 else -1
        )
        snippet = (
            raw[window_start : window_end if window_end > 0 else len(raw)]
            if window_start >= 0
            else ""
        )
        vm = _VERDICT_RE.search(snippet)
        sm = _SCORE_RE.search(snippet)
        if not vm:
            continue
        try:
            score = float(sm.group(1)) if sm else 0.0
        except ValueError:
            score = 0.0
        findings.append(
            {"i": i, "verdict": vm.group(1).upper(), "score": max(0.0, min(1.0, score))}
        )
    return findings


def _normalize_verdict(item: Any, idx: int) -> dict[str, Any]:
    """Coerce a single (possibly malformed) parsed item to the schema."""
    if not isinstance(item, dict):
        return {"i": idx, "verdict": "UNKNOWN", "score": 0.0, "reasoning": ""}
    v = item.get("verdict", "UNKNOWN")
    if not isinstance(v, str):
        v = "UNKNOWN"
    v = v.upper()
    if v not in {"PASS", "FAIL", "UNKNOWN"}:
        v = "UNKNOWN"
    try:
        s = float(item.get("score", 0.0))
    except (TypeError, ValueError):
        s = 0.0
    s = max(0.0, min(1.0, s))
    reasoning = item.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)
    return {"i": idx, "verdict": v, "score": s, "reasoning": reasoning}


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------


def build_batches(
    blocks: Sequence[tuple[str, str]],
    task_ids: Sequence[str],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[JudgeBatch]:
    """Pair `blocks` and `task_ids`, then chunk into batches of `batch_size`."""
    if len(blocks) != len(task_ids):
        raise ValueError("blocks and task_ids length mismatch")
    if batch_size <= 0:
        batch_size = DEFAULT_BATCH_SIZE
    out: list[JudgeBatch] = []
    for batch_idx in range(0, len(blocks), batch_size):
        chunk_p = list(blocks[batch_idx : batch_idx + batch_size])
        chunk_t = list(task_ids[batch_idx : batch_idx + batch_size])
        out.append(
            JudgeBatch(
                batch_idx=len(out),
                task_ids=chunk_t,
                prompts=[p for p, _ in chunk_p],
            )
        )
    return out


def evaluate_batch(
    batch: JudgeBatch,
    *,
    adapter: ModelAdapter | None = None,
    completion_fn: Callable[[str], Completion] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> JudgeBatch:
    """Run one batch through the judge; attach `verdict` field to the batch.

    `completion_fn` lets tests stub the model call without standing up the
    `AnthropicAdapter`; either `adapter` or `completion_fn` must be supplied.
    """
    if batch.verdict is not None:
        return batch
    if adapter is None and completion_fn is None:
        raise ValueError("either adapter or completion_fn must be provided")

    rendered = _render_batch_prompt(batch.prompts)
    if completion_fn is not None:
        comp = completion_fn(rendered)
    else:
        # Adapter path: feed rendered batch as a single user message.
        comp = adapter.complete(  # type: ignore[union-attr]
            rendered,
            temperature=temperature,
            max_tokens=max_tokens,
            system=JUDGE_SYSTEM,
        )
    findings = _parse_verdicts(comp.text, expected=len(batch.task_ids))
    # Attach per-task verdicts on the batch for downstream mapping.
    by_idx = {f.get("i"): f for f in findings}
    verdicts = []
    for i, tid in enumerate(batch.task_ids):
        f = by_idx.get(i) or {
            "i": i,
            "verdict": "UNKNOWN",
            "score": 0.0,
            "reasoning": "",
        }
        verdicts.append(
            JudgeVerdict(
                task_id=tid,
                verdict=str(f.get("verdict", "UNKNOWN")),
                score=float(f.get("score", 0.0)),
                reasoning=str(f.get("reasoning", "")),
                raw=comp.text,
            )
        )
    batch.verdict = (
        verdicts[0]
        if len(verdicts) == 1
        else JudgeVerdict(
            task_id=";".join(batch.task_ids),
            verdict="BATCH",
            score=float(sum(v.score for v in verdicts) / max(1, len(verdicts))),
            reasoning="batch aggregate",
            raw=comp.text,
        )
    )
    # Stash per-task verdicts in `extra` for callers to consume.
    batch._per_task_verdicts = verdicts
    return batch


# ---------------------------------------------------------------------------
# Apply verdicts back to TaskResults
# ---------------------------------------------------------------------------


def attach_verdicts(
    batches: Sequence[JudgeBatch],
    task_results: list[TaskResult],
) -> list[TaskResult]:
    """In-place: attach judge verdict metrics to each `TaskResult`."""
    by_task: dict[str, JudgeVerdict] = {}
    for batch in batches:
        per_task = getattr(batch, "_per_task_verdicts", None) or []
        if (
            not per_task
            and batch.verdict is not None
            and batch.verdict.task_id not in by_task
            and len(batch.task_ids) == 1
        ):
            per_task = [batch.verdict]
        for v in per_task:
            by_task[v.task_id] = v
    for tr in task_results:
        v = by_task.get(tr.task_id)
        if v is None:
            continue
        tr.metrics["judge"] = v.score
        tr.message = (tr.message + " | judge=" + v.verdict).strip(" |")
        # PASS/Fail mapping respects existing ERROR/TIMEOUT and only overrides
        # when the verifier already declared PASS or FAIL.
        if v.verdict == "FAIL" and tr.status == TaskStatus.PASS:
            tr.status = TaskStatus.FAIL
            tr.reward = 0.0
        elif v.verdict == "PASS" and tr.status == TaskStatus.FAIL:
            tr.status = TaskStatus.PASS
            tr.reward = 1.0
    return task_results


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class JudgeRunResult:
    """Aggregate of one judge-runner invocation."""

    judge_model: str
    judge_mode: JudgeMode
    batches: list[JudgeBatch] = field(default_factory=list)
    verdicts: list[JudgeVerdict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the JudgeRunResult to a JSON-friendly dict."""
        return {
            "judge_model": self.judge_model,
            "judge_mode": self.judge_mode.value,
            "batches": [b.to_dict() for b in self.batches],
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


def run_judge(
    task_results: list[TaskResult],
    *,
    blocks: list[tuple[str, str]],
    judge_model: str = DEFAULT_JUDGE_MODEL,
    judge_mode: JudgeMode = JudgeMode.LLM,
    batch_size: int = DEFAULT_BATCH_SIZE,
    completion_fn: Callable[[str], Completion] | None = None,
    api_key: str | None = None,
) -> JudgeRunResult:
    """Top-level: batch the `(prompt, answer)` pairs, judge them, attach verdicts.

    Returns a `JudgeRunResult` and mutates the input `task_results` so each
    `TaskResult` carries its judge-driven status / reward / message.
    """
    if judge_mode == JudgeMode.DETERMINISTIC:
        return JudgeRunResult(judge_model=judge_model, judge_mode=judge_mode)
    if not blocks:
        return JudgeRunResult(judge_model=judge_model, judge_mode=judge_mode)
    task_ids = [tr.task_id for tr in task_results]
    batches = build_batches(blocks, task_ids, batch_size=batch_size)
    # Use an adapter unless a stubbed `completion_fn` was passed (tests).
    adapter: ModelAdapter | None = None
    if completion_fn is None:
        try:
            adapter = AnthropicAdapter(model_id=judge_model, api_key=api_key)  # type: ignore[misc]
        except Exception:
            adapter = None
    verdicts_all: list[JudgeVerdict] = []
    for batch in batches:
        evaluate_batch(batch, adapter=adapter, completion_fn=completion_fn)
        per_task = getattr(batch, "_per_task_verdicts", None) or []
        verdicts_all.extend(per_task)
    attach_verdicts(batches, task_results)
    return JudgeRunResult(
        judge_model=judge_model,
        judge_mode=judge_mode,
        batches=batches,
        verdicts=verdicts_all,
    )


__all__ = [
    "JudgeVerdict",
    "JudgeBatch",
    "JudgeRunResult",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_JUDGE_MODEL",
    "build_batches",
    "evaluate_batch",
    "attach_verdicts",
    "run_judge",
]
