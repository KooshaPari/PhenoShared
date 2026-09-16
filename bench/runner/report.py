"""Back-compat re-export — canonical module lives at ``bench.report``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.report import (  # noqa: F401
    RunReportAggregator as RunReportAggregator,
)
from bench.report import (
    _fmt_metric as _fmt_metric,
)
from bench.report import (
    render_markdown as render_markdown,
)
from bench.report import (
    write_report as write_report,
)
from bench.report import (
    write_suite_result as write_suite_result,
)
