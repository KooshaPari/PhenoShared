"""Report aggregation: combines N SuiteResults into a RunReport + markdown table.

Spec rule §5: when multiple `(suite, model)` rows are run, produces a
markdown table with all Q4 metrics as columns; row = suite; column = metric.
The JSON side keeps the full per-task resolution for downstream tooling.

Key APIs:

* `RunReportAggregator` — collects SuiteResults during a run.
* `render_markdown(report, *, suite_metric_set)` — emit the spec's §5
  matrix-latest.md table.
* `write_report(report, output_dir)` — write `report.json` + `report.md`.
* `render_json(report)` — round-trippable JSON.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bench import __version__ as RUNNER_VERSION
from bench.metric import SPEC_Q4_METRICS
from bench.types import RunReport, SuiteResult

# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


@dataclass
class RunReportAggregator:
    """Build a `RunReport` from a sequence of `SuiteResult` objects.

    Tracks a clock so the produced `generated_at` is accurate even when the
    caller adds results in a streaming fashion.
    """

    run_id: str
    judge_mode: Any = None  # `bench.types.JudgeMode` enum (avoid cycle on import)
    energy_source: Any = None  # `bench.types.EnergySource` enum
    _results: list[SuiteResult] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    def add(self, result: SuiteResult) -> None:
        """Append one SuiteResult to the running aggregate."""
        self._results.append(result)

    def set_extra(self, key: str, value: Any) -> None:
        """Add arbitrary metadata (e.g., `runner_version`, `host:cpu_count`)."""
        self._extra[key] = value

    def add_many(self, results: Iterable[SuiteResult]) -> None:
        for r in results:
            self.add(r)

    def to_run_report(self) -> RunReport:
        """Materialize the aggregator contents into a `RunReport` dataclass."""
        from bench.types import EnergySource, JudgeMode

        return RunReport(
            version=RUNNER_VERSION,
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            run_id=self.run_id,
            judge_mode=self.judge_mode or JudgeMode.DETERMINISTIC,
            energy_source=self.energy_source or EnergySource.NONE,
            results=list(self._results),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the run, including `_extra`."""
        rep = self.to_run_report()
        d = rep.to_dict()
        if self._extra:
            d["runner_metadata"] = dict(self._extra)
        return d


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(
    report: RunReport,
    *,
    title: str = "Pheno-Harness Benchmark Report",
    suite_metric_set: Iterable[str] = SPEC_Q4_METRICS,
) -> str:
    """Render a markdown table: row = (suite, model), columns = metrics.

    The matrix is "long × wide" so users can compare the same `(suite, model)`
    cell across runs and different `(suite, model)` cells against each other.
    """
    metrics = list(suite_metric_set)
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- run_id: `{report.run_id}`")
    lines.append(f"- generated_at: `{report.generated_at}`")
    lines.append(f"- judge_mode: `{report.judge_mode.value}`")
    lines.append(f"- energy_source: `{report.energy_source.value}`")
    lines.append(f"- suite_count: {len(report.results)}")
    lines.append("")
    # Header
    header = ["suite", "model"] + metrics
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    # Body — one row per SuiteResult
    for res in report.results:
        row = [res.suite, res.model]
        for m in metrics:
            val = res.metrics.get(m)
            if val is None:
                row.append("—")
            else:
                row.append(_fmt_metric(val))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    # Footer with version + total task count.
    total_tasks = sum(len(r.tasks) for r in report.results)
    lines.append(f"_version: `{report.version}` — total tasks: {total_tasks}_")
    return "\n".join(lines) + "\n"


