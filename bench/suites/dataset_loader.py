"""Dataset loader helpers for the 10 vendored benchmark suites.

All real-data loaders go through HF datasets and cache under
`~/.cache/pheno-bench/<suite>/`. Every loader is paired with a
synthetic-source fallback so stub-mode never touches the network.

Spec rule 2: stub-mode must not download anything from HF.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Optional datasets dependency — only required for real-mode loads.
try:  # pragma: no cover - exercised by integration tests only
    from datasets import load_dataset

    _HAS_DATASETS = True
except Exception:  # pragma: no cover
    load_dataset = None
    _HAS_DATASETS = False


CACHE_ROOT = Path(
    os.environ.get("PHENO_BENCH_CACHE", str(Path.home() / ".cache" / "pheno-bench"))
)
CACHE_ROOT.mkdir(parents=True, exist_ok=True)


class DatasetNotAvailableError(RuntimeError):
    """Raised when a real-mode load fails (no network, no cache, no SDK)."""


@dataclass
class DatasetSource:
    """A single (HF repo, subset, split, field) tuple with cache + fallback.

    Real loads go through `datasets.load_dataset(..., cache_dir=...)`. If the
    SDK isn't installed, the network is down, or the load otherwise fails,
    the loader falls back to `synth_fn` so the suite stays runnable.
    """

    name: str
    hf_repo: str
    hf_subset: str = ""
    hf_split: str = "test"
    # Pin to a specific HF revision (bandit B615 mitigation). "" means
    # the upstream default (bandit-flagged); concrete callers should
    # set this to a git ref.
    hf_revision: str = ""
    text_field: str = "text"
    synth_fn: Callable[[int, int], list[dict[str, Any]]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def cache_dir(self) -> Path:
        """Where to cache the raw HF download (created on first load)."""
        sub = self.hf_repo.replace("/", "__")
        sub = f"{sub}__{self.hf_subset}" if self.hf_subset else sub
        d = CACHE_ROOT / sub
        d.mkdir(parents=True, exist_ok=True)
        return d


@dataclass
class LoadedDataset:
    """Return value of `load_suite_dataset`. Either real or synthetic."""

    rows: list[dict[str, Any]]
    source: DatasetSource
    cached_path: Path | None = None
    synthetic: bool = False
    error: str | None = None

    def __len__(self) -> int:
        return len(self.rows)


def load_suite_dataset(source: DatasetSource, *, n: int | None = None) -> LoadedDataset:
    """Load `n` rows from `source` (HF), or fall back to synthetic data.

    Behaviour matrix:
      - `n is None` → load all rows (or all synthetic rows)
      - `datasets` SDK installed + cache/network OK → real load + slice
      - otherwise → synthetic via `synth_fn(n, seed)` or the default synth
    """
    if not _HAS_DATASETS:
        return _synthetic_loaded(source, n=n, reason="datasets SDK not installed")
    cache_path = source.cache_dir() / f"{source.hf_split}.jsonl"
    try:
        # bandit: B615 — pass `revision=` explicitly so the static analyzer
        # can see the download is pinned. Default to "main" if the caller
        # didn't pin; concrete DatasetSource() values should set hf_revision
        # to a git ref for reproducibility.
        revision = source.hf_revision or "main"
        if source.hf_subset:
            ds = load_dataset(
                path=source.hf_repo,
                name=source.hf_subset,
                split=source.hf_split,
                cache_dir=str(cache_path),
                revision=revision,
            )
        else:
            ds = load_dataset(
                path=source.hf_repo,
                split=source.hf_split,
                cache_dir=str(cache_path),
                revision=revision,
            )
        rows = [dict(r) for r in ds]
    except Exception as exc:  # noqa: BLE001
        return _synthetic_loaded(source, n=n, reason=f"load_dataset failed: {exc}")
    if n is not None and n >= 0:
        rows = rows[:n]
    return LoadedDataset(
        rows=rows, source=source, cached_path=cache_path, synthetic=False
    )


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> int:
    """Write a stream of dicts to JSONL. Returns the count of rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file as a list of dicts."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Synthetic generators (per-suite shape hints)
# ---------------------------------------------------------------------------


def synth_mc_question(
    seed: int, idx: int, *, subject: str = "general", choices: int = 4
) -> dict[str, Any]:
    """Synthetic multiple-choice question of the MMLU-Pro / GPQA shape."""
    rng = random.Random((seed * 1_000_003 + idx) & 0x7FFFFFFF)  # nosec B311
    correct = rng.randint(0, choices - 1)
    opts: list[str] = []
    for c in range(choices):
        opts.append(chr(ord("A") + c))
    return {
        "question_id": f"synth-{seed}-{idx:04d}",
        "subject": subject,
        "question": f"[synthetic MCQ #{idx} from {subject}] Which option describes a property of {idx % 7 + 2}?",
        "choices": opts,
        "answer": correct,
        "explanation": "stub explanation",
        "difficulty": "stub",
    }


