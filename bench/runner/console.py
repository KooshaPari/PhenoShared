"""Back-compat re-export — canonical module lives at ``bench.console``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.console import (  # noqa: F401
    Console as Console,
)
from bench.console import (
    ProgressBar as ProgressBar,
)
from bench.console import (
    _PlainStatusContext as _PlainStatusContext,
)
from bench.console import (
    _RichStatusContext as _RichStatusContext,
)
from bench.console import (
    _StatusContext as _StatusContext,
)
