"""Back-compat re-export — canonical module lives at ``bench.cache``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.cache import (  # noqa: F401
    CacheEntry as CacheEntry,
)
from bench.cache import (
    ResponseCache as ResponseCache,
)
from bench.cache import (
    default_cache_path as default_cache_path,
)
from bench.cache import (
    make_cache_key as make_cache_key,
)
from bench.cache import (
    open_cache as open_cache,
)
