"""Gate: eval modules have >=80% docstring coverage (Phase 3 task 56)."""

from __future__ import annotations

import importlib
import inspect

TARGET_MODULES = [
    "eval.budget",
    "eval.deepswe",
    "eval.long_horizon",
    "eval.nested_rlvr",
    "eval.pillars",
    "eval.tbench",
]

THRESHOLD = 0.80


def _coverage_for_module(mod_name: str) -> tuple[int, int, float, list[str]]:
    mod = importlib.import_module(mod_name)
    members: list[tuple[str, object]] = []
    for name, obj in inspect.getmembers(mod):
        if inspect.isfunction(obj) or inspect.isclass(obj):
            if getattr(obj, "__module__", None) == mod.__name__:
                # Exclude dunder names
                if name.startswith("__") and name.endswith("__"):
                    continue
                members.append((name, obj))
    # Include class methods (excluding dunders)
    extra: list[tuple[str, object]] = []
    for cname, cls in list(members):
        if inspect.isclass(cls):
            for meth_name, meth in inspect.getmembers(
                cls, predicate=inspect.isfunction
            ):
                if meth_name.startswith("__") and meth_name.endswith("__"):
                    continue
                if meth_name.startswith("_") and meth_name != "__init__":
                    # Count private methods as well for stricter gate, but skip dunders
                    # Already filtered above, allow them
                    pass
                if meth.__qualname__.startswith(cname):
                    extra.append((f"{cname}.{meth_name}", meth))
            # Also include class-defined methods that are not functions (e.g., dataclass to_dict)
            for meth_name in dir(cls):
                if meth_name.startswith("__") and meth_name.endswith("__"):
                    continue
                try:
                    meth = getattr(cls, meth_name)
                except AttributeError:
                    continue
                if inspect.isfunction(meth) or inspect.ismethod(meth):
                    qname = getattr(meth, "__qualname__", "")
                    if cname in qname and f"{cname}.{meth_name}" not in [
                        x[0] for x in extra + members
                    ]:
                        extra.append((f"{cname}.{meth_name}", meth))
    members.extend(extra)
    # Filter dunders again and deduplicate
    filtered: list[tuple[str, object]] = []
    seen: set[str] = set()
    for n, o in members:
        short = n.split(".")[-1]
        if short.startswith("__") and short.endswith("__"):
            continue
        if n not in seen:
            seen.add(n)
            filtered.append((n, o))
    total = len(filtered)
    if total == 0:
        return (0, 0, 1.0, [])
    missing = [n for n, o in filtered if not getattr(o, "__doc__", None)]
    covered = total - len(missing)
    ratio = covered / total if total else 1.0
    return (covered, total, ratio, missing)


def test_eval_docstring_coverage() -> None:
    failures: list[str] = []
    for mod_name in TARGET_MODULES:
        covered, total, ratio, missing = _coverage_for_module(mod_name)
        if ratio < THRESHOLD:
            failures.append(
                f"{mod_name}: {covered}/{total} ({ratio:.0%}) missing {missing}"
            )
    assert not failures, "Eval docstring coverage below 80%:\n" + "\n".join(failures)


def test_eval_docstring_args_returns_present() -> None:
    """Spot-check that public functions document Args/Returns."""
    for mod_name in TARGET_MODULES:
        mod = importlib.import_module(mod_name)
        for name, obj in inspect.getmembers(mod, predicate=inspect.isfunction):
            if getattr(obj, "__module__", None) != mod.__name__:
                continue
            if name.startswith("_"):
                continue
            doc = getattr(obj, "__doc__", "") or ""
            sig = inspect.signature(obj)
            if len(sig.parameters) > 0:
                assert "Args:" in doc or "Returns:" in doc, (
                    f"{mod_name}.{name} docstring should contain Args/Returns"
                )
