"""GPQA Diamond — idavidrein/gpqa.

198 questions, graduate-level reasoning. 0-shot chain-of-thought. MCQ is
deterministic; open-ended variants fall through to the LLM judge (spec
§2 row 7).

Anti-contamination canary: spec §3.3 row "GPQA password" requires gating
prompts with the string `deserted-untie-orchid` before any leakage.
"""

from __future__ import annotations

import time
from typing import Any

from bench.types import RunSpec, SuiteResult, TaskResult, TaskStatus

from ._stub import BaseSuite, TaskSpec, synthetic_prompt, synthetic_response
from .dataset_loader import (
    DatasetSource,
    load_suite_dataset,
    synth_mc_question,
)

SOURCE_URL = "github.com/idavidrein/gpqa"
VERSION = "1.0"
NUM_TASKS = 198  # Diamond split (198 hard Qs, spec §2 row 7)
ANTI_CONTAMINATION_PASSWORD = "deserted-untie-orchid"  # spec §3.3  # nosec B105
DIAMOND_SUBJECTS: tuple[str, ...] = ("physics", "chemistry", "biology")
LETTER_CHOICES: tuple[str, ...] = ("A", "B", "C", "D")


def _normalise_choice(c: Any) -> str:
    if isinstance(c, int):
        return LETTER_CHOICES[c] if 0 <= c < len(LETTER_CHOICES) else str(c)
    if isinstance(c, str) and len(c) == 1:
        return c.upper()
    return str(c).strip().upper()[:1] or "A"


class GPQADiamond(BaseSuite):
    """GPQA Diamond — graduate-level reasoning benchmark."""

    name = "gpqa-diamond"
    version = VERSION
    num_tasks = NUM_TASKS
    task_format = "0-shot chain-of-thought (MCQ; 4 choices)"
    scoring = "pass@1 = accuracy (exact letter match); open-ended → LLM judge"
    source_url = SOURCE_URL
    format = task_format
    _subset_label = "full 198 (small)"
    rationale = "grad reasoning"
    default_judge_mode = "deterministic"  # type: ignore[assignment]
    task_id_prefix = "gpqa-d"

    _PAPER_METRICS = (
        ("pass@1", "%", "spec §4.1 + GPQA Diamond leaderboard"),
        ("pass@1_ci95", "%", "spec §4.1"),
        ("wall_clock_total", "s", "spec §4.3"),
    )

    # ------------------------------------------------------------------
    # Subset
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n GPQA Diamond task specs.

        Real-mode: pulls from HF `Idavidrein/gpqa`. Stub-mode: emits synthetic
        graduate-style MCQs. Anti-contamination password is embedded into
        the metadata so downstream tools can assert the gate.
        """
        n = max(0, int(n))
        source = DatasetSource(
            name="gpqa-diamond",
            hf_repo="Idavidrein/gpqa",
            hf_subset="gpqa_diamond",
            hf_split="train",
            text_field="Question",
            synth_fn=lambda k, s: [
                synth_mc_question(42, i, subject=DIAMOND_SUBJECTS[i % 3], choices=4)
                for i in range(k)
            ],
        )
        loaded = load_suite_dataset(source, n=n)
        out: list[TaskSpec] = []
        for i, row in enumerate(
            loaded.rows[:n] if len(loaded.rows) >= n else loaded.rows
        ):
            question = row.get("Question") or row.get("question") or ""
            choices = [
                row.get("Correct Answer") or row.get("correct_answer") or "",
                row.get("Incorrect Answer 1") or row.get("incorrect_answer_1") or "",
                row.get("Incorrect Answer 2") or row.get("incorrect_answer_2") or "",
                row.get("Incorrect Answer 3") or row.get("incorrect_answer_3") or "",
            ]
            gold_idx = 0
            gold = _normalise_choice(gold_idx)
            out.append(
                TaskSpec(
                    task_id=str(row.get("Record ID", row.get("id", f"gpqa-d-{i:04d}"))),
                    suite=self.name,
                    prompt=question,
                    reference=gold,
                    metadata={
                        "seed": seed,
                        "index": i,
                        "subdomain": str(
                            row.get("Subdomain", row.get("subject", "physics"))
                        ).lower(),
                        "high_level_domain": str(
                            row.get("High-level domain", row.get("domain", "physics"))
                        ).lower(),
                        "choices": [str(c) for c in choices],
                        "gold": gold,
                        "anti_contamination_password": ANTI_CONTAMINATION_PASSWORD,
                        "cot": True,
                        "shots": 0,
                        "synthetic": loaded.synthetic,
                    },
                    tags=("gpqa", "diamond"),
                )
            )
        # Pad with synthetic if HF was empty.
        while len(out) < n:
            i = len(out)
            out.append(
                TaskSpec(
                    task_id=f"gpqa-d-stub-{i:04d}",
                    suite=self.name,
                    prompt=synthetic_prompt(seed, i),
                    reference="A",
                    metadata={
                        "seed": seed,
                        "index": i,
                        "subdomain": DIAMOND_SUBJECTS[i % 3],
                        "high_level_domain": DIAMOND_SUBJECTS[i % 3],
                        "choices": list(LETTER_CHOICES),
                        "gold": "A",
                        "anti_contamination_password": ANTI_CONTAMINATION_PASSWORD,
                        "cot": True,
                        "shots": 0,
                        "synthetic": True,
                    },
                    tags=("gpqa", "diamond", "stub"),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Per-task execution
    # ------------------------------------------------------------------

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Grade a model response against the gold letter (deterministic)."""
        gold = str(task.metadata.get("gold", task.reference or "A")).upper()[:1]
        response = str(kwargs.get("response", ""))
        if not response:
            response = synthetic_response(0, hash(task.task_id) & 0xFFFF)
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
            tool_calls=0,
            meta={"predicted": match or chr(8709), "gold": gold},
        )

    # ------------------------------------------------------------------
    # Skeleton `Suite.run` orchestrator
    # ------------------------------------------------------------------

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the GPQA-Diamond subset and return a SuiteResult."""
        started_at = time.time()
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = [self.run_task(t, run_spec.model) for t in tasks]
        if not results:
            return SuiteResult(
                suite=self.name,
                model=run_spec.model,
                wall_clock_s=time.time() - started_at,
                n=len(results),
                task_results=results,
                meta={},
            )
        sum(1 for r in results if r.status == TaskStatus.PASS)
        return SuiteResult(
            suite=self.name,
            model=run_spec.model,
            wall_clock_s=time.time() - started_at,
            n=len(results),
            task_results=results,
            meta={},
        )


__all__ = [
    "GPQADiamond",
    "NUM_TASKS",
    "ANTI_CONTAMINATION_PASSWORD",
    "DIAMOND_SUBJECTS",
]
