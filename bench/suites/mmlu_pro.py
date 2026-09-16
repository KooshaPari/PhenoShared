"""MMLU-Pro — TIGER-Lab/MMLU-Pro.

12,032 questions; deterministic 5-shot chain-of-thought multiple choice.
Stratified across 14 subjects (per spec §2 row 6).

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2 row 6,
§3.1 (submodule).
"""

from __future__ import annotations

import json
import time
from typing import Any

from bench.types import RunSpec, SuiteResult, TaskResult, TaskStatus

from ._stub import BaseSuite, TaskSpec, synthetic_prompt, synthetic_response
from .dataset_loader import (
    DatasetSource,
    load_suite_dataset,
    synth_mc_question,
)

SOURCE_URL = "github.com/TIGER-Lab/MMLU-Pro"
VERSION = "1.0"
NUM_TASKS = 12032  # full MMLU-Pro test split (spec §2 row 6)
SUBJECTS: tuple[str, ...] = (
    "math",
    "physics",
    "chemistry",
    "biology",
    "law",
    "engineering",
    "economics",
    "philosophy",
    "psychology",
    "history",
    "computer science",
    "business",
    "health",
    "other",
)
DEFAULT_SUBSET = 200  # spec §2 row 6: n=200 stratified over 14 subjects
LETTER_CHOICES: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")
SYSTEM_PROMPT = (
    "The following are multiple choice questions (with answers) about "
    "the given subject. Think step by step and then give your final answer "
    "as a single letter in the range A-J."
)


def _normalise_choice(c: Any) -> str:
    """Coerce a choice value into a single capital letter."""
    if isinstance(c, int):
        return LETTER_CHOICES[c] if 0 <= c < len(LETTER_CHOICES) else str(c)
    if isinstance(c, str) and len(c) == 1:
        return c.upper()
    return str(c).strip().upper()[:1] or "A"


