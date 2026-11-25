# Mypy Error Inventory — v0.10 Phase 1 Sweep

> DAG Task 2 (`docs/plans/2026-08-08-pheno-harness-WBS-PERT-100-v0.10.md`).
> Batched inventory of remaining mypy type errors feeding the Phase 1
> type-error sweep (tasks 6–24). Depends on task 1 (DAG landed).

## Header

| Field | Value |
|-------|-------|
| as_of | 2026-08-08 |
| HEAD | `a54a51e` (branch `wip/2026-07-28-pheno-harness-m80-d76`) |
| mypy version | 2.3.0 (compiled: yes), throwaway venv `C:\Users\koosh\AppData\Local\Temp\proc-mypy-venv` |
| command | `C:\Users\koosh\AppData\Local\Temp\proc-mypy-venv\Scripts\python.exe -m mypy bench/ pheno/ verifier/ eval/` (run from repo root; config discovered from `pyproject.toml` `[tool.mypy]`; full output captured to `C:\Users\koosh\AppData\Local\Temp\mypy_scan_aug08.txt`) |
| total error count | **371** |
| baseline (audit `5433e4b`, post-v0.9) | **212** |
| delta | **+159** |

### Delta note (do not fudge)

The +159 delta is **not** a single-cause regression. Contributing factors,
recorded for the sweep planners:

1. **Mypy version drift.** The baseline 212 was measured at audit commit
   `5433e4b` with the audit-environment mypy; this scan uses mypy 2.3.0,
   which emits newer error classes (e.g. `func-returns-value`,
   `unused-coroutine`, tighter `override`/`call-overload` checks) that the
   audit binary did not report.
2. **HEAD drift.** This scan runs at `a54a51e`, which contains many files
   added since `5433e4b` (notably `pheno/evidence/*`, `pheno/preservation.py`
   (29 errors), `bench/suites/*`, `bench/rlvr_af/*`). Those are new errors
   relative to the audit snapshot.
3. **Scan scope.** Per DAG task 2 instructions the scan covers
   `bench/ pheno/ verifier/ eval/`; AGENTS.md §10.6 canonical invocation is
   `pheno/ bench/` only. `verifier/` + `eval/` contributed errors outside the
   Phase 1 file set (counted in the appendix).
4. **Windows-host platform artifacts.** Running mypy on this win32 host
   surfaces `signal.SIGALRM`/`signal.alarm` (missing on Windows) in
   `bench/adapters_mlx.py` and `resource.getrusage`/`RUSAGE_SELF` in
   `bench/perf.py`. These are `attr-defined` errors that will likely
   disappear on the macOS/WSL reference hosts; they are flagged inline.

## DAG task mapping (tasks 6–24)

Per-file error clusters with exact line numbers from this scan, mapped to
the DAG task that owns each file. Fix class legend: **annotation** = add a
type annotation / narrow a variable type; **typecast** = `cast(...)` or
explicit type narrowing; **protocol** = define/use a `Protocol` or a
dataclass instead of raw `str`/`dict`; **platform** = guard
platform-specific stdlib modules (`signal`, `resource`) behind
`sys.platform` / `os.name` checks.

| DAG task | File (DAG-cited line) | Errors this scan | Detail |
|----------|------------------------|------------------|--------|
| 6 | `bench/adapters.py:246` | 0 | No errors in file this scan. |
| 7 | `bench/adapters_mlx.py:127` | 4 | Errors at 100, 101, 112, 113 (platform). `:127` clean. |
| 8 | `bench/adapters_openai.py:62` | 0 | No errors in file this scan. |
| 9 | `bench/adapters_anthropic.py:23` | 0 | No errors in file this scan. |
| 10 | `bench/adapters_mock.py` | 0 | No errors in file this scan. |
| 11 | `bench/comparison/_forge_reply_parser.py` | 0 | No errors in file this scan. |
| 12 | `bench/comparison/stock_vs_ours_adapters.py:207` | 8 | Lines 207, 229, 233, 236, 237, 238, 239, 245. |
| 13 | `bench/comparison/run_minimax_m3.py:188` | 0 | No errors in file this scan. |
| 14 | `bench/comparison/run_5min_matrix.py:114` | 0 | No errors in file this scan. (Note: sibling `run_5min_benchmark.py:125` has 1 error → appendix.) |
| 15 | `bench/comparison/run_5min_matrix.py:375` | 0 | No errors in file this scan. |
| 16 | `bench/matrix/run_ablation.py:153` | 2 | Line 153 (two `attr-defined`). |
| 17 | `bench/matrix/run_ablation.py:160` | 2 | Lines 160, 161. |
| 18 | `bench/perf.py:221` | 3 | Line 221 (misc) + 37 (2× platform). |
| 19 | `bench/registry.py:131` | 2 | Lines 57, 131. |
| 20 | `bench/report.py:244` | 1 | Line 244. |
| 21 | `bench/cli.py:211` | 0 | No errors in file this scan (matches DAG "already done; verify"). |
| 22 | `bench/parallel.py:227` | 0 | No errors in file this scan. |
| 23 | `bench/console.py:52` | 0 | No errors in file this scan. |
| 24 | `bench/energy.py:241` | 6 | Lines 159, 164 (×2), 241, 274, 301. |

### Cluster 7 — `bench/adapters_mlx.py` (4 errors, all platform)

- line 100: `Module has no attribute "SIGALRM"` — `[attr-defined]` — **platform** (Windows lacks SIGALRM; guard behind `sys.platform != "win32"`)
- line 101: `Module has no attribute "alarm"` — `[attr-defined]` — **platform**
- line 112: `Module has no attribute "alarm"` — `[attr-defined]` — **platform**
- line 113: `Module has no attribute "SIGALRM"` — `[attr-defined]` — **platform**

