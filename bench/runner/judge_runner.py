"""Back-compat re-export — canonical module lives at ``bench.judge_runner``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.judge_runner import (
    _SCORE_RE as _SCORE_RE,
)
from bench.judge_runner import (
    _VERDICT_RE as _VERDICT_RE,
)
from bench.judge_runner import (  # noqa: F401
    DEFAULT_BATCH_SIZE as DEFAULT_BATCH_SIZE,
)
from bench.judge_runner import (
    DEFAULT_JUDGE_MODEL as DEFAULT_JUDGE_MODEL,
)
from bench.judge_runner import (
    JUDGE_SYSTEM as JUDGE_SYSTEM,
)
from bench.judge_runner import (
    JudgeBatch as JudgeBatch,
)
from bench.judge_runner import (
    JudgeRunResult as JudgeRunResult,
)
from bench.judge_runner import (
    JudgeVerdict as JudgeVerdict,
)
from bench.judge_runner import (
    _normalize_verdict as _normalize_verdict,
)
from bench.judge_runner import (
    _parse_verdicts as _parse_verdicts,
)
from bench.judge_runner import (
    _render_batch_prompt as _render_batch_prompt,
)
from bench.judge_runner import (
    attach_verdicts as attach_verdicts,
)
from bench.judge_runner import (
    build_batches as build_batches,
)
from bench.judge_runner import (
    evaluate_batch as evaluate_batch,
)
from bench.judge_runner import (
    run_judge as run_judge,
)
