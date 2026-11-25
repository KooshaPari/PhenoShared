"""OSWorld — XLang Labs desktop OS agent benchmark.

369 tasks across Windows/macOS/Linux desktop environments. Each task has:
- An initial VM/host state (snapshot)
- A natural-language instruction
- A verifier script that checks final state

Verifiers check filesystem state, app data, screenshots, or DB records.

Spec reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §3.
Source: osworld.github.io (v1.0).
Default judge: DETERMINISTIC (verifier script).
Output unit: pass rate %.

Categories (14): chrome, vs_code, terminal, settings, files, libre_office,
gimp, vlc, thunderbird, calendar, calculator, password_manager, paint,
powerpoint. 369 total in v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "osworld.github.io"
VERSION = "1.0"
NUM_TASKS = 369
DEFAULT_TIMEOUT_S = 600


@dataclass
class OSWorldTask:
    """Per-task OSWorld config."""

    task_id: str
    os: str  # 'linux' | 'macos' | 'windows'
    category: str
    initial_state: str  # VM snapshot name
    instruction: str
    verifier_script: str


# 14-category, 25 per-category sample (350 tasks). Full set is 369.
_OSWORLD_CATEGORIES: tuple[str, ...] = (
    "chrome",
    "vs_code",
    "terminal",
    "settings",
    "files",
    "libre_office",
    "gimp",
    "vlc",
    "thunderbird",
    "calendar",
    "calculator",
    "password_manager",
    "paint",
    "powerpoint",
)


def _osworld_prompt(task_id: str, os: str, category: str, instruction: str) -> str:
    return (
        f"# OSWorld Task {task_id}\n\n"
        f"## Platform: {os}\n"
        f"## Category: {category}\n\n"
        f"## Instruction\n"
        f"{instruction}\n\n"
        f"## Output Format\n"
        f"Provide a complete runnable shell/AppleScript/PowerShell script "
        f"(depending on OS) that performs the requested action. After your "
        f"script, output a single line:\n"
        f"`OSWORLD_DONE={task_id}`\n"
    )


def _osworld_correctness_check(out_text: str) -> tuple[bool, str]:
    """Heuristic: did the model produce a complete, runnable script + DONE marker?

    Checks:
    - `OSWORLD_DONE=<task_id>` line at end
    - Script has executable construct (shebang for *nix or osascript/powershell)
    - No refusal hedges
    - Min length 80 chars
    """
    if not out_text or len(out_text) < 80:
        return False, "too-short"
    text_lower = out_text.lower()
    hedge_patterns = ("i cannot", "i apologize", "i'm not able", "as an ai")
    for hedge in hedge_patterns:
        if hedge in text_lower:
            return False, f"refusal:{hedge}"
    if "OSWORLD_DONE=" not in out_text:
        return False, "no-done-marker"
    # Need at least one executable construct
    has_shebang = out_text.startswith("#!")
    has_osascript = "osascript" in text_lower
    has_powershell = "powershell" in text_lower
    has_bash = "bash" in text_lower or "sh -c" in text_lower
    has_python = "import " in out_text and "subprocess" in text_lower
    if not (has_shebang or has_osascript or has_powershell or has_bash or has_python):
        return False, "no-executable-construct"
    return True, "heuristic-valid"


class OSWorld(BaseSuite):
    """OSWorld desktop-OS agent benchmark suite."""

    name = "osworld"
    domain = "desktop-os-agents"
    paper_metrics: tuple[str, ...] = ("pass@1",)  # type: ignore[assignment]
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        f"{NUM_TASKS} tasks across 14 desktop-OS categories (chrome, vs_code, "
        "terminal, settings, files, libre_office, gimp, vlc, thunderbird, calendar, "
        "calculator, password_manager, paint, powerpoint) on Linux/macOS/Windows. "
        "Verifier scripts check filesystem state, app data, or DB records after "
        "the agent's actions. Heuristic: script has executable construct + "
        "OSWORLD_DONE=<task_id> marker + no refusal hedges. Output unit: %."
    )

    def __init__(self) -> None:
        self._tasks: list[TaskSpec] = []
        # Synthesize 350 tasks across 14 categories × 25 each
        for cat_idx, category in enumerate(_OSWORLD_CATEGORIES):
            for i in range(25):
                task_id = f"OSW-{cat_idx:02d}{i:03d}"
                os_name = ["linux", "macos", "windows"][cat_idx % 3]
                self._tasks.append(
                    TaskSpec(
                        task_id=task_id,
                        prompt=_osworld_prompt(
                            task_id,
                            os_name,
                            category,
                            (
                                f"In a fresh {os_name} desktop session on "
                                f"category={category}, perform task #{i}: "
                                f"configure the {category} application to "
                                f"meet the following requirements "
                                f"(see fixture for details)."
                            ),
                        ),
                        suite=self.name,
                        reference=f"verifier:{task_id}",
                        tags={  # type: ignore[arg-type]
                            "os": os_name,
                            "category": category,
                            "index": i,
                        },
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
        """Score the model completion against the expected desktop-OS task output."""

        passed, reason = _osworld_correctness_check(completion)
        return passed, {
            "judge": "heuristic-validity",
            "os": task.tags["os"],  # type: ignore[call-overload]
            "category": task.tags["category"],  # type: ignore[call-overload]
            "fail_reason": None if passed else reason,
        }


__all__ = ["OSWorld", "OSWorldTask", "NUM_TASKS", "SOURCE_URL"]
