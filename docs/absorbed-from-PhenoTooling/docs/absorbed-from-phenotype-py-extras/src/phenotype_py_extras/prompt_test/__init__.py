# Migrated from KooshaPari/pheno-prompt-test on 2026-06-20 (L5-114)
# Source repo deleted; code preserved in phenotype-py-extras.
"""pheno-prompt-test: pytest-friendly assertions and harness for LLM prompt regression tests.

Implements §77.3 of `FLEET_100TASK_DAG_V4.md`.

Public API:
- LLMResponse: frozen dataclass wrapping an LLM completion
- PromptCase: a (.prompt) test case with name, prompt, expected output, and assertions
- assert_in_text, assert_matches_pattern, assert_json_valid: pass/fail assertions
- compute_similarity: Jaccard token overlap for fuzzy match
- find_prompt_cases, register_case, registered_cases: discovery & registration helpers
- run_case: end-to-end runner that takes a callable LLM backend
- init_prompt_test: scaffold-kit entrypoint (V6 PR-4) that materializes a starter
  tests/prompts/ skeleton.
"""

from pathlib import Path
from typing import Any, Union

from phenotype_py_extras.prompt_test.plugin import (
    LLMResponse,
    PromptCase,
    assert_in_text,
    assert_matches_pattern,
    assert_json_valid,
    compute_similarity,
    find_prompt_cases,
    register_case,
    registered_cases,
    run_case,
)


def init_prompt_test(repo_dir: Union[str, Path], **kwargs: Any) -> dict[str, Any]:
    """Scaffold-kit entrypoint (V6 PR-4): bootstrap a prompts/ test layout."""
    root = Path(repo_dir).expanduser().resolve()
    if not root.exists():
        return {"ok": False, "error": f"Repository directory does not exist: {root}"}

    prompts_dir = root / "tests" / "prompts"
    created: list[str] = []
    try:
        prompts_dir.mkdir(parents=True, exist_ok=True)
        created.append(str(prompts_dir))

        readme = prompts_dir / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Prompt regression tests\n\n"
                "Drop `*.prompt` files in this directory. Each file is a YAML document.\n",
                encoding="utf-8",
            )
            created.append(str(readme))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "repo_dir": str(root),
        "prompts_dir": str(prompts_dir),
        "created": created,
    }


__version__ = "0.1.0"

__all__ = [
    "LLMResponse",
    "PromptCase",
    "assert_in_text",
    "assert_matches_pattern",
    "assert_json_valid",
    "compute_similarity",
    "find_prompt_cases",
    "register_case",
    "registered_cases",
    "run_case",
    "init_prompt_test",
]
