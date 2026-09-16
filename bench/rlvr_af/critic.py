"""L3 — Critic agent: diagnoses suite failures from traces.

The critic reads a `Trail` (collection of transitions), identifies
failures, attempts to reproduce them, and writes a `CriticReport`
with actionable diagnosis. The report feeds L4 (Optimizer) which
applies the patch.

From the RLVR-AF spec:
  "Critic: given a failed Trail, examines the transition sequence,
   identifies the root cause, classifies it (hallucination / tool
   mis-use / context lost / instruction-following / internal error),
   and writes an RFC-style annotation."
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
from dataclasses import dataclass, field
from typing import Any

from bench.rlvr_af.trace import Trail

# ---------------------------------------------------------------------------
# Critic report
# ---------------------------------------------------------------------------

FAILURE_CLASSES = {
    "hallucination": "model generated factually incorrect content",
    "tool_misuse": "model used a tool incorrectly or called wrong tool",
    "context_loss": "model lost long-horizon context mid-trail",
    "instruction_following": "model did not follow the instruction precisely",
    "internal_error": "harness or suite code crashed with an exception",
    "timeout": "trail exceeded the time limit",
    "empty_completion": "model returned empty or error-prefixed content",
    "unknown": "could not classify automatically",
}


@dataclass
class CriticReport:
    """Critic analysis of a single trail (motion + drift observations)."""

    trail_id: str
    suite_name: str
    failure_class: str = "unknown"
    confidence: float = 0.0
    root_cause: str = ""
    reproduction_script: str = ""
    fix_suggestion: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base critic
# ---------------------------------------------------------------------------


class BaseCritic:
    """Base critic. Subclass to implement custom critics."""

    def __call__(self, trail: Trail) -> CriticReport:
        """Make the critic callable; delegates to ``analyze()``."""
        return self.analyze(trail)

    def analyze(self, trail: Trail) -> CriticReport:
        """Analyze a trail and return a critic report (subclasses implement)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Heuristic critic (classifies by analysing transition metadata)
# ---------------------------------------------------------------------------


class HeuristicCritic(BaseCritic):
    """Rule-based critic that inspects failed transitions."""

    def analyze(self, trail: Trail) -> CriticReport:
        """Classify the failure by inspecting transition completions + metadata."""
        failure_class = "unknown"
        root_cause_lines = []
        fix_lines = []
        total = len(trail.transitions)
        failed = [t for t in trail.transitions if t.verdict and not t.verdict.passed]
        passed = [t for t in trail.transitions if t.verdict and t.verdict.passed]

        # Heuristic classification
        for t in failed:
            comp = (t.artifact.completion or "").strip()
            if not comp:
                failure_class = "empty_completion"
                root_cause_lines.append(
                    f"Transition {t.index}: empty completion (task={t.artifact.task_id})"
                )
                fix_lines.append(
                    "Check that the model adapter is returning text for the given prompt"
                )
            elif comp.startswith("[error]") or comp.startswith("error:"):
                failure_class = "internal_error"
                root_cause_lines.append(
                    f"Transition {t.index}: error in adapter: {comp[:100]}"
                )
                fix_lines.append("Check model adapter instantiation or weight path")
            elif "timeout" in (str(t.artifact.meta.get("trail_stderr", "")).lower()):
                failure_class = "timeout"
                root_cause_lines.append(f"Transition {t.index}: trail timed out")
                fix_lines.append("Increase timeout or optimize generation speed")
            elif "tool" in comp.lower() or "command" in comp.lower():
                failure_class = "tool_misuse"
                root_cause_lines.append(
                    f"Transition {t.index}: tool misuse suspected in '{comp[:80]}'"
                )
                fix_lines.append("Check tool-call syntax in adapter prompt")
            elif len(comp) > 200:
                failure_class = "hallucination"
                root_cause_lines.append(
                    f"Transition {t.index}: long completion may indicate hallucination ({len(comp)} chars)"
                )
                fix_lines.append("Add grounding instructions to system prompt")
            else:
                failure_class = "instruction_following"
                root_cause_lines.append(
                    f"Transition {t.index}: instruction-following failure (completion='{comp[:60]}')"
                )
                fix_lines.append(
                    "Verify prompt template includes explicit format instructions"
                )

        if not root_cause_lines:
            root_cause_lines.append(
                "No root cause identified — all transitions passed or empty trail"
            )

        return CriticReport(
            trail_id=trail.run_id,
            suite_name=trail.suite,
            failure_class=failure_class,
            confidence=0.8 if failed else 1.0,
            root_cause="\n".join(root_cause_lines),
            fix_suggestion="\n".join(fix_lines),
            meta={
                "total_transitions": total,
                "failed": len(failed),
                "passed": len(passed),
                "pass_rate": len(passed) / max(total, 1),
            },
        )


