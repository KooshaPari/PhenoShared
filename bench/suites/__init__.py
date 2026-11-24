"""pheno-harness vendored benchmark suites.

This package contains the 10 Suite subclasses specified in
`docs/superpowers/specs/2026-07-16-benchmark-harness.md` §2:

1. DeepSWE            (deepswe.py)            — agentica-project/DeepSWE
2. TerminalBench      (terminal_bench.py)     — laude-institute/terminal-bench
3. SWEBenchVerified   (swe_bench_verified.py) — swebench.com + SWE-agent
4. IFEval             (ifeval.py)             — google-research IFE
5. MTBench            (mt_bench.py)           — lm-sys/FastChat
6. MMLUPro            (mmlu_pro.py)           — TIGER-Lab/MMLU-Pro
7. GPQADiamond        (gpqa_diamond.py)       — idavidrein/gpqa
8. HLE                (hle.py)                — lastexam.ai
9. BFCLv4             (bfcl_v4.py)            — gorilla.cs.berkeley.edu/bfcl
10. Perplexity        (perplexity.py)         — wikitext + slimpajama backend

All suites subclass `BaseSuite` (from `bench.suites._stub`) which itself
subclasses the skeleton's `bench.registry.Suite` — so importing this
package triggers automatic registration into `bench.registry._SUITES`.
Every suite supports stub-mode (`--self-test`) and degrades gracefully when
Docker / HF cache / `ANTHROPIC_API_KEY` are missing.

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md.
"""

from __future__ import annotations

# Import order matters: helpers first so suites can rely on them.
from ._stub import (  # noqa: F401  (re-exported)
    BaseSuite,
    TaskSpec,
    aggregate_paper_metrics,
    synthetic_prompt,
    synthetic_response,
)

# Suite subclasses (each auto-registers via Suite.__init_subclass__).
from .bfcl_v4 import BFCLv4
from .container_runner import (  # noqa: F401
    ContainerBackend,
    ContainerNotAvailableError,
    ContainerRunError,
    ContainerRunner,
    ContainerRunResult,
    RewardContract,
    detect_backend,
    run_or_stub,
)
from .dataset_loader import (  # noqa: F401
    CACHE_ROOT,
    DatasetNotAvailableError,
    DatasetSource,
    LoadedDataset,
    load_suite_dataset,
    read_jsonl,
    write_jsonl,
)
from .deepswe import DeepSWE
from .gpqa_diamond import GPQADiamond
from .hle import HLE
from .ifeval import IFEval
from .judge import (  # noqa: F401
    DEFAULT_JUDGE_MODEL,
    JudgeError,
    JudgeRequest,
    JudgeVerdict,
    LLMJudge,
)
from .mmlu_pro import MMLUPro
from .mt_bench import MTBench
from .perplexity import Perplexity
from .swe_bench_verified import SWEBenchVerified
from .terminal_bench import TerminalBench

# Canonical alias table — `cli.py` `--suite` names use these strings.
SUITE_ALIASES: dict[str, str] = {
    "deep-swe": "DeepSWE",
    "terminal-bench": "TerminalBench",
    "swe-bench-verified": "SWEBenchVerified",
    "ifeval": "IFEval",
    "mt-bench": "MTBench",
    "mmlu-pro": "MMLUPro",
    "gpqa-diamond": "GPQADiamond",
    "hle": "HLE",
    "bfcl": "BFCLv4",
    "perplexity": "Perplexity",
    # Mock/CLI-test alias — points at the registered name of IFEval
    # (``IFEval.name == "ifeval"``, lowercase — set via Suite.__init_subclass__
    # line 49 of bench/registry.py). Used by tests/test_benchmark_envelope.py
    # and any "smoke only" dry-run path that needs a valid registered suite
    # name without firing real eval pipelines.
    "mock-fixture": "ifeval",
}


def list_suite_classes() -> list[type[BaseSuite]]:
    """Return the 10 Suite subclasses in canonical (spec §2) order."""
    return [
        DeepSWE,
        TerminalBench,
        SWEBenchVerified,
        IFEval,
        MTBench,
        MMLUPro,
        GPQADiamond,
        HLE,
        BFCLv4,
        Perplexity,
    ]


def suite_class_by_name(name: str) -> type[BaseSuite]:
    """Look up a Suite subclass by either its class name or its alias.

    Examples:
        suite_class_by_name("DeepSWE") -> DeepSWE
        suite_class_by_name("deep-swe") -> DeepSWE
    """
    # Direct class-name match first.
    for cls in list_suite_classes():
        if cls.__name__ == name:
            return cls
    # Then alias match.
    canonical = SUITE_ALIASES.get(name)
    if canonical is None:
        raise KeyError(f"unknown suite: {name!r}; known: {sorted(SUITE_ALIASES)}")
    for cls in list_suite_classes():
        if cls.__name__ == canonical:
            return cls
    raise KeyError(f"alias {name!r} resolves to {canonical!r} but no such class found")


__all__ = [
    # Helpers
    "BaseSuite",
    "TaskSpec",
    "aggregate_paper_metrics",
    "synthetic_prompt",
    "synthetic_response",
    "ContainerBackend",
    "ContainerNotAvailableError",
    "ContainerRunError",
    "ContainerRunResult",
    "ContainerRunner",
    "RewardContract",
    "detect_backend",
    "run_or_stub",
    "CACHE_ROOT",
    "DatasetNotAvailableError",
    "DatasetSource",
    "LoadedDataset",
    "load_suite_dataset",
    "read_jsonl",
    "write_jsonl",
    "DEFAULT_JUDGE_MODEL",
    "JudgeError",
    "JudgeRequest",
    "JudgeVerdict",
    "LLMJudge",
    # Suite subclasses
    "BFCLv4",
    "DeepSWE",
    "GPQADiamond",
    "HLE",
    "IFEval",
    "MMLUPro",
    "MTBench",
    "Perplexity",
    "SWEBenchVerified",
    "TerminalBench",
    # Lookup helpers
    "SUITE_ALIASES",
    "list_suite_classes",
    "suite_class_by_name",
]
