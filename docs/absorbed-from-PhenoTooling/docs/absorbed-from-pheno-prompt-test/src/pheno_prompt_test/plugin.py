"""pheno-prompt-test core: assertions + case discovery.

Implements §77.3 of `FLEET_100TASK_DAG_V4.md`.

Public API:
- LLMResponse: frozen dataclass
- PromptCase: a test case (name, prompt, expected, etc.)
- assert_in_text, assert_matches_pattern, assert_json_valid
- compute_similarity (Jaccard token overlap)
- find_prompt_cases, register_case
- run_case (run a case against an LLM backend callable)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

# --- Public dataclasses ------------------------------------------------------

@dataclass(frozen=True)
class LLMResponse:
    """A frozen wrapper around an LLM completion result.

    Attributes:
        text: The model's text output.
        model: The model id (e.g. "gpt-5.5", "claude-sonnet-4-6").
        tokens_in: Input token count (optional).
        tokens_out: Output token count (optional).
        cost_usd: Cost in USD (optional, populated if backend reports it).
    """
    text: str
    model: str = "unknown"
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None


@dataclass
class PromptCase:
    """A regression-test case for a single LLM prompt.

    Attributes:
        name: Identifier (e.g. "greet_new_user").
        prompt: The prompt text.
        expected: The expected output (string match or substring).
        min_similarity: Jaccard threshold (0.0-1.0). Default 0.8.
        must_contain: Substrings that MUST appear in output.
        must_match: Regexes that MUST match the output.
        must_be_json: If True, output must parse as JSON.
        tags: Free-form labels for filtering (e.g. ["smoke", "slow"]).
    """
    name: str
    prompt: str
    expected: str = ""
    min_similarity: float = 0.8
    must_contain: List[str] = field(default_factory=list)
    must_match: List[str] = field(default_factory=list)
    must_be_json: bool = False
    tags: List[str] = field(default_factory=list)


# --- Assertions --------------------------------------------------------------

def assert_in_text(text: str, must_contain: Sequence[str]) -> None:
    """Assert each substring in `must_contain` is in `text`.

    Raises AssertionError on first miss with a clear message.
    """
    for needle in must_contain:
        if needle not in text:
            raise AssertionError(
                f"expected substring not found: {needle!r}\n"
                f"actual (first 200 chars): {text[:200]!r}"
            )


def assert_matches_pattern(text: str, pattern: str) -> None:
    """Assert `re.search(pattern, text)` matches."""
    if not re.search(pattern, text):
        raise AssertionError(
            f"pattern did not match: {pattern!r}\n"
            f"actual (first 200 chars): {text[:200]!r}"
        )


def assert_json_valid(text: str) -> None:
    """Assert `text` parses as JSON."""
    try:
        json.loads(text)
    except (ValueError, TypeError) as e:
        raise AssertionError(f"output is not valid JSON: {e}\ntext: {text[:200]!r}")


def compute_similarity(a: str, b: str) -> float:
    """Jaccard token overlap (0.0 to 1.0).

    Case-insensitive, splits on non-alphanumerics.
    """
    tok = lambda s: set(re.findall(r"\w+", s.lower()))
    sa, sb = tok(a), tok(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# --- Discovery & registration -----------------------------------------------

def find_prompt_cases(directory: Path) -> List[PromptCase]:
    """Find all `.prompt` files in `directory` and return as PromptCase stubs.

    A .prompt file uses a simple mini-YAML format:
        name: <id>
        prompt: |
          <text>
        expected: |
          <text>
        min_similarity: 0.8
        must_contain: ["a", "b"]
        must_match: ["^pattern$"]
        must_be_json: false
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    cases: List[PromptCase] = []
    for prompt_file in sorted(directory.glob("*.prompt")):
        text = prompt_file.read_text()
        name = _extract_kv(text, "name") or prompt_file.stem
        prompt = _extract_kv_block(text, "prompt") or text
        expected = _extract_kv_block(text, "expected") or ""
        try:
            min_sim = float(_extract_kv(text, "min_similarity") or 0.8)
        except ValueError:
            min_sim = 0.8
        case = PromptCase(
            name=name,
            prompt=prompt.strip(),
            expected=expected.strip(),
            min_similarity=min_sim,
        )
        cases.append(case)
    return cases


def register_case(case: PromptCase) -> None:
    """Register a PromptCase into the in-memory registry.

    Test files can use this to build a suite programmatically.
    """
    if not hasattr(register_case, "_registry"):
        register_case._registry = []  # type: ignore[attr-defined]
    register_case._registry.append(case)  # type: ignore[attr-defined]


def registered_cases() -> List[PromptCase]:
    """Return all currently-registered cases."""
    return list(getattr(register_case, "_registry", []))


# --- End-to-end runner -------------------------------------------------------

def run_case(
    case: PromptCase,
    backend: Callable[[str], LLMResponse],
) -> LLMResponse:
    """Run `case` against `backend` and validate the response.

    `backend` takes a prompt string and returns an LLMResponse.
    Applies the case's assertions in order; raises AssertionError on fail.
    """
    response = backend(case.prompt)
    if case.must_contain:
        assert_in_text(response.text, case.must_contain)
    if case.must_match:
        for pat in case.must_match:
            assert_matches_pattern(response.text, pat)
    if case.must_be_json:
        assert_json_valid(response.text)
    if case.expected:
        sim = compute_similarity(response.text, case.expected)
        if sim < case.min_similarity:
            raise AssertionError(
                f"similarity {sim:.2f} < min {case.min_similarity} "
                f"for case {case.name!r}\n"
                f"actual: {response.text[:200]!r}\n"
                f"expected: {case.expected[:200]!r}"
            )
    return response


# --- Mini-parser (no PyYAML dep) --------------------------------------------

def _extract_kv(text: str, key: str) -> Optional[str]:
    """Extract a single-line `key: value` field from text."""
    for line in text.splitlines():
        m = re.match(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None


def _extract_kv_block(text: str, key: str) -> Optional[str]:
    """Extract a multi-line `key: |` block scalar from text."""
    lines = text.splitlines()
    out: List[str] = []
    in_block = False
    for line in lines:
        if not in_block:
            if re.match(rf"^\s*{re.escape(key)}\s*:\s*\|\s*$", line):
                in_block = True
        else:
            if line.startswith(" ") or line.startswith("\t") or line.strip() == "":
                out.append(line)
            else:
                break
    return "\n".join(out) if out else None
