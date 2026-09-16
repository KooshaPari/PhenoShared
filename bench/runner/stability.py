"""Back-compat re-export — canonical module lives at ``bench.stability``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.stability import (  # noqa: F401
    DEFAULT_FALLBACK_DIM as DEFAULT_FALLBACK_DIM,
)
from bench.stability import (
    Turn as Turn,
)
from bench.stability import (
    _hash_embed as _hash_embed,
)
from bench.stability import (
    _user_intents as _user_intents,
)
from bench.stability import (
    analyze_conversation as analyze_conversation,
)
from bench.stability import (
    dead_end_count as dead_end_count,
)
from bench.stability import (
    embed_texts as embed_texts,
)
from bench.stability import (
    intent_drift as intent_drift,
)
from bench.stability import (
    semantic_drift_score as semantic_drift_score,
)