### Cluster 12 — `bench/comparison/stock_vs_ours_adapters.py` (8 errors)

- line 207: `"MLXDirect" has no attribute "model_id"` — `[attr-defined]` — **protocol** (add `model_id` to `MLXDirect` or the Protocol it must satisfy)
- line 229: `"str" has no attribute "ok"` — `[attr-defined]` — **protocol** (caller treats `str` as a result object; bind to a Protocol/dataclass)
- line 233: `"str" has no attribute "text"` — `[attr-defined]` — **protocol**
- line 236: `"str" has no attribute "prompt_tokens"` — `[attr-defined]` — **protocol**
- line 237: `"str" has no attribute "completion_tokens"` — `[attr-defined]` — **protocol**
- line 238: `"str" has no attribute "first_token_latency_ms"` — `[attr-defined]` — **protocol**
- line 239: `"str" has no attribute "tokens_per_second"` — `[attr-defined]` — **protocol**
- line 245: `"str" has no attribute "error"` — `[attr-defined]` — **protocol**

### Cluster 16/17 — `bench/matrix/run_ablation.py` (4 errors)

- line 153: `"str" has no attribute "ok"` — `[attr-defined]` — **protocol** (task 16; DAG cites exactly this)
- line 153: `"str" has no attribute "text"` — `[attr-defined]` — **protocol** (task 16)
- line 160: `"str" has no attribute "wall_clock_s"` — `[attr-defined]` — **protocol** (task 17; DAG cites exactly this)
- line 161: `"str" has no attribute "text"` — `[attr-defined]` — **protocol** (task 17)

### Cluster 18 — `bench/perf.py` (3 errors)

- line 37: `Module has no attribute "getrusage"` — `[attr-defined]` — **platform**
- line 37: `Module has no attribute "RUSAGE_SELF"` — `[attr-defined]` — **platform**
- line 221: `List comprehension has incompatible type List[dict[str, float | int | str]]; expected List[PerfReading]` — `[misc]` — **typecast** (task 18; DAG cites exactly this)

### Cluster 19 — `bench/registry.py` (2 errors)

- line 57: `No return value expected` — `[return-value]` — **annotation** (stray `return <value>` in a `-> None` fn, or missing return annotation)
- line 131: `Incompatible return value type (got "Callable[..., Any]", expected "Task")` — `[return-value]` — **annotation/typecast** (task 19; DAG cites exactly this)

### Cluster 20 — `bench/report.py` (1 error)

- line 244: `Argument 1 to "asdict" has incompatible type "DataclassInstance | type[DataclassInstance]"; expected "DataclassInstance"` — `[arg-type]` — **typecast** (task 20; DAG cites exactly this)

### Cluster 24 — `bench/energy.py` (6 errors)

- line 159: `Item "None" of "IO[Any] | None" has no attribute "readline"` — `[union-attr]` — **annotation** (narrow `IO[Any] | None` before `.readline`)
- line 164: `No overload variant of "max" matches argument types "float", "None"` — `[call-overload]` — **annotation/typecast**
- line 164: `"_on_line" of "_EnergySource" does not return a value (it only ever returns None)` — `[func-returns-value]` — **annotation**
- line 241: `Return type "float" of "_on_line" incompatible with return type "None" in supertype "_EnergySource"` — `[override]` — **annotation** (task 24; DAG cites exactly this)
- line 274: `Return type "float" of "_on_line" incompatible with return type "None" in supertype "_EnergySource"` — `[override]` — **annotation**
- line 301: `Return type "float" of "_on_line" incompatible with return type "None" in supertype "_EnergySource"` — `[override]` — **annotation**

### Zero-error DAG files (this scan)

Ten task-6–24 files had **zero errors** at `a54a51e`: `bench/adapters.py`
(6), `bench/adapters_openai.py` (8), `bench/adapters_anthropic.py` (9),
`bench/adapters_mock.py` (10), `bench/comparison/_forge_reply_parser.py`
(11), `bench/comparison/run_minimax_m3.py` (13),
`bench/comparison/run_5min_matrix.py` (14, 15), `bench/cli.py` (21),
`bench/parallel.py` (22), `bench/console.py` (23). Tasks 6, 8, 9, 10, 11,
13, 14, 15, 21, 22, 23 can be verified-then-closed without code edits, or
re-validated at their fix line on the sweep's merge base.

## Batch summary

| DAG task | File (DAG-cited line) | Errors this scan |
|----------|------------------------|------------------|
| 6 | `bench/adapters.py:246` | 0 |
| 7 | `bench/adapters_mlx.py:127` | 4 |
| 8 | `bench/adapters_openai.py:62` | 0 |
| 9 | `bench/adapters_anthropic.py:23` | 0 |
| 10 | `bench/adapters_mock.py` | 0 |
| 11 | `bench/comparison/_forge_reply_parser.py` | 0 |
| 12 | `bench/comparison/stock_vs_ours_adapters.py:207` | 8 |
| 13 | `bench/comparison/run_minimax_m3.py:188` | 0 |
| 14 | `bench/comparison/run_5min_matrix.py:114` | 0 |
| 15 | `bench/comparison/run_5min_matrix.py:375` | 0 |
| 16 | `bench/matrix/run_ablation.py:153` | 2 |
| 17 | `bench/matrix/run_ablation.py:160` | 2 |
| 18 | `bench/perf.py:221` | 3 |
| 19 | `bench/registry.py:131` | 2 |
| 20 | `bench/report.py:244` | 1 |
| 21 | `bench/cli.py:211` | 0 |
| 22 | `bench/parallel.py:227` | 0 |
| 23 | `bench/console.py:52` | 0 |
| 24 | `bench/energy.py:241` | 6 |
| **Subtotal (tasks 6–24)** | | **28** |
| Appendix (non-mapped errors) | | **343** |
| **Total** | | **371** |

