"""Quickstart: pheno-prompt-test

Demonstrates a one-shot LLM prompt regression test with an inline backend.
"""

from __future__ import annotations

import pheno_prompt_test as ppt


def make_backend(response_text: str):
    """Return a callable LLM backend that always emits ``response_text``."""

    def backend(prompt: str):
        return ppt.LLMResponse(text=response_text, prompt=prompt,
                               metadata={"backend": "stub"})

    return backend


def main() -> None:
    case = ppt.PromptCase(
        name="greets",
        prompt="say hi",
        assertions=[ppt.assert_in_text],
    )
    backend = make_backend("hi there!")
    result = ppt.run_case(case, backend)
    print(f"case={case.name} passed={result.passed} text={result.response.text!r}")
    assert result.passed


if __name__ == "__main__":
    main()