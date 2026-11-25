"""Needle context compiler — router, ranker, budget (v0)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from pheno.paths import CONFIG_DIR, TRAINING_DIR


@dataclass
class Slice:
    path: str
    score: float
    reason: str = ""


@dataclass
class CompiledContext:
    role: str
    slices: list[Slice] = field(default_factory=list)
    token_estimate: int = 0
    original_estimate: int = 0

    @property
    def reduction_ratio(self) -> float:
        if self.original_estimate <= 0:
            return 0.0
        return 1.0 - (self.token_estimate / self.original_estimate)


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _load_caps() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load((CONFIG_DIR / "context_caps.yaml").read_text(encoding="utf-8")),
    )


class NeedleRouter:
    """Route request to role from headers, model name, and heuristics."""

    ROLE_PATTERNS = [
        (re.compile(r"\b(route|routing|classify)\b", re.I), "route"),
        (re.compile(r"\b(retriev|search|grep|find file)\b", re.I), "retrieve"),
        (re.compile(r"\b(rank|score|select context)\b", re.I), "rank"),
        (re.compile(r"\b(plan|architect|design)\b", re.I), "plan"),
        (re.compile(r"\b(debug|fix|error|traceback)\b", re.I), "debug"),
        (re.compile(r"\b(patch|edit|implement|refactor)\b", re.I), "patch"),
    ]

    def __init__(self, patterns_path: Path | None = None):
        self.patterns_path = patterns_path or TRAINING_DIR / "router_patterns.json"
        self._learned: dict[str, Any] = {"role_counts": {}, "default_role": "patch"}
        if self.patterns_path.exists():
            raw = json.loads(self.patterns_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "role_counts" in raw:
                self._learned = raw
            elif isinstance(raw, dict):
                self._learned = {"role_counts": raw, "default_role": "patch"}

    def _default_role(self) -> str:
        counts_obj = self._learned.get("role_counts")
        counts = counts_obj if isinstance(counts_obj, dict) else {}
        if not counts:
            return str(self._learned.get("default_role", "patch"))
        items = cast(list[tuple[str, int]], list(counts.items()))
        return max(items, key=lambda kv: kv[1])[0]

    def train_from_call_logs(self, jsonl_glob: str = "call_logs_*.jsonl") -> dict[str, Any]:
        """Build frequency patterns from exported call_logs."""
        counts: dict[str, int] = {}
        for path in sorted(TRAINING_DIR.glob(jsonl_glob)):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                summary = (rec.get("request_summary") or rec.get("model") or "")[:500]
                role = self.route(summary, rec.get("model", ""))
                counts[role] = counts.get(role, 0) + 1
        default_role = (
            max(counts.items(), key=lambda kv: kv[1])[0] if counts else "patch"
        )
        self._learned = {"role_counts": counts, "default_role": default_role}
        self.patterns_path.parent.mkdir(parents=True, exist_ok=True)
        self.patterns_path.write_text(
            json.dumps(self._learned, indent=2), encoding="utf-8"
        )
        return self._learned

    def route(self, prompt: str, model: str = "", header_role: str = "") -> str:
        if header_role:
            return header_role.lower()
        ml = model.lower()
        if "opus" in ml or "5.5" in ml:
            return "emergency"
        if "codex" in ml or "spark" in ml:
            return "patch"
        if "mini" in ml:
            return "debug"
        if "4b" in ml or "qwen" in ml:
            return "patch"
        for pat, role in self.ROLE_PATTERNS:
            if pat.search(prompt[:4000]):
                return role
        return self._default_role()


class NeedleRanker:
    """Rank repo/file slices by keyword overlap (v0 — replace with trained ranker)."""

    def __init__(self, top_k: int = 12):
        self.top_k = top_k

    def rank(self, query: str, candidates: list[dict[str, Any]]) -> list[Slice]:
        q_tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", query.lower()))
        scored: list[Slice] = []
        for c in candidates:
            path = c.get("path", "")
            content = c.get("content", "")[:8000]
            ct = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", content.lower()))
            overlap = len(q_tokens & ct)
            path_bonus = sum(1 for t in q_tokens if t in path.lower())
            score = overlap + 2 * path_bonus
            if score > 0:
                scored.append(
                    Slice(path=path, score=float(score), reason=f"overlap={overlap}")
                )
        scored.sort(key=lambda s: s.score, reverse=True)
        if not scored:
            for c in candidates[: self.top_k]:
                path = c.get("path", "")
                if path:
                    scored.append(
                        Slice(path=path, score=0.0, reason="fallback_no_overlap")
                    )
        return scored[: self.top_k]


class NeedleBudget:
    """Trim ranked slices to role token budget (87k → ~5k compiled target)."""

    def __init__(self) -> None:
        self.caps = _load_caps()

    def cap_for_role(self, role: str) -> int:
        roles = self.caps.get("roles", {})
        r = roles.get(role, roles.get("patch", {}))
        return int(r.get("max_context", 32768))

    def apply(
        self, role: str, slices: list[Slice], contents: dict[str, str]
    ) -> CompiledContext:
        role_cap = self.cap_for_role(role)
        compile_cap = int(self.caps.get("compiled_target_tokens", 5120))
        budget = min(role_cap, compile_cap)
        used = 0
        kept: list[Slice] = []
        original = sum(_est_tokens(contents.get(s.path, "")) for s in slices)
        for s in slices:
            text = contents.get(s.path, "")
            t = _est_tokens(text)
            if used + t > budget:
                remain = budget - used
                if remain > 256:
                    kept.append(Slice(path=s.path, score=s.score, reason="truncated"))
                    used += remain
                break
            kept.append(s)
            used += t
        return CompiledContext(
            role=role,
            slices=kept,
            token_estimate=used,
            original_estimate=original or used,
        )


class ContextCompiler:
    def __init__(self) -> None:
        self.router = NeedleRouter()
        self.ranker = NeedleRanker()
        self.budget = NeedleBudget()

    def compile(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        contents: dict[str, str],
        model: str = "",
        header_role: str = "",
    ) -> CompiledContext:
        role = self.router.route(query, model, header_role)
        ranked = self.ranker.rank(query, candidates)
        return self.budget.apply(role, ranked, contents)

    def render(self, compiled: CompiledContext, contents: dict[str, str]) -> str:
        parts = [
            f"# Compiled context (role={compiled.role}, ~{compiled.token_estimate} tok)\n"
        ]
        for s in compiled.slices:
            parts.append(
                f"\n## {s.path}\n```\n{contents.get(s.path, '')[:12000]}\n```\n"
            )
        return "".join(parts)
