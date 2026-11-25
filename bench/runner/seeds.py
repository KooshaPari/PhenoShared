"""Back-compat re-export — canonical module lives at ``bench.seeds``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.seeds import (  # noqa: F401
    Subset as Subset,
)
from bench.seeds import (
    _suite_fingerprint as _suite_fingerprint,
)
from bench.seeds import (
    make_rng as make_rng,
)
from bench.seeds import (
    sample as sample,
)
from bench.seeds import (
    shuffled_pool as shuffled_pool,
)