def _fmt_metric(value: Any) -> str:
    """Format a single metric value for the markdown table."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 1000 or (0 < abs(value) < 0.01):
            return f"{value:.3e}"
        return f"{value:.4g}"
    return str(value)


# ---------------------------------------------------------------------------
# IO: write_report
# ---------------------------------------------------------------------------


def write_report(
    report: RunReport,
    output_dir: str | Path,
    *,
    aggregator: RunReportAggregator | None = None,
    filename_base: str = "report",
) -> dict[str, str]:
    """Write both `report.json` and `report.md` to `output_dir`.

    Returns a `{"json": "...", "md": "..."}` mapping of written paths for
    callers that want to print/log them.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_payload = aggregator.to_dict() if aggregator is not None else report.to_dict()
    md_payload = render_markdown(report)
    json_path = out / f"{filename_base}.json"
    md_path = out / f"{filename_base}.md"
    json_path.write_text(
        json.dumps(json_payload, sort_keys=True, indent=2), encoding="utf-8"
    )
    md_path.write_text(md_payload, encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


# ---------------------------------------------------------------------------
# Single-suite convenience
# ---------------------------------------------------------------------------


def write_suite_result(
    result: SuiteResult,
    output_dir: str | Path,
    *,
    filename_base: str = "suite",
) -> dict[str, str]:
    """Write a single SuiteResult (`<base>.json` + `<base>.md`)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_payload = result.to_dict()
    json_path = out / f"{filename_base}.json"
    md_path = out / f"{filename_base}.md"
    json_path.write_text(
        json.dumps(json_payload, sort_keys=True, indent=2), encoding="utf-8"
    )
    md_lines = [
        f"# Suite `{result.suite}` / `{result.model}`",
        "",
        f"- run_id: `{result.run_id}`",
        f"- started_at: `{result.started_at}`",
        f"- stopped_at: `{result.stopped_at}`",
        f"- n_tasks: {len(result.tasks)}",
        "",
        "| task_id | status | duration_s | prompt_tokens | completion_tokens | reward | message |",
        "|---|---|---|---|---|---|---|",
    ]
    for tr in result.tasks:
        md_lines.append(
            f"| {tr.task_id} | {tr.status.value.upper()} | {tr.duration_s:.3f} | "
            f"{tr.prompt_tokens} | {tr.completion_tokens} | "
            f"{tr.reward if tr.reward is not None else '—'} | "
            f"{tr.message.replace('|', '¦')[:80]} |"
        )
    md_lines.append("")
    if result.metrics:
        md_lines.append("## Metrics")
        for k, v in sorted(result.metrics.items()):
            md_lines.append(f"- `{k}`: `{_fmt_metric(v)}`")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


__all__ = [
    "RunReportAggregator",
    "render_markdown",
    "write_report",
    "write_suite_result",
]


def render_json(results: Any) -> str:
    """Serialize a list of `SuiteResult` (or a single one) to JSON.

    The shape mirrors `qwen-comparison/qwen_stock_mlx_vs_pheno_metal.json`
    (top-level keys + `results: [...]`).
    """
    import dataclasses
    import json

    if results is None:
        return "null"
    if not isinstance(results, list):
        results = [results]

    def _as_dict(r: Any) -> Any:
        if dataclasses.is_dataclass(r):
            # `is_dataclass` accepts both instances and subclasses; narrow to
            # an instance here so `asdict` (which only takes instances) types
            # cleanly.
            if not isinstance(r, type):
                d = dataclasses.asdict(r)
                for k, v in list(d.items()):
                    if dataclasses.is_dataclass(v):
                        d[k] = _as_dict(v)
                    elif isinstance(v, list):
                        d[k] = [
                            _as_dict(x) if dataclasses.is_dataclass(x) else x for x in v
                        ]
                return d
        if isinstance(r, list):
            return [_as_dict(x) for x in r]
        return r

    return json.dumps([_as_dict(r) for r in results], default=str, indent=2)


def render_csv(results: Any) -> str:
    import csv
    import dataclasses
    import io

    if results is None:
        return ""
    if not isinstance(results, list):
        results = [results]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "suite",
            "model",
            "n",
            "passed",
            "wrong",
            "errored",
            "pass_at_1",
            "wall_clock_s",
            "tokens_in",
            "tokens_out",
        ]
    )
    for r in results:
        if dataclasses.is_dataclass(r):
            d = dataclasses.asdict(r)  # type: ignore[arg-type]
            w.writerow(
                [
                    d.get("suite"),
                    d.get("model"),
                    d.get("n"),
                    d.get("passed"),
                    d.get("wrong"),
                    d.get("errored"),
                    d.get("pass_at_1"),
                    d.get("wall_clock_s"),
                    d.get("tokens_in"),
                    d.get("tokens_out"),
                ]
            )
        else:
            w.writerow([str(r)])
    return out.getvalue()


def to_dataframe(results: Any) -> str:
    import dataclasses
    import json

    if not isinstance(results, list):
        results = [results]
    return json.dumps(
        [
            (dataclasses.asdict(r) if dataclasses.is_dataclass(r) else r)  # type: ignore[arg-type]
            for r in results
        ],
        default=str,
    )