Sum check: 0+4+0+0+0+0+8+0+0+0+2+2+3+2+1+0+0+0+6 = 28 mapped;
28 + 343 = 371 = scan total.

## Appendix — errors outside the DAG task mapping (343)

These errors live outside the task-6–24 file set (primarily `pheno/`,
`eval/`, `verifier/`, `bench/suites/`, `bench/rlvr_af/`,
`bench/results/`, `bench/v0/`) and inform future phases (Phase 3
`eval/` + `verifier/` docstring/type narrowing, Phase 6 MLX-stub +
adapters typing, and general debt). Grouped by file with exact line
numbers from this scan.

### bench/benchmark_envelope.py (1 errors)
- line 39: `No overload variant of "dict" matches argument type "TaskResult"  [call-overload]`

### bench/comparison/run_5min_benchmark.py (1 errors)
- line 125: `Value of type "Coroutine[Any, Any, None]" must be used  [unused-coroutine]`

### bench/judge_runner.py (2 errors)
- line 222: `Item "None" of "ModelAdapter | None" has no attribute "complete"  [union-attr]`
- line 337: `"None" not callable  [misc]`

### bench/results/kernelbench/2026-08-01/_probe_backend.py (1 errors)
- line 23: `Incompatible types in assignment (expression has type "list[str]", target has type "dict[str, Any]")  [assignment]`

### bench/results/kernelbench/2026-08-01/_probe_toolchain.py (9 errors)
- line 14: `Unsupported target for indexed assignment ("Collection[str]")  [index]`
- line 16: `Unsupported target for indexed assignment ("Collection[str]")  [index]`
- line 21: `Incompatible types in assignment (expression has type "bool", target has type "Collection[str]")  [assignment]`
- line 22: `Incompatible types in assignment (expression has type "int", target has type "Collection[str]")  [assignment]`
- line 32: `Incompatible types in assignment (expression has type "list[dict[str, Any]]", target has type "Collection[str]")  [assignment]`
- line 37: `Incompatible types in assignment (expression has type "str | None", target has type "Collection[str]")  [assignment]`
- line 53: `Incompatible types in assignment (expression has type "None", target has type "Collection[str]")  [assignment]`
- line 56: `List item 0 has incompatible type "Collection[str]"; expected "str | bytes | PathLike[str] | PathLike[bytes]"  [list-item]`
- line 68: `Incompatible types in assignment (expression has type "int", target has type "Collection[str]")  [assignment]`

### bench/results/kernelbench/2026-08-01/_probe_wsl.py (3 errors)
- line 17: `Incompatible types in assignment (expression has type "int", target has type "str")  [assignment]`
- line 28: `Incompatible types in assignment (expression has type "list[str]", target has type "str")  [assignment]`
- line 44: `Incompatible types in assignment (expression has type "dict[str, Any]", target has type "str")  [assignment]`

### bench/rlvr_af/critic.py (14 errors)
- line 90: `"Transition" has no attribute "index"  [attr-defined]`
- line 90: `"Artifact" has no attribute "task_id"  [attr-defined]`
- line 98: `"Transition" has no attribute "index"  [attr-defined]`
- line 101: `"Artifact" has no attribute "meta"  [attr-defined]`
- line 103: `"Transition" has no attribute "index"  [attr-defined]`
- line 108: `"Transition" has no attribute "index"  [attr-defined]`
- line 114: `"Transition" has no attribute "index"  [attr-defined]`
- line 120: `"Transition" has no attribute "index"  [attr-defined]`
- line 187: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 188: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 198: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 198: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 206: `"Transition" has no attribute "index"  [attr-defined]`
- line 206: `"Artifact" has no attribute "task_id"  [attr-defined]`

### bench/rlvr_af/optimize.py (9 errors)
- line 120: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 121: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 147: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 179: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 180: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 213: `"Trail" has no attribute "suite_name"  [attr-defined]`
- line 213: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 268: `"Trail" has no attribute "trail_id"  [attr-defined]`
- line 269: `"Trail" has no attribute "suite_name"  [attr-defined]`

### bench/runner/model_adapter_openai.py (1 errors)
- line 21: `Name "_openai_mod" already defined on line 19  [no-redef]`

### bench/seeds.py (3 errors)
- line 57: `Incompatible types in assignment (expression has type "None", variable has type "list[str]")  [assignment]`
- line 105: `Argument "task_ids" to "Subset" has incompatible type "list[str] | None"; expected "list[str]"  [arg-type]`
- line 115: `Argument "task_ids" to "Subset" has incompatible type "list[str] | None"; expected "list[str]"  [arg-type]`

### bench/suites/_stub.py (2 errors)
- line 83: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 175: `"SuiteSpec" has no attribute "subset"  [attr-defined]`

### bench/suites/arc_agi2.py (3 errors)
- line 128: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 152: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 203: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/bfcl_v4.py (3 errors)
- line 86: `Name "args" already defined on line 60  [no-redef]`
- line 136: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 152: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/browsercomp.py (4 errors)
- line 284: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 305: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, str]"; expected "tuple[str, ...]"  [arg-type]`
- line 309: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 320: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/suites/container_runner.py (2 errors)
- line 307: `Unexpected keyword argument "wall_clock_s" for "ContainerRunResult"  [call-arg]`
- line 347: `Unexpected keyword argument "wall_clock_s" for "ContainerRunResult"  [call-arg]`