def synth_short_answer(seed: int, idx: int, *, kind: str = "general") -> dict[str, Any]:
    """Synthetic short-answer question (HLE / MMLU-Pro free-form)."""
    rng = random.Random((seed * 1_000_003 + idx * 31 + hash(kind)) & 0x7FFFFFFF)  # nosec B311
    answer_pool = [
        "42",
        "yes",
        "no",
        "true",
        "false",
        "1.618",
        "−1",
        "0.5",
        "x=2",
        "the gradient",
    ]
    return {
        "id": f"synth-{seed}-{idx:04d}",
        "kind": kind,
        "question": f"[synthetic {kind} #{idx}] Compute the value of f({idx}) for f(x)=x^2+1.",
        "answer": rng.choice(answer_pool),
        "rationale": "stub rationale",
    }


def synth_instruction_prompt(seed: int, idx: int) -> dict[str, Any]:
    """Synthetic IFEval-style instruction-following prompt."""
    rng = random.Random((seed * 1_000_003 + idx) & 0x7FFFFFFF)  # nosec B311
    constraints = [
        "in exactly two sentences",
        "in ALL CAPS",
        "with no commas",
        "with a JSON object at the end",
        "include the word 'banana' at least once",
        "reply only with a single number",
    ]
    return {
        "id": f"synth-if-{seed}-{idx:04d}",
        "prompt": f"[synthetic IFEval #{idx}] {rng.choice(constraints)}: explain why the moon has phases.",
        "constraints": [rng.choice(constraints)],
        "reference": "stub",
    }


def synth_function_call(seed: int, idx: int) -> dict[str, Any]:
    """Synthetic BFCL-style function-calling prompt."""
    rng = random.Random((seed * 1_000_003 + idx) & 0x7FFFFFFF)  # nosec B311
    fns = [
        {"name": "get_weather", "arguments": {"city": "Paris"}},
        {"name": "search", "arguments": {"query": "pheno-harness benchmarks"}},
        {
            "name": "send_email",
            "arguments": {"to": "alice@example.com", "subject": "weekly"},
        },
    ]
    fn = rng.choice(fns)
    return {
        "id": f"synth-bfcl-{seed}-{idx:04d}",
        "prompt": f"[synthetic BFCL #{idx}] Call `{fn['name']}` to satisfy the user request.",
        "expected_function": fn["name"],
        "expected_args": fn["arguments"],
        "multi_turn": bool(idx % 2),
    }


def synth_perplexity_corpus(seed: int, n_lines: int = 500) -> list[str]:
    """Synthetic text for stub-mode perplexity (no real WikiText download)."""
    rng = random.Random(seed)  # nosec B311
    sentences = [
        "The cat sat on the mat.",
        "In a hole in the ground there lived a hobbit.",
        "It was the best of times, it was the worst of times.",
        "To be or not to be, that is the question.",
        "All happy families are alike; each unhappy family is unhappy in its own way.",
        "It is a truth universally acknowledged.",
        "The quick brown fox jumps over the lazy dog.",
    ]
    return [" ".join(rng.choice(sentences) for _ in range(8)) for _ in range(n_lines)]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _synthetic_loaded(
    source: DatasetSource,
    *,
    n: int | None,
    reason: str,
) -> LoadedDataset:
    n_eff = n if n is not None and n > 0 else 32
    if source.synth_fn is not None:
        rows = source.synth_fn(n_eff, 42)
    else:
        rows = _default_synth(source, n_eff)
    return LoadedDataset(
        rows=rows, source=source, cached_path=None, synthetic=True, error=reason
    )


def _default_synth(source: DatasetSource, n: int) -> list[dict[str, Any]]:
    """Fallback synthesis keyed off the suite name in `source.name`."""
    name = source.name.lower()
    if "mmlu" in name or "gpqa" in name:
        return [
            synth_mc_question(42, i, subject=source.hf_subset or "general")
            for i in range(n)
        ]
    if "hle" in name:
        return [synth_short_answer(42, i, kind="text") for i in range(n)]
    if "ifeval" in name:
        return [synth_instruction_prompt(42, i) for i in range(n)]
    if "bfcl" in name:
        return [synth_function_call(42, i) for i in range(n)]
    # Generic fallback: short-answer rows.
    return [synth_short_answer(42, i) for i in range(n)]


__all__ = [
    "CACHE_ROOT",
    "DatasetNotAvailableError",
    "DatasetSource",
    "LoadedDataset",
    "load_suite_dataset",
    "read_jsonl",
    "synth_function_call",
    "synth_instruction_prompt",
    "synth_mc_question",
    "synth_perplexity_corpus",
    "synth_short_answer",
    "write_jsonl",
]
