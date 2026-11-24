"""Concurrent multi-agent execution: LatentMAS, TiDAR, SSD, JetSpec.

Each agent is an adapter that wraps a third-party model and exposes a uniform
`async def step(prompt, state)` interface, so the same scheduler can fan out,
chain, or fall back between them.
"""

from .jetspec_runner import JetSpecRunner, jetspec_draft_tree
from .latentmas_runner import LatentMasRunner, latentmas_fanout
from .scheduler import ConcurrentScheduler, Strategy
from .ssd_runner import SsdRunner
from .tidar_runner import TidarRunner, tidar_ar_diffusion_loop

__all__ = [
    "ConcurrentScheduler",
    "JetSpecRunner",
    "LatentMasRunner",
    "SsdRunner",
    "Strategy",
    "TidarRunner",
    "jetspec_draft_tree",
    "latentmas_fanout",
    "tidar_ar_diffusion_loop",
]