### bench/suites/dataset_loader.py (1 errors)
- line 21: `Module "datasets" has no attribute "load_dataset"  [attr-defined]`

### bench/suites/deepswe.py (3 errors)
- line 60: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 86: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 153: `Name "RunSpec_Result" is not defined  [name-defined]`

### bench/suites/gpqa_diamond.py (2 errors)
- line 54: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 67: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/hle.py (12 errors)
- line 30: `List item 0 has incompatible type "str"; expected "tuple[str, str, str]"  [list-item]`
- line 40: `Argument "paper_metrics" to "SuiteSpec" has incompatible type "list[tuple[str, str, str]]"; expected "tuple[str, ...]"  [arg-type]`
- line 48: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 53: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 55: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 59: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 61: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 66: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 68: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 72: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 74: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 78: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`

### bench/suites/ifeval.py (3 errors)
- line 211: `Incompatible return value type (got "tuple[Literal[''] | bool, bool]", expected "tuple[bool, bool]")  [return-value]`
- line 273: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 287: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/kernelbench.py (9 errors)
- line 263: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 288: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 298: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 302: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 312: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`
- line 315: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`
- line 316: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`
- line 317: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`
- line 318: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/suites/mmlu_pro.py (2 errors)
- line 64: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 78: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/mt_bench.py (2 errors)
- line 48: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 77: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/osworld.py (5 errors)
- line 102: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 138: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 146: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 157: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`
- line 158: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/suites/perplexity.py (12 errors)
- line 32: `List item 0 has incompatible type "str"; expected "tuple[str, str, str]"  [list-item]`
- line 42: `Argument "paper_metrics" to "SuiteSpec" has incompatible type "list[tuple[str, str, str]]"; expected "tuple[str, ...]"  [arg-type]`
- line 50: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 55: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 57: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 62: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 64: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 69: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 71: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 74: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`
- line 76: `Missing positional argument "suite" in call to "TaskSpec"  [call-arg]`
- line 80: `Argument "tags" to "TaskSpec" has incompatible type "list[str]"; expected "tuple[str, ...]"  [arg-type]`

### bench/suites/pinchbench.py (4 errors)
- line 85: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 106: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 110: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 118: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/suites/startup_bench.py (10 errors)
- line 53: `Need type annotation for "out"  [var-annotated]`
- line 62: `No overload variant of "__add__" of "list" matches argument type "int"  [operator]`
- line 62: `Unsupported operand types for + ("None" and "int")  [operator]`
- line 63: `Item "int" of "list[Any] | int | None" has no attribute "append"  [union-attr]`
- line 63: `Item "None" of "list[Any] | int | None" has no attribute "append"  [union-attr]`
- line 69: `Incompatible types in assignment (expression has type "dict[str, float]", target has type "list[Any] | int | None")  [assignment]`
- line 98: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 129: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, object]"; expected "tuple[str, ...]"  [arg-type]`
- line 134: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 152: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/suites/swe_bench_verified.py (2 errors)
- line 41: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 61: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/terminal_bench.py (2 errors)
- line 43: `Incompatible types in assignment (expression has type "str", base class "BaseSuite" defined the type as "JudgeMode")  [assignment]`
- line 62: `Signature of "subset" incompatible with supertype "Suite"  [override]`

### bench/suites/vending_bench.py (14 errors)
- line 51: `Need type annotation for "out"  [var-annotated]`
- line 60: `No overload variant of "__add__" of "list" matches argument type "int"  [operator]`
- line 60: `Unsupported operand types for + ("None" and "int")  [operator]`
- line 61: `Item "int" of "list[Any] | int | None" has no attribute "append"  [union-attr]`
- line 61: `Item "None" of "list[Any] | int | None" has no attribute "append"  [union-attr]`
- line 66: `Incompatible types in assignment (expression has type "float", target has type "list[Any] | int | None")  [assignment]`
- line 71: `Unsupported operand types for <= ("float" and "None")  [operator]`
- line 71: `Argument 1 to "max" has incompatible type "int"; expected "list[Any]"  [arg-type]`
- line 71: `Argument 2 to "max" has incompatible type "float"; expected "list[Any]"  [arg-type]`
- line 89: `Incompatible types in assignment (expression has type "tuple[str, ...]", base class "BaseSuite" defined the type as "list[tuple[str, str, str]]")  [assignment]`
- line 108: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, float]"; expected "tuple[str, ...]"  [arg-type]`
- line 115: `Argument "tags" to "TaskSpec" has incompatible type "dict[str, float]"; expected "tuple[str, ...]"  [arg-type]`
- line 119: `Signature of "subset" incompatible with supertype "Suite"  [override]`
- line 127: `No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]`

