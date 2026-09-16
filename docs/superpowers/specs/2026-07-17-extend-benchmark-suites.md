# Benchmark Suite Extension Plan (2026-07-17)

**Goal:** Add 6 new benchmark suites + fix existing broken suites + run a 5–10
minute end-to-end matrix against MiniMax-M3 via `forge -p`.

---

## 1. Existing suite audit

| Module | File | Status |
|---|---|---|
| terminal-bench | `terminal_bench.py` | ✅ exists, has timed-out in MiniMax-M3 run |
| deep-swe | `deepswe.py` | ✅ exists, same |
| gpqa-diamond | `gpqa_diamond.py` | ✅ exists |
| mmlu-pro | `mmlu_pro.py` | ✅ exists |
| hle | `hle.py` | ✅ exists |

**Problems found during the MiniMax-M3 run (`bench/results/minimax-m3/matrix.md`):**

1. `hle.py → HLESuite` — `0 results` (broken suite module, error on any call)
2. `perplexity.py → PerplexitySuite` — `0 results` (same, probably seed issue)
3. `terminal-bench / deep-swe / swe-bench-verified` — all time out at 60–120s
   per task because `forge -p` agent overhead dominates (the task runs the *forge
   agent*, which has spinner + reasoning-print + tool-call scaffolding). We need a
   **user-prompt → model-prompt → reply** path that skips the agent or sets a
   tighter timeout.
4. `bfcl-v4 / mt-bench` — skip for now (function-calling + multi-turn not
   compatible with forge's chat-only mode)

## 2. New suites required

| # | Benchmark | Source / Reference | Vendoring approach |
|---|---|---|---|
| 1 | **kernel-bench** (KernelBench) | Stanford ICML 2025 — GPU kernel code gen | Vendored subset (~20 GPU kernel prompts) |
| 2 | **browser-comp** (BrowserComp) | OpenAI — agentic browser task | Vendored subset (~10 web-agent tasks) |
| 3 | **os-world** (OSWorld v1) | Microsoft — desktop OS agent (Ubuntu + Mac) | Vendored subset (~10 OS tasks) |
| 4 | **pinch-bench** | OpenClaw — 53 multi-agent programming tasks | Vendored subset (~15 TDD-style coding tasks) |
| 5 | **arc-agi-2** | ARChitects / Kaggle — grid puzzle reasoning, 2025/2026 edition | Vendored subset (~10 puzzles with 4-shot exemplar each) |
| 6 | **vending-bench-v0** | tiny 2-task benchmark (vending machine + cookie shop) | Vendored both tasks |
| 7 | **startup-bench** | StartupBench July 2026 — founder/startup evaluation | Vendored subset (~10 startup scenarios) |

**Naming convention** (matches existing hyphen pattern):
- `kernel_bench.py` / `KernelBenchSuite` / name=`kernel-bench`
- `browser_comp.py` / `BrowserCompSuite` / name=`browser-comp`
- `osworld.py` / `OSWorldSuite` / name=`os-world`
- `pinch_bench.py` / `PinchBenchSuite` / name=`pinch-bench`
- `arc_agi.py` / `ArcAgiSuite` / name=`arc-agi`
- `vending_bench.py` / `VendingBenchSuite` / name=`vending-bench`
- `startup_bench.py` / `StartupBenchSuite` / name=`startup-bench`

**Template** (from `_stub.py`):
```python
@register
class XxxSuite(BaseSuite):
    name = "xxx-bench"
    domain = TaskDomain.REASONING  # from bench.types
    paper_metrics = {"pass@1", "latency_p50"}
    tasks = [Task(...), ...]

    def subset(self, n: int, seed: int) -> list[Task]:
        return deterministic_subset(self.tasks, n, seed)

    def run_task(self, task: Task, model: str, **kwargs) -> TaskResult:
        messages = [{"role": "user", "content": task.prompt}]
        reply = call_model(model, messages)
        ok = heuristic_judge(task, reply)
        return TaskResult(task_id=task.id, ..., status=TaskStatus.PASS if ok else TaskStatus.FAIL)
```

---

## 3. Implementation order

| Step | What | Est. time |
|---|---|---|
| 1 | Create worktree parallel agents: 3 agents each own 2-3 new suites | 5 min |
| 2 | Fix existing broken suites: hle.py (seed bug), perplexity.py (same) | 2 min |
| 3 | Wire new suite modules into `cli.py` (add to `_ensure_suites_loaded()`) | 1 min |
| 4 | Wire into `run_5min_benchmark.py` (add to import list + `TARGET_SUITES` or `DISABLED_SUITES`) | 1 min |
| 5 | Run all 10+ suites against MiniMax-M3 with n=5, capture matrix | ~250 min (background) |
| 6 | Update `bench/results/qwen-stock-vs-pheno-metal.md` with MiniMax-M3 row | 2 min |
| 7 | Commit + push to origin/main | 1 min |

---

## 4. Task breakdown

### Agent 1 — kernel-bench, arc-agi
- kernel-bench: 20 GPU kernel prompts (CUDA-equivalent in Mojo? Just prompt-text
  with 'write a GPU kernel that ...')
- arc-agi: 10 grid puzzles, each with 4-shot exemplar. Heuristic judge = exact
  output match on the arithmetic solution.

### Agent 2 — browser-comp, os-world
- browser-comp: 10 web-agent scenarios ('search for X on Y', 'compare prices
  of Z'). Heuristic judge = substring match.
- os-world: 10 OS tasks ('create a file at /tmp/...', 'list processes that
  use port ...'). Heuristic judge = keyword match.

### Agent 3 — pinch-bench, vending-bench, startup-bench
- pinch-bench: 15 TDD-style prompts (write tests, then code, then refactor).
  Heuristic judge = has "test_", has "def ", has "assert".
- vending-bench: 2 prompts (vending machine OO design, cookie shop inventory).
  Heuristic judge = has class/object keywords.
- startup-bench: 10 founder scenarios ('write a pitch deck for ...').
  Heuristic judge = has "executive summary" or "market" keywords.
