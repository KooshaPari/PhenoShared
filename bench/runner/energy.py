"""Back-compat re-export — canonical module lives at ``bench.energy``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.energy import (
    _PM_HEADER as _PM_HEADER,
)
from bench.energy import (
    _PM_KV as _PM_KV,
)
from bench.energy import (  # noqa: F401
    EnergyReading as EnergyReading,
)
from bench.energy import (
    EnergyTotal as EnergyTotal,
)
from bench.energy import (
    _EnergySource as _EnergySource,
)
from bench.energy import (
    _NoOpSource as _NoOpSource,
)
from bench.energy import (
    _NvidiaSmiSource as _NvidiaSmiSource,
)
from bench.energy import (
    _parse_powermetrics_line as _parse_powermetrics_line,
)
from bench.energy import (
    _PowermetricsSource as _PowermetricsSource,
)
from bench.energy import (
    detect_source as detect_source,
)
from bench.energy import (
    make_source as make_source,
)