### bench/v0/contracts.py (7 errors)
- line 145: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 158: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 177: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 241: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 285: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 322: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`
- line 399: `Argument 2 to "_exact" has incompatible type "frozenset[str]"; expected "set[str]"  [arg-type]`

### eval/deepswe.py (6 errors)
- line 98: `Name "result" already defined on line 86  [no-redef]`
- line 101: `Unsupported target for indexed assignment ("CompletedProcess[str]")  [index]`
- line 104: `"CompletedProcess[str]" has no attribute "update"  [attr-defined]`
- line 111: `Incompatible return value type (got "CompletedProcess[str]", expected "dict[str, Any]")  [return-value]`
- line 113: `"CompletedProcess[str]" has no attribute "update"  [attr-defined]`
- line 114: `Incompatible return value type (got "CompletedProcess[str]", expected "dict[str, Any]")  [return-value]`

### eval/role_suite.py (1 errors)
- line 84: `Item "None" of "Any | dict[Any, Any] | None" has no attribute "get"  [union-attr]`

### eval/route_matrix.py (2 errors)
- line 202: `Unsupported target for indexed assignment ("list[dict[str, Any]] | str | Any | dict[str, Any] | None")  [index]`
- line 202: `No overload variant of "__setitem__" of "list" matches argument types "str", "dict[str, object]"  [call-overload]`

### perf/resources.py (1 errors)
- line 198: `Argument 1 to "run" has incompatible type "list[str | None]"; expected "str | bytes | PathLike[str] | PathLike[bytes] | Sequence[str | bytes | PathLike[str] | PathLike[bytes]]"  [arg-type]`

### pheno/analytical_capacity.py (4 errors)
- line 25: `Unsupported operand types for + ("int" and "object")  [operator]`
- line 27: `Unsupported operand types for - ("object" and "int")  [operator]`
- line 28: `Unsupported operand types for <= ("int" and "object")  [operator]`
- line 56: `Unsupported operand types for + ("int" and "object")  [operator]`

### pheno/authorization_non_escalation.py (2 errors)
- line 27: `Incompatible types in assignment (expression has type "None", variable has type "datetime")  [assignment]`
- line 39: `Unsupported operand types for / ("Path" and "None")  [operator]`

### pheno/authorization_request_materializer.py (2 errors)
- line 210: `Argument 2 to "_bound_file" has incompatible type "Any | None"; expected "str"  [arg-type]`
- line 210: `Argument 3 to "_bound_file" has incompatible type "Any | None"; expected "str"  [arg-type]`

### pheno/authorization_request_template.py (1 errors)
- line 217: `Argument 1 to "dict" has incompatible type "Any | None"; expected "SupportsKeysAndGetItem[Any, Any]"  [arg-type]`

### pheno/current_decision_status.py (1 errors)
- line 195: `Argument "evaluated_at_utc" to "_assemble" has incompatible type "Any | None"; expected "str"  [arg-type]`

### pheno/deepswe_execution_closure.py (8 errors)
- line 64: `Dict entry 1 has incompatible type "str": "int"; expected "str": "bool"  [dict-item]`
- line 77: `Value of type variable "SupportsRichComparisonT" of "sorted" cannot be "Any | None"  [type-var]`
- line 79: `Item "None" of "Any | None" has no attribute "get"  [union-attr]`
- line 79: `Dict entry 1 has incompatible type "str": "int"; expected "str": "bool"  [dict-item]`
- line 79: `Dict entry 2 has incompatible type "str": "Any | None"; expected "str": "bool"  [dict-item]`
- line 79: `Dict entry 3 has incompatible type "str": "str | None"; expected "str": "bool"  [dict-item]`
- line 81: `Dict entry 1 has incompatible type "str": "str | None"; expected "str": "bool"  [dict-item]`
- line 90: `Dict entry 1 has incompatible type "str": "dict[str, Any]"; expected "str": "bool"  [dict-item]`

### pheno/descendant_reparse_inventory.py (3 errors)
- line 69: `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, object]], object]"; expected "Callable[[dict[str, object]], SupportsDunderLT[Any] | SupportsDunderGT[Any]]"  [arg-type]`
- line 69: `Incompatible return value type (got "object", expected "SupportsDunderLT[Any] | SupportsDunderGT[Any]")  [return-value]`
- line 98: `Need type annotation for "blockers" (hint: "blockers: list[<type>] = ...")  [var-annotated]`

### pheno/device_model_runtime_coverage.py (1 errors)
- line 70: `Item "None" of "Any | None" has no attribute "__iter__" (not iterable)  [union-attr]`

### pheno/evidence/aggregate_contracts.py (1 errors)
- line 1540: `Incompatible types in assignment (expression has type "Any | None", variable has type "dict[str, Any]")  [assignment]`

### pheno/evidence/avs_numerator.py (6 errors)
- line 10: `Module "pheno.evidence.aggregate_contracts" has no attribute "validate_bound_aggregate_record"; maybe "validate_aggregate_record"?  [attr-defined]`
- line 20: `Module "pheno.evidence.trial_contracts" has no attribute "ARTIFACT_BUNDLE_SUMMARY_V2_SCHEMA_VERSION"; maybe "ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION"?  [attr-defined]`
- line 162: `Incompatible types in assignment (expression has type "Mapping[str, Any]", variable has type "dict[str, Any]")  [assignment]`
- line 164: `Unexpected keyword argument "accepted_step_summary" for "validate_trial_artifact_bundle"  [call-arg]`
- line 164: `Unexpected keyword argument "accepted_step_policy" for "validate_trial_artifact_bundle"  [call-arg]`
- line 164: `Unexpected keyword argument "require_accepted_step_proof" for "validate_trial_artifact_bundle"  [call-arg]`

### pheno/evidence/concurrency_contract.py (1 errors)
- line 90: `Need type annotation for "events" (hint: "events: list[<type>] = ...")  [var-annotated]`

### pheno/evidence/cost_allocation.py (4 errors)
- line 199: `Need type annotation for "meter_domains" (hint: "meter_domains: set[<type>] = ...")  [var-annotated]`
- line 199: `Need type annotation for "interval_groups" (hint: "interval_groups: dict[<type>, <type>] = ...")  [var-annotated]`
- line 318: `Need type annotation for "domains" (hint: "domains: set[<type>] = ...")  [var-annotated]`
- line 456: `Need type annotation for "rates_by"  [var-annotated]`

### pheno/evidence/cost_usage.py (4 errors)
- line 139: `Need type annotation for "children"  [var-annotated]`
- line 158: `Need type annotation for "assigned" (hint: "assigned: set[<type>] = ...")  [var-annotated]`
- line 158: `Need type annotation for "all_categories" (hint: "all_categories: set[<type>] = ...")  [var-annotated]`
- line 158: `Need type annotation for "all_domains" (hint: "all_domains: set[<type>] = ...")  [var-annotated]`

