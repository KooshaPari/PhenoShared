"""Unit tests for the bench harness skeleton layer (8+ tests required)."""

from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest

from bench import __version__
from bench.cli import build_parser
from bench.cli import main as cli_main
from bench.metric import (
    SPEC_Q4_METRICS,
    Metric,
    MetricSet,
    cosine_similarity,
    percentile,
    semantic_drift,
    wilson_ci,
)
from bench.registry import (
    Suite,
    Task,
    get_metric,
    get_suite,
    get_suite_spec,
    get_task,
    list_suites,
    reset_metric_registry,
    reset_registry,
    reset_task_registry,
)
from bench.registry import (
    metric as metric_decorator,
)
from bench.registry import (
    task as task_decorator,
)
from bench.trajectory import (
    RecordFormat,
    RunRecord,
    Step,
    StepRole,
    read_atif_document,
    read_ctrf_document,
    read_jsonl,
    write_jsonl,
)
from bench.types import (
    EnergySource,
    JudgeMode,
    RunReport,
    RunSpec,
    SuiteResult,
    TaskResult,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Fixtures: scoped registry resets so tests are hermetic
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_all_registries():
    """Wipe registries before every test to keep cases hermetic."""
    reset_registry()
    reset_task_registry()
    reset_metric_registry()
    yield
    reset_registry()
    reset_task_registry()
    reset_metric_registry()


# ---------------------------------------------------------------------------
# 1. CLI flag parsing
# ---------------------------------------------------------------------------


def test_cli_flag_parsing_run_subcommand():
    """`bench run --suite ifeval --n 5 --seed 42` parses a complete RunSpec."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--suite",
            "ifeval",
            "--n",
            "5",
            "--seed",
            "42",
            "--model",
            "Qwen3.5-0.8B",
            "--judge-model",
            "claude-sonnet-5",
            "--judge-mode",
            "deterministic",
            "--energy-source",
            "nvidia_smi",
            "--output",
            "/tmp/run.json",  # nosec B108 - test fixture; sandboxed
            "--run-id",
            "test-run-001",
        ]
    )
    assert args.command == "run"
    assert args.suite == "ifeval"
    assert args.n == 5
    assert args.seed == 42
    assert args.judge_mode == "deterministic"
    assert args.energy_source == "nvidia_smi"
    assert args.run_id == "test-run-001"


def test_cli_help_runs():
    """`bench --help` runs cleanly and exits 0 under --exit-on-error semantics."""
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0


def test_cli_self_test_command_round_trip(tmp_path, capsys):
    """`bench self-test` exits 0 and round-trips a synthetic SuiteResult through JSON + disk."""
    out = tmp_path / "self.json"
    rc = cli_main(
        [
            "self-test",
            "--suite",
            "ifeval",
            "--model",
            "Qwen3.5-0.8B",
            "--self-test-output",
            str(out),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "[bench self-test] PASS" in captured.out
    assert out.exists()
    body = out.read_text(encoding="utf-8").strip()
    # Round-trip
    parsed = SuiteResult.from_json(body)
    assert parsed.suite == "ifeval"
    assert parsed.model == "Qwen3.5-0.8B"
    assert len(parsed.tasks) == 3
    # And the on-disk payload is JSON-compatible
    obj = json.loads(body)
    assert obj["suite"] == "ifeval"


def test_cli_run_subcommand_prints_resolved_spec(capsys):
    """`bench run-dry --suite ifeval --n 5` prints a resolved RunSpec as JSON."""
    rc = cli_main(["run-dry", "--suite", "ifeval", "--n", "5", "--seed", "7"])
    assert rc == 0
    captured = capsys.readouterr()
    # Status line then JSON dump of the RunSpec.
    json_blob = captured.out.split("\n", 1)[-1].strip()
    # Prefer the last JSON object if a banner precedes it.
    start = json_blob.find("{")
    assert start >= 0
    obj = json.loads(json_blob[start:])
    assert obj["suite"] == "ifeval"
    assert obj["n"] == 5
    assert obj["seed"] == 7


def test_cli_rejects_unknown_suite():
    """An unknown --suite value fails at run time (registry lookup)."""
    with pytest.raises(KeyError):
        cli_main(["run-dry", "--suite", "totally-bogus", "--n", "1"])


# ---------------------------------------------------------------------------
# 2. Suite registration auto-discovery (via __init_subclass__)
# ---------------------------------------------------------------------------


def test_suite_subclass_auto_registers():
    """Subclasses of `Suite` auto-register on import / class-construction."""

    class DeepSWE(Suite):
        name = "deep-swe"
        source_url = "github.com/agentica-project/DeepSWE"
        format = "bash via mini-swe-agent"
        subset = "n=5 seed=42"
        rationale = "flagship SWE capability"

    registered = {cls.name for cls in list_suites()}
    assert "deep-swe" in registered
    spec = get_suite_spec("deep-swe")
    assert spec.source_url == "github.com/agentica-project/DeepSWE"


def test_suite_duplicate_registration_raises():
    """A second subclass with the same `name` raises on definition."""

    class A(Suite):
        name = "dup"

    # A second subclass with the same `name` must raise (registration collision).
    with pytest.raises(RuntimeError, match="already registered"):

        class B(Suite):  # noqa: F841
            name = "dup"

    # And the original is still in the registry.
    assert get_suite("dup") is A


# ---------------------------------------------------------------------------
# 3. @task and @metric decorator behaviors
# ---------------------------------------------------------------------------


def test_task_decorator_registers():
    """`@task(...)` registers a Task and keeps the underlying callable callable."""

    @task_decorator(task_id="ifeval-001", suite="ifeval", category="format")
    def my_handler(prompt: str) -> str:
        return prompt.upper()

    # Decorator returns the original function, which is still usable.
    assert my_handler("abc") == "ABC"
    t = get_task("ifeval-001")
    assert isinstance(t, Task)
    assert t.suite == "ifeval"
    assert t.metadata.get("category") == "format"


def test_metric_decorator_registers_and_coerces():
    """`@metric(...)` registers a Metric; MetricSet.coerce from dict works."""

    @metric_decorator(
        name="tokens_per_sec", units="tok/s", source="pheno.eval.perplexity"
    )
    def compute_tps() -> float:
        return 123.4

    m = get_metric("tokens_per_sec")
    assert isinstance(m, Metric)
    assert m.value == pytest.approx(123.4)
    assert m.units == "tok/s"
    # Coercion path
    metric_set = MetricSet.coerce(
        {"pass@1": {"value": 0.66, "source": "pheno", "units": "ratio"}}
    )
    assert "pass@1" in metric_set.metrics
    assert metric_set.get("pass@1").value == pytest.approx(0.66)
    # Coercion with raw number
    metric_set2 = MetricSet.coerce({"inline": 1.23})
    assert metric_set2.get("inline").value == pytest.approx(1.23)


# ---------------------------------------------------------------------------
# 4. ATIF v1.7 + CTRF roundtrip
# ---------------------------------------------------------------------------


def test_atif_roundtrip(tmp_path):
    """parse_atif then re-serialize parses to a consistent RunRecord set."""
    doc = {
        "schema": "ATIF/1.7",
        "trajectories": [
            {
                "session_id": "sess-1",
                "agent_name": "pheno.eval.agent_loop",
                "suite": "ifeval",
                "task_id": "ifeval-001",
                "model": "Qwen3.5-0.8B",
                "started_at": "2026-07-16T00:00:00Z",
                "stopped_at": "2026-07-16T00:01:00Z",
                "steps": [
                    {"step_id": 0, "role": "user", "content": "hello"},
                    {
                        "step_id": 1,
                        "role": "assistant",
                        "content": "hi",
                        "tool_calls": [{"name": "search", "arguments": {"q": "hi"}}],
                    },
                ],
            }
        ],
    }
    docs_file = tmp_path / "doc.json"
    docs_file.write_text(json.dumps(doc), encoding="utf-8")
    records = read_atif_document(str(docs_file))
    assert len(records) == 1
    rec = records[0]
    assert rec.source_format == RecordFormat.ATIF
    assert rec.task_id == "ifeval-001"
    assert len(rec.steps) == 2
    assert rec.steps[1].tool_calls[0].name == "search"
    # Round-trip through RunRecord.from_dict
    rec2 = RunRecord.from_dict(rec.to_dict())
    assert rec2.task_id == rec.task_id
    assert rec2.steps[1].tool_calls[0].name == "search"
    assert rec2.source_format == RecordFormat.ATIF


def test_ctrf_roundtrip(tmp_path):
    """parse_ctrf normalizes a CTRF payload into RunRecords with Step latency."""
    doc = {
        "report": {
            "title": "pheno-bench",
            "timestamp": "2026-07-16T00:00:00Z",
            "status": "passed",
            "summary": "1/2 passed",
            "testFramework": "pheno.eval.ctrf",
        },
        "results": [
            {
                "name": "ifeval-001",
                "suite": "ifeval",
                "status": "passed",
                "duration": 1234,
                "started": "2026-07-16T00:00:00Z",
                "stopped": "2026-07-16T00:00:01Z",
                "steps": [
                    {"step_id": 0, "message": "step-one", "duration": 50},
                    {"step_id": 1, "message": "step-two", "duration": 70},
                ],
            },
            {
                "name": "ifeval-002",
                "suite": "ifeval",
                "status": "failed",
                "duration": 4321,
                "started": "2026-07-16T00:00:01Z",
                "stopped": "2026-07-16T00:00:05Z",
            },
        ],
    }
    p = tmp_path / "ctrf.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    records = read_ctrf_document(str(p))
    assert len(records) == 2
    assert records[0].source_format == RecordFormat.CTRF
    assert records[0].task_id == "ifeval-001"
    assert records[0].status == "passed"
    assert records[0].steps[0].latency_ms == 50.0
    # Records serialize to JSON and come back identical
    payload = records[0].to_json()
    reparsed = RunRecord.from_dict(json.loads(payload))
    assert reparsed.task_id == records[0].task_id


def test_jsonl_roundtrip(tmp_path):
    """write_jsonl + read_jsonl preserves a stream of RunRecords."""
    records = [
        RunRecord(
            record_id="r1",
            source_format=RecordFormat.UNIFIED,
            suite="ifeval",
            task_id=f"task-{i}",
            agent="pheno",
            model="Qwen3.5-0.8B",
            started_at="2026-07-16T00:00:00Z",
            stopped_at="2026-07-16T00:00:01Z",
            steps=[Step(step_id=0, role=StepRole.USER, content=f"prompt-{i}")],
            status="pass",
        )
        for i in range(5)
    ]
    p = tmp_path / "stream.jsonl"
    written = write_jsonl(records, p)
    assert written == 5
    read_back = list(read_jsonl(p))
    assert len(read_back) == 5
    assert [r.task_id for r in read_back] == [f"task-{i}" for i in range(5)]


# ---------------------------------------------------------------------------
# 5. Type equality + serialization
# ---------------------------------------------------------------------------


def test_runspec_dataclass_equality_and_json_roundtrip():
    """RunSpec dataclass equality compares value-equal instances and JSON is stable."""
    a = RunSpec(
        suite="ifeval",
        n=5,
        seed=42,
        model="Qwen3.5-0.8B",
        judge_model="claude-sonnet-5",
        judge_mode=JudgeMode.LLM,
        energy_source=EnergySource.POWERMETRICS,
        output="/tmp/x.json",  # nosec B108 - test fixture; sandboxed
        run_id="r1",
    )
    b = RunSpec(
        suite="ifeval",
        n=5,
        seed=42,
        model="Qwen3.5-0.8B",
        judge_model="claude-sonnet-5",
        judge_mode=JudgeMode.LLM,
        energy_source=EnergySource.POWERMETRICS,
        output="/tmp/x.json",  # nosec B108 - test fixture; sandboxed
        run_id="r1",
    )
    assert a == b
    blob = json.dumps(a.to_dict(), sort_keys=True)
    obj = json.loads(blob)
    assert obj["judge_mode"] == "llm"
    assert obj["energy_source"] == "powermetrics"


def test_suite_result_json_roundtrip_and_status_enum():
    """SuiteResult dumps and loads back with TaskStatus enum preserved."""
    res = SuiteResult(
        run_id="r1",
        suite="ifeval",
        model="Qwen3.5-0.8B",
        started_at="2026-07-16T00:00:00Z",
        stopped_at="2026-07-16T00:00:05Z",
        tasks=[
            TaskResult(
                task_id="t1", status=TaskStatus.PASS, duration_s=1.0, reward=1.0
            ),
            TaskResult(
                task_id="t2", status=TaskStatus.FAIL, duration_s=1.5, reward=0.0
            ),
        ],
        metrics={"pass@1": 0.5},
    )
    payload = res.to_json()
    restored = SuiteResult.from_json(payload)
    assert restored == res
    assert restored.tasks[0].status == TaskStatus.PASS
    assert restored.tasks[1].status == TaskStatus.FAIL
    assert restored.metrics == {"pass@1": 0.5}


def test_run_report_serializes_full_nesting():
    """RunReport round-trips nested SuiteResult list."""
    res = SuiteResult(
        run_id="r1",
        suite="ifeval",
        model="Qwen3.5-0.8B",
        started_at="2026-07-16T00:00:00Z",
        stopped_at="2026-07-16T00:00:05Z",
    )
    rep = RunReport(
        version=__version__,
        generated_at="2026-07-16T00:00:05Z",
        run_id="r1",
        judge_mode=JudgeMode.DETERMINISTIC,
        energy_source=EnergySource.NVIDIA_SMI,
        results=[res],
    )
    obj = json.loads(rep.to_json())
    assert obj["version"] == __version__
    assert obj["judge_mode"] == "deterministic"
    assert len(obj["results"]) == 1
    assert obj["results"][0]["suite"] == "ifeval"


# ---------------------------------------------------------------------------
# 6. Metric helpers (percentile / wilson_ci / cosine_similarity)
# ---------------------------------------------------------------------------


def test_metric_helpers_percentile_and_wilson():
    """percentile + wilson_ci numerical correctness."""
    # Percentile of [1..100]
    values = list(range(1, 101))
    assert percentile(values, 50.0) == pytest.approx(50.5, abs=0.01)
    assert percentile(values, 95.0) == pytest.approx(95.05, abs=0.01)
    # Empty list
    assert math.isnan(percentile([], 50.0))
    # Wilson CI for 80/100 ≈ 0.80 +/- ~0.08
    center, margin = wilson_ci(80, 100)
    assert 0.70 < center < 0.80  # center < raw rate is normal for Wilson
    assert 0.05 < margin < 0.10


def test_metric_helpers_cosine_similarity_and_semantic_drift():
    """cosine_similarity: identical vectors → 1.0; orthogonal → 0.0; opposite → -1.0."""
    # Identical
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    # Orthogonal
    assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)
    # Opposite
    assert cosine_similarity([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)
    # semantic_drift = 1 - cos
    drift = semantic_drift([1, 0, 0], [1, 0, 0])
    assert drift == pytest.approx(0.0)
    drift2 = semantic_drift([1, 0, 0], [0, 1, 0])
    assert drift2 == pytest.approx(1.0)
    # Length mismatch raises
    with pytest.raises(ValueError):
        cosine_similarity([1, 0], [1, 0, 0])


# ---------------------------------------------------------------------------
# 7. Spec parsing
# ---------------------------------------------------------------------------


def test_spec_table_parsing(tmp_path):
    """parse_spec_file extracts suite rows and metric names from the spec doc."""
    md = (
        "# Benchmark Harness Spec\n"
        "**Doc ID:** 2026-07-16-test\n"
        "**Version:** 1.0\n"
        "**Date:** 2026-07-16\n"
        "**Status:** Draft\n"
        "\n"
        "## 2. Suite selection (10 suites, locked)\n"
        "\n"
        "| # | Suite | Source URL | Format | Subset | Why |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | **DeepSWE v1.1** | `github.com/agentica-project/DeepSWE` | bash | n=5 | flagship |\n"
        "| 2 | **terminal-bench 2.0** | `github.com/laude-institute/terminal-bench` | Harbor | n=5 | harness |\n"
        "\n"
        "## 4. Metrics matrix (per `(suite, model)` row)\n"
        "\n"
        "### 4.1 Quality\n"
        "- `pass@1` (binary)\n"
        "- `pass@4` (4-run any-pass)\n"
    )
    p = tmp_path / "spec.md"
    p.write_text(md, encoding="utf-8")
    from bench.spec import parse_spec_file

    facts = parse_spec_file(p)
    assert facts.doc_id == "2026-07-16-test"
    assert facts.version == "1.0"
    assert len(facts.suites) == 2
    # Suite names are extracted verbatim from the bolded cell content.
    assert facts.suites[0].name.startswith("DeepSWE")
    assert "agentica-project" in facts.suites[0].source_url
    assert "pass@1" in facts.metrics
    assert "pass@4" in facts.metrics


# ---------------------------------------------------------------------------
# 8. Full `python -m bench --version` smoke
# ---------------------------------------------------------------------------


def test_python_m_bench_module_invocation():
    """`python -m bench --version` exits 0 and prints the version banner."""
    result = subprocess.run(
        [sys.executable, "-m", "bench", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


# ---------------------------------------------------------------------------
# 9. Spec Q4 catalog sanity check
# ---------------------------------------------------------------------------


def test_spec_q4_metric_catalog_includes_all_categories():
    """SPEC_Q4_METRICS covers every section of the §4 matrix."""
    name_set = set(SPEC_Q4_METRICS)
    # Quality
    assert "pass@1" in name_set
    # Tool-call stability
    assert "tool_call_success_rate" in name_set
    assert "dead_end_rate" in name_set
    # HW/SW perf
    assert "peak_RSS_MB" in name_set
    assert "energy_proxy_joules" in name_set
    # Speed
    assert "first_token_latency_p95" in name_set
    # Conciseness
    assert "redundant_tool_call_rate" in name_set
    # Long-horizon stability
    assert "semantic_drift_p99" in name_set
