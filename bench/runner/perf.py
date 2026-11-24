"""Back-compat re-export — canonical module lives at ``bench.perf``.

Explicit re-exports (rather than dynamic ``importlib`` updates) so static
type checkers can see the symbols without following dynamic-globals tricks.
"""

from __future__ import annotations

from bench.perf import (
    _RUSAGE_KEY as _RUSAGE_KEY,
)
from bench.perf import (  # noqa: F401
    PerfReading as PerfReading,
)
from bench.perf import (
    PerfSnapshot as PerfSnapshot,
)
from bench.perf import (
    TimedSection as TimedSection,
)
from bench.perf import (
    _read_max_rss as _read_max_rss,
)
from bench.perf import (
    aggregate as aggregate,
)
from bench.perf import (
    macos_metal_mem_mb as macos_metal_mem_mb,
)
from bench.perf import (
    measure_task as measure_task,
)
from bench.perf import (
    nvidia_smi_mem_mb as nvidia_smi_mem_mb,
)
from bench.perf import (
    peak_gpu_mem_mb as peak_gpu_mem_mb,
)
from bench.perf import (
    peak_rss_mb as peak_rss_mb,
)