### pheno/evidence/coverage_audit.py (8 errors)
- line 81: `Need type annotation for "discovered" (hint: "discovered: list[<type>] = ...")  [var-annotated]`
- line 122: `Incompatible types in assignment (expression has type "bool", target has type "Collection[Collection[str]]")  [assignment]`
- line 244: `Item "int" of "dict[str, Any] | list[str] | int | str | Any | None" has no attribute "__iter__" (not iterable)  [union-attr]`
- line 244: `Item "None" of "dict[str, Any] | list[str] | int | str | Any | None" has no attribute "__iter__" (not iterable)  [union-attr]`
- line 245: `No overload variant of "__getitem__" of "list" matches argument type "str"  [call-overload]`
- line 245: `Value of type "dict[str, Any] | list[str] | int | str | Any | None" is not indexable  [index]`
- line 245: `Generator has incompatible item type "Any | str"; expected "bool"  [misc]`
- line 245: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`

### pheno/evidence/evaluation_bundle_v8.py (4 errors)
- line 165: `Item "None" of "Any | dict[Any, Any] | None" has no attribute "get"  [union-attr]`
- line 166: `Item "None" of "Any | dict[Any, Any] | None" has no attribute "get"  [union-attr]`
- line 178: `Item "None" of "Any | dict[Any, Any] | None" has no attribute "get"  [union-attr]`
- line 179: `Item "None" of "Any | dict[Any, Any] | None" has no attribute "get"  [union-attr]`

### pheno/evidence/execute_run_denominator.py (3 errors)
- line 208: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 215: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 232: `Value of type "dict[str, Any] | None" is not indexable  [index]`

### pheno/evidence/execution_attempt_ledger.py (2 errors)
- line 266: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 268: `Value of type "dict[str, Any] | None" is not indexable  [index]`

### pheno/evidence/helper_cross_plan_readiness.py (11 errors)
- line 24: `Argument 1 to "validate_plan" has incompatible type "str | Any"; expected "Mapping[str, Any]"  [arg-type]`
- line 26: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 28: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 29: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 30: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 31: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 34: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 35: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 36: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 38: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`
- line 39: `Invalid index type "str" for "str"; expected type "SupportsIndex | slice[SupportsIndex | None, SupportsIndex | None, SupportsIndex | None]"  [index]`

### pheno/evidence/local_chatgpt_3090ti_review.py (1 errors)
- line 36: `Unsupported operand types for + ("object" and "int")  [operator]`

### pheno/evidence/physical_allocation.py (3 errors)
- line 109: `Need type annotation for "children"  [var-annotated]`
- line 176: `Need type annotation for "assigned_assets" (hint: "assigned_assets: set[<type>] = ...")  [var-annotated]`
- line 241: `Need type annotation for "authoritative_coverage" (hint: "authoritative_coverage: set[<type>] = ...")  [var-annotated]`

### pheno/evidence/promotion_gates.py (7 errors)
- line 15: `Module "pheno.evidence.aggregate_contracts" has no attribute "BOUND_AGGREGATE_SCHEMA_VERSION"; maybe "AGGREGATE_SCHEMA_VERSION"?  [attr-defined]`
- line 15: `Module "pheno.evidence.aggregate_contracts" has no attribute "validate_bound_aggregate_record"; maybe "validate_aggregate_record"?  [attr-defined]`
- line 20: `Module "pheno.evidence.replay_stability" has no attribute "BOUND_REPLAY_STABILITY_SCHEMA_VERSION"; maybe "REPLAY_STABILITY_SCHEMA_VERSION"?  [attr-defined]`
- line 20: `Module "pheno.evidence.replay_stability" has no attribute "validate_bound_replay_stability_record"; maybe "validate_replay_stability_record" or "build_replay_stability_record"?  [attr-defined]`
- line 270: `Incompatible types in assignment (expression has type "def calculate_avs_v7(record: Mapping[str, Any], *, trial_artifact_roots: Mapping[str, str | Path], facts_source_root: str | Path, counter_root: str | Path, telemetry_anchor_root: str | Path) -> dict[str, Any]", variable has type "def calculate_avs_v5(record: Mapping[str, Any], *, trial_artifact_roots: Mapping[str, str | Path], facts_source_root: str | Path, counter_root: str | Path) -> dict[str, Any]")  [assignment]`
- line 274: `Argument 2 has incompatible type "**dict[str, object]"; expected "Mapping[str, str | Path]"  [arg-type]`
- line 274: `Argument 2 has incompatible type "**dict[str, object]"; expected "str | Path"  [arg-type]`

### pheno/evidence/registry_import_dry_run.py (3 errors)
- line 170: `Argument 1 to "len" has incompatible type "Any | list[Any] | None"; expected "Sized"  [arg-type]`
- line 180: `Argument 1 to "enumerate" has incompatible type "Any | list[Any] | None"; expected "Iterable[Any]"  [arg-type]`
- line 304: `Argument 1 to "len" has incompatible type "Any | list[Any] | None"; expected "Sized"  [arg-type]`

### pheno/evidence/suite_score.py (10 errors)
- line 153: `Argument "at_time" to "validate_candidate_holdout_attestation" has incompatible type "str | None"; expected "str"  [arg-type]`
- line 158: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 241: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 261: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 262: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 266: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 267: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 268: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 269: `Value of type "dict[str, Any] | None" is not indexable  [index]`
- line 270: `Value of type "dict[str, Any] | None" is not indexable  [index]`

