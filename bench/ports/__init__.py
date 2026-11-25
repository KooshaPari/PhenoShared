"""Ports — abstract interfaces for the hexagonal architecture layer.

Ports define *what* the domain needs; adapters provide *how*.

Subpackages:
    inference  — InferencePort (model generation)
    energy     — EnergyPort (power measurement)
    judge      — JudgePort (LLM-as-judge evaluation)
"""

from bench.ports.energy import EnergyPort
from bench.ports.inference import InferencePort
from bench.ports.judge import JudgePort

__all__ = ["InferencePort", "EnergyPort", "JudgePort"]
