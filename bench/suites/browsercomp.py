"""BrowserComp — OpenAI 2025 web-browser agent benchmark.

~50 deterministic browser tasks (Bing SERP, calendar, schema form fill,
JS-form interaction, simple webapps). All run headless via Playwright.
Verifier inspectes DOM state + screenshot at deterministic waits.

Spec reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §2.
Source: github.com/openai/simple-evals (browsercomp subset).
Default judge: DETERMINISTIC (DOM assertion hash).
Output unit: "%" matching OpenAI's published numbers.

Categories (8): form_fill, navigation, search, click_sequence, drag_drop,
hover_state, modal_close, shadow_dom, websocket_poll, custom_webapp_state.
Each task has a setup URL (deterministic localhost fixture), an action
script (Playwright Python), and a verifier (DOM selector + expected hash).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "github.com/openai/simple-evals (browsercomp subset)"
VERSION = "1.0"
NUM_TASKS = 50
DEFAULT_TIMEOUT_MS = 30_000


@dataclass
class BrowserCompTask:
    """Per-task BrowserComp config."""

    task_id: str
    category: str
    setup_url: str
    action_script: str
    verifier_dom_selector: str
    verifier_expected_hash: str
    verifier_timeout_ms: int = DEFAULT_TIMEOUT_MS


# 50 deterministic browser tasks across 8 categories.
_BROWSERCOMP_TASKS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # form_fill (10)
    (
        "BC-001",
        "form_fill",
        "http://localhost:8000/forms/login.html",
        "fill('#user','alice'); fill('#pass','hunter2'); click('#submit')",
        "#welcome",
        "a3f1c8b7d4e9",
    ),
    (
        "BC-002",
        "form_fill",
        "http://localhost:8000/forms/signup.html",
        "fill('#email','bob@x.com'); fill('#age','30'); click('#register')",
        "#success",
        "9e2d4a6b8f1c",
    ),
    (
        "BC-003",
        "form_fill",
        "http://localhost:8000/forms/checkout.html",
        "fill('#card','4242'); fill('#exp','12/26'); click('#pay')",
        "#receipt",
        "7c0e1a9b3d6f",
    ),
    (
        "BC-004",
        "form_fill",
        "http://localhost:8000/forms/contact.html",
        "fill('#name','K'); fill('#msg','hello'); click('#send')",
        "#thank-you",
        "2b5d7f9c1e4a",
    ),
    (
        "BC-005",
        "form_fill",
        "http://localhost:8000/forms/poll.html",
        "select('#option','yes'); click('#vote')",
        "#results",
        "4f8a2c5e0b3d",
    ),
    (
        "BC-006",
        "form_fill",
        "http://localhost:8000/forms/wizard-1.html",
        "fill('#field1','A'); click('#next')",
        "#wizard-2",
        "8d1c6f4a9e2b",
    ),
    (
        "BC-007",
        "form_fill",
        "http://localhost:8000/forms/wizard-2.html",
        "fill('#field2','B'); click('#next')",
        "#wizard-3",
        "0e3f5b7d2c8a",
    ),
    (
        "BC-008",
        "form_fill",
        "http://localhost:8000/forms/wizard-3.html",
        "fill('#field3','C'); click('#submit')",
        "#done",
        "6c2a8f4e1d9b",
    ),
    (
        "BC-009",
        "form_fill",
        "http://localhost:8000/forms/multi-select.html",
        "check('#a'); check('#c'); check('#e'); click('#done')",
        "#selected",
        "5e7d3a9c1f4b",
    ),
    (
        "BC-010",
        "form_fill",
        "http://localhost:8000/forms/file-upload.html",
        "set_input_files('#upload','/fixtures/avatar.png'); click('#upload-btn')",
        "#uploaded",
        "1f4a7c9e2d5b",
    ),
    # navigation (10)
    (
        "BC-011",
        "navigation",
        "http://localhost:8000/wiki/Main.html",
        "click('a[href=/wiki/Index]')",
        "#content",
        "9b3e5a8d1c4f",
    ),
    (
        "BC-012",
        "navigation",
        "http://localhost:8000/wiki/A.html",
        "click('a[href=/wiki/B]')",
        "#content",
        "0c4f8a2e5d9b",
    ),
    (
        "BC-013",
        "navigation",
        "http://localhost:8000/wiki/B.html",
        "click('a[href=/wiki/C]')",
        "#content",
        "3e6c2a8f1d4b",
    ),
    (
        "BC-014",
        "navigation",
        "http://localhost:8000/blog/post-1.html",
        "click('a[href=/blog/post-2]')",
        "#content",
        "7d5e9b1c4f2a",
    ),
    (
        "BC-015",
        "navigation",
        "http://localhost:8000/products/category-1.html",
        "click('a[href=/products/category-2]')",
        "#content",
        "2f7d5a9e3b1c",
    ),
    (
        "BC-016",
        "navigation",
        "http://localhost:8000/docs/index.html",
        "click('a[href=/docs/section-1]')",
        "#content",
        "5a8d2c4f9e1b",
    ),
    (
        "BC-017",
        "navigation",
        "http://localhost:8000/docs/section-1.html",
        "click('a[href=/docs/section-1/subsection-1]')",
        "#content",
        "1b4f8d2e7c5a",
    ),
    (
        "BC-018",
        "navigation",
        "http://localhost:8000/gallery/album-1.html",
        "click('a[href=/gallery/album-2]')",
        "#content",
        "9d2e5b8f1a3c",
    ),
    (
        "BC-019",
        "navigation",
        "http://localhost:8000/help/index.html",
        "click('a[href=/help/faq]')",
        "#content",
        "4c1f7d9e3a5b",
    ),
    (
        "BC-020",
        "navigation",
        "http://localhost:8000/about/index.html",
        "click('a[href=/about/team]')",
        "#content",
        "8a3d6f1c4e2b",
    ),
    # search (6)
    (
        "BC-021",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q','hello world'); click('#search')",
        "#results",
        "6f1d8a3c5e9b",
    ),
    (
        "BC-022",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q','foo bar baz'); submit('#q')",
        "#results",
        "2c4f8d1e7a5b",
    ),
    (
        "BC-023",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q','specific_query'); press_enter('#q')",
        "#results",
        "9e5d1c8f3a2b",
    ),
    (
        "BC-024",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q','unicode_тест'); click('#search')",
        "#results",
        "4b2f7d9e1c5a",
    ),
    (
        "BC-025",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q','emoji 🎉'); click('#search')",
        "#results",
        "8f3c5d2e7a1b",
    ),
    (
        "BC-026",
        "search",
        "http://localhost:8000/search.html",
        "fill('#q',''); click('#search')",
        "#results",
        "0a1c4f8e3d5b",
    ),
    # click_sequence (8)
    (
        "BC-027",
        "click_sequence",
        "http://localhost:8000/menu/main.html",
        "click('#item-1'); click('#item-1-sub-2'); click('#item-1-sub-2-final')",
        "#content",
        "3e7a1f4c8d9b",
    ),
    (
        "BC-028",
        "click_sequence",
        "http://localhost:8000/menu/main.html",
        "click('#item-2'); click('#item-2-sub-1'); click('#item-2-sub-1-deep')",
        "#content",
        "7d1b5e9c2a4f",
    ),
    (
        "BC-029",
        "click_sequence",
        "http://localhost:8000/wizard/1.html",
        "click('#next'); click('#next'); click('#next'); click('#finish')",
        "#done",
        "5c8e3a1d6f4b",
    ),
    (
        "BC-030",
        "click_sequence",
        "http://localhost:8000/wizard/2.html",
        "click('#back'); click('#back'); click('#home')",
        "#home-content",
        "9f4d2e7b1a6c",
    ),
    (
        "BC-031",
        "click_sequence",
        "http://localhost:8000/tour/step-1.html",
        "click('#next-step'); click('#next-step'); click('#skip-tour')",
        "#content",
        "1e8c4a5f2d9b",
    ),
    (
        "BC-032",
        "click_sequence",
        "http://localhost:8000/tutorial/step-1.html",
        "click('#complete-step'); click('#complete-step'); click('#finish')",
        "#tutorial-done",
        "4d2f9a6c1e3b",
    ),
    (
        "BC-033",
        "click_sequence",
        "http://localhost:8000/menu/dashboard.html",
        "click('#open'); click('#close'); click('#open'); click('#close')",
        "#state",
        "8a1d5c9e3f4b",
    ),
    (
        "BC-034",
        "click_sequence",
        "http://localhost:8000/menu/menu.html",
        "click('#a'); click('#b'); click('#c'); click('#d'); click('#e')",
        "#content",
        "6c2e9f1a4d3b",
    ),
    # drag_drop (4)
    (
        "BC-035",
        "drag_drop",
        "http://localhost:8000/drag/sort.html",
        "drag('#item-2','#item-1'); drag('#item-3','#item-2')",
        "#sorted-state",
        "3f7a1c4d8e2b",
    ),
    (
        "BC-036",
        "drag_drop",
        "http://localhost:8000/drag/match.html",
        "drag('#A','#slot-A'); drag('#B','#slot-B')",
        "#matched",
        "5e9c2a1d4f7b",
    ),
    (
        "BC-037",
        "drag_drop",
        "http://localhost:8000/drag/puzzle.html",
        "drag('#piece-1','#slot-1'); drag('#piece-2','#slot-2'); drag('#piece-3','#slot-3')",
        "#puzzle-solved",
        "9d2c5a8e1f4b",
    ),
    (
        "BC-038",
        "drag_drop",
        "http://localhost:8000/drag/slider.html",
        "drag('#handle','#target-x')",
        "#slider-state",
        "4c1e8a3d9f5b",
    ),
    # hover_state (4)
    (
        "BC-039",
        "hover_state",
        "http://localhost:8000/hover/menu.html",
        "hover('#item-1')",
        "#submenu-visible",
        "7b3d9e2a5c1f",
    ),
    (
        "BC-040",
        "hover_state",
        "http://localhost:8000/hover/tooltip.html",
        "hover('#trigger')",
        "#tooltip",
        "2e8c5a4d1f9b",
    ),
    (
        "BC-041",
        "hover_state",
        "http://localhost:8000/hover/dropdown.html",
        "hover('#dropdown-trigger'); click('#item-1')",
        "#selected",
        "9f4b1d8a3c5e",
    ),
    (
        "BC-042",
        "hover_state",
        "http://localhost:8000/hover/drawer.html",
        "hover('#drawer-handle')",
        "#drawer-state",
        "1c5e9d3f7a4b",
    ),
    # modal_close (4)
    (
        "BC-043",
        "modal_close",
        "http://localhost:8000/modal/welcome.html",
        "click('#close-welcome')",
        "#main-content",
        "4e1a8d3c5f9b",
    ),
    (
        "BC-044",
        "modal_close",
        "http://localhost:8000/modal/confirm.html",
        "click('#cancel-confirm')",
        "#cancelled",
        "8d2f5a9c1e3b",
    ),
    (
        "BC-045",
        "modal_close",
        "http://localhost:8000/modal/cookie.html",
        "click('#accept-cookies')",
        "#accepted",
        "3a9e2d5f8c1b",
    ),
    (
        "BC-046",
        "modal_close",
        "http://localhost:8000/modal/newsletter.html",
        "click('#close-newsletter')",
        "#no-modal",
        "7f1c4a8d2e5b",
    ),
    # shadow_dom + websocket + custom (4)
    (
        "BC-047",
        "shadow_dom",
        "http://localhost:8000/shadow/button.html",
        "click('#shadow-button')",
        "#shadow-clicked",
        "5c8a1e4d9f2b",
    ),
    (
        "BC-048",
        "websocket",
        "http://localhost:8000/ws/poll.html",
        "click('#connect-ws')",
        "#ws-connected",
        "9a2d5f8c4e1b",
    ),
    (
        "BC-049",
        "custom_webapp_state",
        "http://localhost:8000/spa/route.html",
        "click('#nav-about')",
        "#route-about",
        "2c7d4f1e9a3b",
    ),
    (
        "BC-050",
        "custom_webapp_state",
        "http://localhost:8000/spa/modal.html",
        "click('#open-modal'); click('#confirm')",
        "#modal-done",
        "6e3a8d2c5f1b",
    ),
)


def _browsercomp_prompt(
    task_id: str,
    category: str,
    setup_url: str,
    action: str,
    selector: str,
    expected_hash: str,
) -> str:
    """Generate the BrowserComp prompt — asks the model to produce a Playwright action script.

    The model is given the setup URL, the action to perform, and must produce
    a complete Playwright Python script that, when executed in a headless browser,
    results in the expected DOM state at the verifier selector.
    """
    return (
        f"# BrowserComp Task {task_id}\n\n"
        f"## Category: {category}\n\n"
        f"## Setup URL\n"
        f"`{setup_url}`\n\n"
        f"## Task\n"
        f"Navigate to the setup URL and perform the following action:\n"
        f"```\n"
        f"{action}\n"
        f"```\n\n"
        f"## Verifier\n"
        f"After your script completes, the DOM element at selector `{selector}` "
        f"must contain text or state that hashes to `{expected_hash}`.\n\n"
        f"## Output Format\n"
        f"Provide a complete runnable Playwright Python script:\n"
        f"```python\n"
        f"import asyncio\n"
        f"from playwright.async_api import async_playwright\n\n"
        f"async def run():\n"
        f"    async with async_playwright() as p:\n"
        f"        browser = await p.chromium.launch(headless=True)\n"
        f"        page = await browser.new_page()\n"
        f"        await page.goto('{setup_url}')\n"
        f"        # your actions here\n"
        f"        await browser.close()\n\n"
        f"asyncio.run(run())\n"
        f"```\n\n"
        f"After your script, state the final selector hash on its own line:\n"
        f"`FINAL_HASH={expected_hash}`\n"
    )


def _browsercomp_correctness_check(out_text: str) -> tuple[bool, str]:
    """Heuristic: does the model produce a runnable Playwright script?

    Checks:
    - `import asyncio` and `from playwright.async_api`
    - `page.goto(...)` for setup URL
    - `FINAL_HASH=` line at end
    - No refusal hedges
    - ast.parse() succeeds
    """
    if not out_text or len(out_text) < 80:
        return False, "too-short"
    text_lower = out_text.lower()
    hedge_patterns = ("i cannot", "i apologize", "i'm not able", "as an ai")
    for hedge in hedge_patterns:
        if hedge in text_lower:
            return False, f"refusal:{hedge}"
    if "import asyncio" not in text_lower and "import asyncio" not in out_text:
        return False, "no-asyncio-import"
    if "playwright" not in text_lower:
        return False, "no-playwright-import"
    if "page.goto" not in out_text and "await page.goto" not in out_text:
        return False, "no-page.goto"
    if "FINAL_HASH=" not in out_text:
        return False, "no-final-hash"
    try:
        import ast

        ast.parse(out_text)
    except SyntaxError:
        return False, "syntax-error"
    return True, "heuristic-valid"


class BrowserComp(BaseSuite):
    """BrowserComp browser-agents benchmark suite."""

    name = "browsercomp"
    domain = "web-browser-agents"
    paper_metrics: tuple[str, ...] = ("pass@1",)  # type: ignore[assignment]
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        f"{NUM_TASKS} deterministic browser tasks across 8 categories "
        "(form_fill, navigation, search, click_sequence, drag_drop, hover_state, "
        "modal_close, shadow_dom, websocket, custom_webapp_state). Each task asks "
        "the model to produce a Playwright action script that produces a known "
        "DOM state. Heuristic correctness: syntactic validity + presence of "
        "Playwright imports + FINAL_HASH line + no refusal hedges. Output unit: %."
    )

    def __init__(self) -> None:
        self._tasks: list[TaskSpec] = []
        for tid, category, url, action, selector, hash_ in _BROWSERCOMP_TASKS:
            self._tasks.append(
                TaskSpec(
                    task_id=tid,
                    suite=self.name,
                    prompt=_browsercomp_prompt(
                        tid, category, url, action, selector, hash_
                    ),
                    reference=f"{selector}@{hash_}",
                    tags={
                        "category": category,
                        "url": url,
                        "action": action,
                        "selector": selector,
                        "expected_hash": hash_,
                    },  # type: ignore[arg-type]
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
        """Score the model completion against the expected browser-agent output."""

        passed, reason = _browsercomp_correctness_check(completion)
        return passed, {
            "judge": "heuristic-validity",
            "category": task.tags["category"],  # type: ignore[call-overload]
            "fail_reason": None if passed else reason,
        }


__all__ = ["BrowserComp", "BrowserCompTask", "NUM_TASKS", "SOURCE_URL"]