# ---------------------------------------------------------------------------
# LLM critic (uses forge -p or codex to analyse trails)
# ---------------------------------------------------------------------------


class ForgeCritic(BaseCritic):
    """Critic that sends trail summaries to forge -p and parses diagnosis."""

    FORGE_BIN = "/Users/<REDACTED>/.local/bin/forge"

    def analyze(self, trail: Trail) -> CriticReport:
        """Send the trail summary to ``forge -p`` and merge with heuristic fallback."""
        summary = self._summarise(trail)
        prompt = (
            f"You are a critic agent for the RLVR-AF optimisation framework.\n\n"
            f"Analyse the following benchmark trail and produce:\n"
            f"1. A failure class from: {', '.join(FAILURE_CLASSES.keys())}\n"
            f"2. Root cause (1-2 sentences)\n"
            f"3. A fix suggestion (1-2 sentences)\n\n"
            f"Trail:\n{summary}"
        )
        try:
            proc = subprocess.run(  # nosec B603
                [self.FORGE_BIN, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=60,
                env={
                    **os.environ,
                    "PATH": "/usr/bin:/bin:/usr/local/bin:/Users/<REDACTED>/.local/bin",
                },
            )
            reply = proc.stdout or ""
        except Exception as e:
            reply = f"forge error: {e}"

        # Heuristic fallback if forge fails
        heuristic = HeuristicCritic()
        base = heuristic.analyze(trail)

        return CriticReport(
            trail_id=trail.trail_id,
            suite_name=trail.suite_name,
            failure_class=base.failure_class,
            confidence=0.7,
            root_cause=reply[:500] if reply else base.root_cause,
            fix_suggestion=base.fix_suggestion,
            meta={"forge_reply_length": len(reply), **base.meta},
        )

    def _summarise(self, trail: Trail) -> str:
        """Build a short text summary of the trail (first 5 transitions)."""
        lines = [
            f"Trail: {trail.trail_id}  Suite: {trail.suite_name}  Model: {trail.model}"
        ]
        lines.append(f"Total transitions: {len(trail.transitions)}")
        for t in trail.transitions[:5]:  # first 5 only for brevity
            v = t.verdict
            if v:
                comp = (t.artifact.completion or "")[:80]
                lines.append(
                    f"  [{t.index}] task={t.artifact.task_id} "
                    f"passed={v.passed} reward={v.reward:.2f} "
                    f"reason={v.reason} completion='{comp}'"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Critic factory
# ---------------------------------------------------------------------------

_CRITICS: dict[str, type[BaseCritic]] = {}


def register_critic(key: str, cls: type[BaseCritic]) -> None:
    """Register a critic class under a string key (used by tests + suites)."""
    _CRITICS[key] = cls


def get_critic(key: str = "heuristic") -> BaseCritic:
    """Look up a critic by key; falls back to ``HeuristicCritic``."""
    cls = _CRITICS.get(key, HeuristicCritic)
    return cls()


register_critic("heuristic", HeuristicCritic)
register_critic("forge", ForgeCritic)


__all__ = [
    "FAILURE_CLASSES",
    "CriticReport",
    "BaseCritic",
    "HeuristicCritic",
    "ForgeCritic",
    "register_critic",
    "get_critic",
]
