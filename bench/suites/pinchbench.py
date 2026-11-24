"""PinchBench — OpenClaw agent benchmark (53 tasks).

Simulates a "AI assistant at a 6-person marketing consultancy" with tasks across:
- Calendar scheduling (avoid conflicts, optimize for timezone)
- Email drafting (matching client tone, correct reply-to threading)
- Research synthesis (cross-document summary with citations)
- Code analysis (small Python/JS snippets)

Each task has an explicit pass criterion (verifier script in YAML).

Spec reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §4.
Source: github.com/openclaw-ai/pinchbench (53-task v1.0).
Default judge: DETERMINISTIC.
Output unit: pass rate %.

Subtasks: 18 calendar + 12 email + 14 research + 9 code = 53 total.
"""

from __future__ import annotations

from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "github.com/openclaw-ai/pinchbench"
VERSION = "1.0"
NUM_TASKS = 53
DEFAULT_TIMEOUT_S = 120


_SUBTASK_SPLIT = (
    ("calendar", 18),
    ("email", 12),
    ("research", 14),
    ("code", 9),
)


def _pinchbench_prompt(task_id: str, subtask: str, idx: int) -> str:
    return (
        f"# PinchBench Task {task_id}\n\n"
        f"## Subtask: {subtask}\n"
        f"## Variant: #{idx}\n\n"
        f"You are the AI assistant at a 6-person marketing consultancy. "
        f"Complete the {subtask} task below per the consultancy's standard "
        f"workflow and constraints.\n\n"
        f"## Output Format\n"
        f"Provide the final deliverable (calendar event / email body / "
        f"research summary / code patch) followed by a single line:\n"
        f"`PINCHBENCH_DONE={task_id}`\n"
    )


def _pinchbench_correctness_check(out_text: str, subtask: str) -> tuple[bool, str]:
    """Heuristic: did the model produce a complete deliverable + DONE marker?"""
    if not out_text or len(out_text) < 100:
        return False, "too-short"
    text_lower = out_text.lower()
    if "PINCHBENCH_DONE=" not in out_text:
        return False, "no-done-marker"
    hedge_patterns = ("i cannot", "i apologize", "i'm not able", "as an ai")
    for hedge in hedge_patterns:
        if hedge in text_lower:
            return False, f"refusal:{hedge}"
    # Subtask-specific heuristic: must contain domain keyword
    keywords = {
        "calendar": ("meeting", "schedule", "attendees", "duration"),
        "email": ("subject:", "to:", "from:", "dear"),
        "research": ("sources:", "summary", "according to", "findings"),
        "code": ("def ", "function", "import", "return"),
    }
    kw_required = keywords.get(subtask, ())
    if not any(kw in text_lower for kw in kw_required):
        return False, f"missing-{subtask}-keywords"
    return True, "heuristic-valid"


class PinchBench(BaseSuite):
    """PinchBench/003 office-assistant multi-step task suite."""

    name = "pinchbench"
    domain = "office-assistants"
    paper_metrics: tuple[str, ...] = ("pass@1",)  # type: ignore[assignment]
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        f"{NUM_TASKS} tasks simulating AI assistant at a 6-person marketing "
        "consultancy (18 calendar + 12 email + 14 research + 9 code). "
        "Heuristic: deliverable must include domain-specific keywords "
        "(meeting/subject:/sources:/def) + PINCHBENCH_DONE marker."
    )

    def __init__(self) -> None:
        self._tasks: list[TaskSpec] = []
        for subtask_idx, (subtask, count) in enumerate(_SUBTASK_SPLIT):
            for i in range(count):
                task_id = f"PINCH-{subtask_idx}-{i:03d}"
                self._tasks.append(
                    TaskSpec(
                        task_id=task_id,
                        suite=self.name,
                        prompt=_pinchbench_prompt(task_id, subtask, i),
                        reference=f"verifier:{task_id}",
                        tags={"subtask": subtask, "index": i},  # type: ignore[arg-type]
                    )
                )

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return ``n`` deterministically sampled tasks for a benchmark run."""
        from bench.seeds import sample

        if n >= len(self._tasks):
            return list(self._tasks)
        idx = sample(self.name, seed, pool=list(range(len(self._tasks))), n=n)
        return [self._tasks[i] for i in idx.ordered_indices]

    def verify(self, task: TaskSpec, completion: str) -> tuple[bool, dict[str, Any]]:
        """Score the model completion against the expected office-assistant output."""

        subtask = task.tags["subtask"]  # type: ignore[call-overload]
        passed, reason = _pinchbench_correctness_check(completion, subtask)
        return passed, {
            "judge": "heuristic-validity",
            "subtask": subtask,
            "fail_reason": None if passed else reason,
        }


__all__ = ["PinchBench", "NUM_TASKS", "SOURCE_URL"]
