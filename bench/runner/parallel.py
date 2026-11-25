"""Back-compat re-export — canonical module lives at ``bench.parallel``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.parallel import (  # noqa: F401
    ParallelRunner as ParallelRunner,
)
from bench.parallel import (
    ParallelStats as ParallelStats,
)
from bench.parallel import (
    TaskTimeoutError as TaskTimeoutError,
)
from bench.parallel import (
    default_workers as default_workers,
)