### pheno/evidence/telemetry_bundle_set.py (5 errors)
- line 49: `Need type annotation for "result"  [var-annotated]`
- line 125: `Incompatible types in assignment (expression has type "dict[str, Any] | None", variable has type "dict[str, Any]")  [assignment]`
- line 134: `Need type annotation for "domain_values" (hint: "domain_values: dict[<type>, <type>] = ...")  [var-annotated]`
- line 140: `Incompatible types in assignment (expression has type "None", target has type "int")  [assignment]`
- line 176: `Incompatible types in assignment (expression has type "dict[str, Any] | None", variable has type "dict[str, Any]")  [assignment]`

### pheno/evidence/telemetry.py (7 errors)
- line 800: `Argument 1 to "append" of "list" has incompatible type "int | str | None"; expected "str"  [arg-type]`
- line 802: `List item 0 has incompatible type "int | str | None"; expected "str"  [list-item]`
- line 802: `List item 1 has incompatible type "int | str | None"; expected "str"  [list-item]`
- line 809: `Argument "key" to "sort" of "list" has incompatible type "Callable[[dict[str, int | str | None]], int | str | None]"; expected "Callable[[dict[str, int | str | None]], SupportsDunderLT[Any] | SupportsDunderGT[Any]]"  [arg-type]`
- line 809: `Incompatible return value type (got "int | str | None", expected "SupportsDunderLT[Any] | SupportsDunderGT[Any]")  [return-value]`
- line 811: `Argument 1 to "log" has incompatible type "int | str | None"; expected "SupportsFloat | SupportsIndex"  [arg-type]`
- line 812: `Argument 1 to "log" has incompatible type "int | str | None"; expected "SupportsFloat | SupportsIndex"  [arg-type]`

### pheno/evidence/tiered_memory_evidence.py (7 errors)
- line 139: `Unsupported operand types for >= ("datetime" and "None")  [operator]`
- line 139: `Unsupported operand types for <= ("datetime" and "None")  [operator]`
- line 139: `Unsupported operand types for > ("datetime" and "None")  [operator]`
- line 139: `Unsupported operand types for < ("datetime" and "None")  [operator]`
- line 139: `Unsupported left operand type for > ("None")  [operator]`
- line 139: `No overload variant of "__sub__" of "datetime" matches argument type "None"  [operator]`
- line 139: `Unsupported left operand type for - ("None")  [operator]`

### pheno/evidence/training_capture_provenance.py (4 errors)
- line 88: `Need type annotation for "accepted" (hint: "accepted: dict[<type>, <type>] = ...")  [var-annotated]`
- line 149: `Need type annotation for "adj"  [var-annotated]`
- line 167: `Incompatible types in assignment (expression has type "str", variable has type "Mapping[str, Any]")  [assignment]`
- line 168: `Need type annotation for "reverse"  [var-annotated]`

### pheno/evidence/typed_operational_evidence.py (1 errors)
- line 34: `Item "None" of "timedelta | None" has no attribute "total_seconds"  [union-attr]`

### pheno/execution_capability.py (1 errors)
- line 78: `Incompatible return value type (got "object", expected "str")  [return-value]`

### pheno/inference_runner_projection.py (1 errors)
- line 12: `Module "pheno.runtime_admission" has no attribute "select_lane"  [attr-defined]`

### pheno/lane_identity_readiness.py (1 errors)
- line 10: `Module "pheno.runtime_admission" has no attribute "LANES"  [attr-defined]`

### pheno/mobile_envelope.py (1 errors)
- line 167: `Module has no attribute "binascii"  [attr-defined]`

### pheno/mobile_safety_telemetry.py (2 errors)
- line 200: `Unsupported operand types for <= ("datetime" and "None")  [operator]`
- line 214: `Module has no attribute "binascii"  [attr-defined]`

### pheno/objective_dependency_graph_status.py (1 errors)
- line 138: `Argument "evaluated_at_utc" to "_assemble" has incompatible type "Any | None"; expected "str"  [arg-type]`

### pheno/objective_dependency_graph.py (2 errors)
- line 29: `Value of type variable "SupportsRichComparisonT" of "sorted" cannot be "Sequence[Collection[str]]"  [type-var]`
- line 30: `Value of type variable "SupportsRichComparisonT" of "sorted" cannot be "Sequence[Collection[str]]"  [type-var]`

### pheno/owner_decision_dag.py (4 errors)
- line 15: `Need type annotation for "NODES"  [var-annotated]`
- line 54: `Item "bool" of "bool | str | Any | list[Any] | list[str] | None" has no attribute "__iter__" (not iterable)  [union-attr]`
- line 54: `Item "None" of "bool | str | Any | list[Any] | list[str] | None" has no attribute "__iter__" (not iterable)  [union-attr]`
- line 54: `Unsupported right operand type for in ("bool | str | Any | list[Any] | list[str] | None")  [operator]`

### pheno/placement_evidence_v2.py (1 errors)
- line 8: `Module "pheno.runtime_admission" has no attribute "LANES"  [attr-defined]`

### pheno/placement/decision.py (5 errors)
- line 94: `Unsupported operand types for > ("int" and "None")  [operator]`
- line 99: `Argument 1 to "isfinite" has incompatible type "float | None"; expected "SupportsFloat | SupportsIndex"  [arg-type]`
- line 101: `Unsupported operand types for < ("float" and "None")  [operator]`
- line 101: `Value of type variable "SupportsRichComparisonT" of "max" cannot be "float | None"  [type-var]`
- line 103: `Argument 1 to "sum" has incompatible type "tuple[float | None, float | None, float | None, float | None, float | None]"; expected "Iterable[bool]"  [arg-type]`

