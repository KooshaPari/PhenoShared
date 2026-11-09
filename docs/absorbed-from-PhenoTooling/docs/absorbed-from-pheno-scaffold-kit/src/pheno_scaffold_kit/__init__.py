"""Unified API for Phenotype scaffold libraries."""

from __future__ import annotations

import importlib
import sys as _sys
from pathlib import Path
from typing import Any

# Sub-libraries are imported lazily to keep import-time cost low.
# Each entry is (module_name, public_attr) where public_attr is the symbol
# re-exported as `pheno_scaffold_kit.<key>`.
_SUB_LIBRARY_SOURCES: dict[str, tuple[str, str]] = {
    # Original 4 (V6 era).
    "llms_txt": ("pheno_llms_txt", "pheno_llms_txt"),
    "prompt_test": ("pheno_prompt_test", "pheno_prompt_test"),
    "vibecoding_guard": ("pheno_vibecoding_guard", "pheno_vibecoding_guard"),
    "worklog_schema": ("pheno_worklog_schema", "pheno_worklog_schema"),
    # L72/L73/L74 absorbed 2026-06-19 from KooshaPari/pheno-{predict,framework-lint,drift-detector}.
    "predict": ("pheno_scaffold_kit._predict", "pheno_scaffold_kit._predict"),
    "framework_lint": ("pheno_scaffold_kit._framework_lint", "pheno_scaffold_kit._framework_lint"),
    "drift_detector": ("pheno_scaffold_kit._drift_detector", "pheno_scaffold_kit._drift_detector"),
}

# We pre-declare None placeholders so `hasattr(pheno_scaffold_kit, "predict")` works
# and so mypy sees the names. Real values resolve via __getattr__ (PEP 562).
for _key in _SUB_LIBRARY_SOURCES:
    globals()[_key] = None  # type: ignore[assignment]
del _key

_loaded: dict[str, Any] | None = None


def _get_loaded() -> dict[str, Any]:
    global _loaded
    if _loaded is None:
        out: dict[str, Any] = {}
        for key, (module_name, attr) in _SUB_LIBRARY_SOURCES.items():
            try:
                mod = importlib.import_module(module_name)
                out[key] = getattr(mod, attr, mod)
            except ImportError:  # pragma: no cover - optional dep
                out[key] = None
        _loaded = out
    return _loaded


def __getattr__(name: str) -> Any:  # PEP 562
    if name == "SUB_LIBRARIES":
        return dict(_get_loaded())
    if name in _SUB_LIBRARY_SOURCES:
        return _get_loaded().get(name)
    raise AttributeError(f"module 'pheno_scaffold_kit' has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Sub-library wrappers
# ---------------------------------------------------------------------------


def _call_first(module: Any, names: tuple[str, ...], repo_dir: Path, **kwargs: Any) -> Any:
    """Call the first supported initializer exposed by a scaffold sub-library.

    Per V6 PR-2: each sub-step is wrapped in a try/except so a single failure
    produces a JSON error result and the rest of the scaffold still runs.
    """
    if module is None:
        return {"ok": False, "error": "sub-library not installed"}

    for name in names:
        target = getattr(module, name, None)
        if callable(target):
            return target(repo_dir, **kwargs)

    return {
        "ok": False,
        "error": f"{module.__name__} does not expose any supported entrypoint: {', '.join(names)}",
    }


def detect_repo_type(repo_dir: str | Path) -> dict[str, bool]:
    """Detect basic repository traits used by ergonomic scaffold defaults.

    Examples
    --------
    >>> detect_repo_type("/nonexistent/path-that-does-not-exist-abc123")["exists"]
    False
    >>> sorted(detect_repo_type("/nonexistent/path-that-does-not-exist-abc123").keys())
    ['exists', 'git', 'go', 'node', 'python', 'rust']
    """
    root = Path(repo_dir).resolve()
    return {
        "exists": root.exists(),
        "git": (root / ".git").exists(),
        "python": (root / "pyproject.toml").exists(),
        "node": (root / "package.json").exists(),
        "rust": (root / "Cargo.toml").exists(),
        "go": (root / "go.mod").exists(),
    }


def init_llms(repo_dir: str | Path, **kwargs: Any) -> Any:
    return _call_first(llms_txt, ("init_llms", "init", "scaffold"), Path(repo_dir), **kwargs)


def init_prompt_test(repo_dir: str | Path, **kwargs: Any) -> Any:
    return _call_first(prompt_test, ("init_prompt_test", "init", "scaffold"), Path(repo_dir), **kwargs)


def install_hooks(repo_dir: str | Path, **kwargs: Any) -> Any:
    return _call_first(
        vibecoding_guard,
        ("install_hooks", "init_vibecoding_guard", "init", "scaffold"),
        Path(repo_dir),
        **kwargs,
    )


def init_worklog(repo_dir: str | Path, **kwargs: Any) -> Any:
    return _call_first(worklog_schema, ("init_worklog", "init", "scaffold"), Path(repo_dir), **kwargs)


def init_scaffold(repo_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Run all scaffold steps for a repository and return structured results.

    V6 PR-2: per-step try/except so one sub-step failing does not abort the run.
    """
    root = Path(repo_dir).resolve()
    context = {"repo_type": detect_repo_type(root), **kwargs}
    results: dict[str, Any] = {
        "repo_dir": str(root),
        "repo_type": context["repo_type"],
    }
    for step_name, step_fn in (
        ("llms", init_llms),
        ("prompt_test", init_prompt_test),
        ("hooks", install_hooks),
        ("worklog", init_worklog),
    ):
        try:
            results[step_name] = step_fn(root, **context)
        except Exception as exc:  # noqa: BLE001 — propagate as JSON for caller
            results[step_name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return results


__all__ = [
    "SUB_LIBRARIES",
    "llms_txt",
    "prompt_test",
    "vibecoding_guard",
    "worklog_schema",
    "predict",
    "framework_lint",
    "drift_detector",
    "detect_repo_type",
    "init_llms",
    "init_prompt_test",
    "install_hooks",
    "init_worklog",
    "init_scaffold",
]

# Re-export module reference for tooling.
_module = _sys.modules[__name__]
