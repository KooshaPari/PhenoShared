"""Unit checks for scripts/escape_redacted_for_vitepress.py.

The script turns the literal token ``<REDACTED>`` into ``&lt;REDACTED&gt;`` in
Markdown prose so that VitePress' Vue template compiler does not read it as
an unclosed HTML element. These tests pin down what must be rewritten and
what must be left alone.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts/escape_redacted_for_vitepress.py"

_spec = importlib.util.spec_from_file_location("escape_redacted_for_vitepress", SCRIPT)
assert _spec and _spec.loader
esc = importlib.util.module_from_spec(_spec)
sys.modules["escape_redacted_for_vitepress"] = esc
_spec.loader.exec_module(esc)

T = "<REDACTED>"
E = "&lt;REDACTED&gt;"


def _run(source: str, mask_fn) -> tuple[str, int]:
    return esc.escape_unprotected(source, mask_fn(source))


@pytest.mark.parametrize(
    ("name", "source", "expected", "count"),
    [
        ("prose", f"Use {T} here.", f"Use {E} here.", 1),
        ("heading", f"# {T}", f"# {E}", 1),
        ("blockquote", f"> {T}", f"> {E}", 1),
        ("table_cell", f"| a | {T} |", f"| a | {E} |", 1),
        ("list_item", f"- {T}", f"- {E}", 1),
        ("link_text", f"[{T}](https://example.com)", f"[{E}](https://example.com)", 1),
        ("inline_code", f"Use `{T}` here.", f"Use `{T}` here.", 0),
        ("double_backtick", f"Use ``{T}`` here.", f"Use ``{T}`` here.", 0),
        ("fenced_code", f"```bash\ngh repo list {T}\n```", f"```bash\ngh repo list {T}\n```", 0),
        ("tilde_fence", f"~~~\n{T}\n~~~", f"~~~\n{T}\n~~~", 0),
        ("link_destination", f"[repo](https://github.com/{T}/x)", f"[repo](https://github.com/{T}/x)", 0),
        ("reference_definition", f"[lbl]: https://x/{T}\n", f"[lbl]: https://x/{T}\n", 0),
        ("interpolation", f"{{{{ fmt('{T}') }}}}", f"{{{{ fmt('{T}') }}}}", 0),
        ("already_escaped", f"Use {E} here.", f"Use {E} here.", 0),
        ("html_attribute", f'<a href="https://x/{T}">l</a>', f'<a href="https://x/{T}">l</a>', 0),
        ("html_comment", f"<!-- {T} -->", f"<!-- {T} -->", 0),
        ("script_block", f"<script>\nconst a = '{T}';\n</script>", f"<script>\nconst a = '{T}';\n</script>", 0),
        ("mixed", f"a `{T}` b {T} c", f"a `{T}` b {E} c", 1),
    ],
)
def test_markdown_contexts(name: str, source: str, expected: str, count: int) -> None:
    out, changed = _run(source, esc.markdown_mask)
    assert out == expected, name
    assert changed == count, name


@pytest.mark.parametrize(
    ("name", "source", "expected", "count"),
    [
        (
            "template_text",
            f"<template>\n  <div>\n    {T}\n  </div>\n</template>",
            f"<template>\n  <div>\n    {E}\n  </div>\n</template>",
            1,
        ),
        ("script_string", f"<script setup>\nconst a = '{T}'\n</script>", f"<script setup>\nconst a = '{T}'\n</script>", 0),
        (
            "template_attribute",
            f'<template>\n  <a href="https://x/{T}">l</a>\n</template>',
            f'<template>\n  <a href="https://x/{T}">l</a>\n</template>',
            0,
        ),
        (
            "template_interpolation",
            f"<template>\n  <p>{{{{ '{T}' }}}}</p>\n</template>",
            f"<template>\n  <p>{{{{ '{T}' }}}}</p>\n</template>",
            0,
        ),
    ],
)
def test_vue_sfc_contexts(name: str, source: str, expected: str, count: int) -> None:
    out, changed = _run(source, esc.vue_mask)
    assert out == expected, name
    assert changed == count, name


def test_escape_is_idempotent() -> None:
    source = f"Use {T} in prose, `{T}` in code, and {T} again."
    once, first = _run(source, esc.markdown_mask)
    twice, second = _run(once, esc.markdown_mask)
    assert first == 2
    assert second == 0
    assert once == twice


def test_table_rows_do_not_swallow_prose() -> None:
    """A stray backtick in one table row must not mask a later row.

    markdown-it parses inline content per block, so a code span never spans
    table rows. A whole-file scan used to pair the stray backtick with a
    backtick many rows later and silently skip the real occurrence.
    """
    source = "\n".join(
        [
            "| path | note |",
            "| ---- | ---- |",
            f"| a | unmatched ` backtick |",
            f"| b | {T} |",
        ]
    )
    out, changed = _run(source, esc.markdown_mask)
    assert changed == 1
    assert f"| b | {E} |" in out