### pheno/preservation_acceptance.py (2 errors)
- line 137: `Argument 2 to "_immutable_report_path" has incompatible type "Any | None"; expected "str"  [arg-type]`
- line 223: `Argument 1 to "PureWindowsPath" has incompatible type "Any | None"; expected "str | PathLike[str]"  [arg-type]`

### pheno/preservation_evidence_closure.py (4 errors)
- line 97: `Incompatible types in assignment (expression has type "dict[str, Any] | None", variable has type "dict[str, Any]")  [assignment]`
- line 109: `Incompatible types in assignment (expression has type "dict[str, Any] | None", variable has type "dict[str, Any]")  [assignment]`
- line 129: `Incompatible types in assignment (expression has type "dict[str, Any] | None", variable has type "dict[str, Any]")  [assignment]`
- line 165: `Argument 3 to "_generation_binding" has incompatible type "Any | None"; expected "str"  [arg-type]`

### pheno/preservation_readiness_status.py (1 errors)
- line 17: `Argument 1 to "validate" has incompatible type "Mapping[str, Any]"; expected "dict[str, Any]"  [arg-type]`

### pheno/preservation.py (29 errors)
- line 125: `Incompatible types in assignment (expression has type "tuple[Path, ...]", variable has type "tuple[Path, Path]")  [assignment]`
- line 196: `"object" has no attribute "replace"  [attr-defined]`
- line 197: `"object" has no attribute "replace"  [attr-defined]`
- line 214: `"object" has no attribute "get"  [attr-defined]`
- line 217: `"object" has no attribute "get"  [attr-defined]`
- line 615: `"object" has no attribute "values"  [attr-defined]`
- line 714: `No overload variant of "int" matches argument type "object"  [call-overload]`
- line 824: `"object" has no attribute "__iter__"; maybe "__dir__" or "__str__"? (not iterable)  [attr-defined]`
- line 826: `Value of type "object" is not indexable  [index]`
- line 827: `Argument "control_directory" to "build_preservation_acceptance" has incompatible type "object"; expected "str"  [arg-type]`
- line 828: `Argument "evaluated_at_utc" to "build_preservation_acceptance" has incompatible type "object"; expected "str"  [arg-type]`
- line 845: `Value of type "object" is not indexable  [index]`
- line 852: `Value of type "object" is not indexable  [index]`
- line 853: `Value of type "object" is not indexable  [index]`
- line 855: `Value of type "object" is not indexable  [index]`
- line 859: `"object" has no attribute "replace"  [attr-defined]`
- line 860: `"object" has no attribute "replace"  [attr-defined]`
- line 861: `Argument 1 to "strptime" of "datetime" has incompatible type "object"; expected "str"  [arg-type]`
- line 864: `"object" has no attribute "replace"  [attr-defined]`
- line 865: `"object" has no attribute "replace"  [attr-defined]`
- line 868: `"object" has no attribute "replace"  [attr-defined]`
- line 872: `"object" has no attribute "replace"  [attr-defined]`
- line 873: `"object" has no attribute "replace"  [attr-defined]`
- line 918: `Incompatible types in assignment (expression has type "str", variable has type "Path")  [assignment]`
- line 919: `Unsupported operand types for <= ("Path" and "str")  [operator]`
- line 920: `Incompatible types in assignment (expression has type "Path", variable has type "str | None")  [assignment]`
- line 997: `Value of type "object" is not indexable  [index]`
- line 1001: `Value of type "object" is not indexable  [index]`
- line 1007: `Value of type "object" is not indexable  [index]`

### pheno/reconciliation_inventory.py (2 errors)
- line 232: `Unsupported operand types for < ("int" and "None")  [operator]`
- line 234: `Unsupported operand types for + ("int" and "None")  [operator]`

### pheno/runtime_admission_artifact.py (1 errors)
- line 12: `Module "pheno.runtime_admission" has no attribute "SCHEMA"  [attr-defined]`

### pheno/runtime_admission_v2_canonical.py (2 errors)
- line 11: `Module "pheno.runtime_admission" has no attribute "AS_OF"  [attr-defined]`
- line 11: `Module "pheno.runtime_admission" has no attribute "build_runtime_admission"; maybe "validate_runtime_admission"?  [attr-defined]`

### pheno/tbench_execution_closure.py (3 errors)
- line 96: `Item "None" of "Any | None" has no attribute "__iter__" (not iterable)  [union-attr]`
- line 147: `Value of type variable "SupportsRichComparisonT" of "sorted" cannot be "Any | None"  [type-var]`
- line 150: `Item "None" of "dict[str, Any] | None" has no attribute "get"  [union-attr]`

### pheno/tiered_memory/capture.py (3 errors)
- line 106: `Argument "size_bytes" to "TransferSample" has incompatible type "Any | None"; expected "int"  [arg-type]`
- line 107: `Unsupported operand types for / ("None" and "int")  [operator]`
- line 108: `Argument "repetition" to "TransferSample" has incompatible type "Any | None"; expected "int"  [arg-type]`

### pheno/tokenizer_interface_manifest.py (1 errors)
- line 138: `Need type annotation for "blockers" (hint: "blockers: list[<type>] = ...")  [var-annotated]`

### pheno/trial_generation.py (3 errors)
- line 78: `Incompatible types in assignment (expression has type "list[Never]", variable has type "set[str | Any]")  [assignment]`
- line 81: `"set[Any]" has no attribute "append"  [attr-defined]`
- line 84: `"set[Any]" has no attribute "sort"  [attr-defined]`

### pheno/trial_v7_readiness.py (1 errors)
- line 80: `Need type annotation for "blockers" (hint: "blockers: list[<type>] = ...")  [var-annotated]`