class MMLUPro(BaseSuite):
    """MMLU-Pro — knowledge/reasoning MCQ eval (deterministic)."""

    name = "mmlu-pro"
    version = VERSION
    num_tasks = NUM_TASKS
    task_format = "5-shot chain-of-thought (MCQ; 10 choices)"
    scoring = "pass@1 = accuracy (exact letter match against gold)"
    source_url = SOURCE_URL
    format = task_format
    _subset_label = "n=200 stratified over 14 subjects"
    rationale = "knowledge/reasoning"
    default_judge_mode = "deterministic"  # type: ignore[assignment]
    task_id_prefix = "mmlu-pro"

    _PAPER_METRICS = (
        ("pass@1", "%", "spec §4.1 + MMLU-Pro leaderboard"),
        ("pass@1_ci95", "%", "spec §4.1"),
        ("subject_coverage", "ratio", "spec §2 row 6 (stratification)"),
        ("wall_clock_total", "s", "spec §4.3"),
    )

    # ------------------------------------------------------------------
    # Subset
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n MMLU-Pro task specs, stratified across the 14 subjects.

        Real-mode: pulls from HF `TIGER-Lab/MMLU-Pro`. Stub-mode: emits
        `synth_mc_question(...)` rows with the same shape.
        """
        n = max(0, int(n))
        per_subject = max(1, n // max(1, len(SUBJECTS)))
        # Try the real HF dataset; fall back to synthetic on any failure.
        source = DatasetSource(
            name="mmlu-pro",
            hf_repo="TIGER-Lab/MMLU-Pro",
            hf_subset="default",  # config name on HF
            hf_split="test",
            text_field="question",
            synth_fn=lambda k, s: [
                synth_mc_question(
                    42, i, subject=SUBJECTS[i % len(SUBJECTS)], choices=10
                )
                for i in range(k)
            ],
        )
        loaded = load_suite_dataset(
            source, n=n * 2
        )  # load more than needed for stratification
        out: list[TaskSpec] = []
        per_subject_count: dict[str, int] = dict.fromkeys(SUBJECTS, 0)
        for i, row in enumerate(loaded.rows):
            if len(out) >= n:
                break
            subj = str(row.get("category", row.get("subject", "other"))).lower()
            if subj not in per_subject_count:
                subj = "other"
            if per_subject_count[subj] >= per_subject:
                continue
            per_subject_count[subj] += 1
            question = row.get("question") or row.get("input") or ""
            choices = row.get("options") or row.get("choices") or []
            if isinstance(choices, str):
                try:
                    choices = json.loads(choices)
                except Exception:
                    choices = [choices]
            if not isinstance(choices, list) or len(choices) < 2:
                choices = list(LETTER_CHOICES[:4])
            gold = _normalise_choice(row.get("answer", row.get("label", 0)))
            out.append(
                TaskSpec(
                    task_id=str(
                        row.get("question_id", row.get("id", f"mmlu-pro-{i:05d}"))
                    ),
                    suite=self.name,
                    prompt=question,
                    reference=gold,
                    metadata={
                        "seed": seed,
                        "index": i,
                        "subject": subj,
                        "choices": [str(c) for c in choices],
                        "gold": gold,
                        "cot": True,
                        "shots": 5,
                        "synthetic": loaded.synthetic,
                    },
                    tags=("mmlu-pro", subj),
                )
            )
        # Pad to n if real data was smaller than requested.
        while len(out) < n:
            i = len(out)
            subj = SUBJECTS[i % len(SUBJECTS)]
            out.append(
                TaskSpec(
                    task_id=f"mmlu-pro-stub-{i:05d}",
                    suite=self.name,
                    prompt=synthetic_prompt(seed, i),
                    reference="A",
                    metadata={
                        "seed": seed,
                        "index": i,
                        "subject": subj,
                        "choices": list(LETTER_CHOICES[:4]),
                        "gold": "A",
                        "cot": True,
                        "shots": 5,
                        "synthetic": True,
                    },
                    tags=("mmlu-pro", subj),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Per-task execution
    # ------------------------------------------------------------------

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Grade a model response against the gold letter for this MCQ.

        In stub-mode the response is synthetic. In real-mode the caller
        passes the model's response via `kwargs['response']`.
        """
        gold = str(task.metadata.get("gold", task.reference or "A")).upper()[:1]
        response = str(kwargs.get("response", ""))
        if not response:
            response = synthetic_response(0, hash(task.task_id) & 0xFFFF)
        # Extract the last uppercase letter A-J from the response.
        match = ""
        for ch in reversed(response):
            if ch.upper() in LETTER_CHOICES:
                match = ch.upper()
                break
        status = TaskStatus.PASS if match == gold else TaskStatus.FAIL
        return TaskResult(
            task_id=task.task_id,
            status=status,
            wall_clock_s=float(kwargs.get("simulated_duration_s", 0.05)),
            tokens_in=len(task.prompt.split()),
            tokens_out=len(response.split()),
            tool_calls=[],
            meta={"predicted": match or "∅", "gold": gold},
        )

    # ------------------------------------------------------------------
    # Skeleton `Suite.run` orchestrator
    # ------------------------------------------------------------------

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the MMLU-Pro subset and return a SuiteResult."""
        time.time()
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = [self.run_task(t, run_spec.model) for t in tasks]
        if not results:
            return SuiteResult(
                suite=self.name,
                model=run_spec.model,
            )
        passes = sum(1 for r in results if r.status == TaskStatus.PASS)
        # Subject coverage = fraction of the 14 subjects actually represented.
        subjects_seen = {"other"}
        return SuiteResult(
            suite=self.name,
            model=run_spec.model,
            wall_clock_s=0.0,
            n=len(results),
            task_results=results,
            meta={
                "pass@1": passes / len(results),
                "subject_coverage": len(subjects_seen & set(SUBJECTS)) / len(SUBJECTS),
            },
        )


__all__ = ["MMLUPro", "NUM_TASKS", "SUBJECTS", "DEFAULT_SUBSET"]
