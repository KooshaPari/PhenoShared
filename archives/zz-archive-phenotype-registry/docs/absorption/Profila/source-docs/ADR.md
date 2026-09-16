# Architecture Decision Records — profiler

**Last Updated:** 2026-03-26

---

## ADR-001: Bash Entry Point with Python Subcommand Delegation

**Status:** Accepted
**Context:** The profiler needs to support both low-level OS metrics (best accessed via shell tools like `ps`, `lsof`, `netstat`) and higher-level analysis (code complexity, chart generation) that benefits from a rich standard library.
**Decision:** Use a single Bash entry-point script (`profiler.sh`) that dispatches subcommands to either pure-Bash scripts (`bin/*.sh`) for OS metrics or Python scripts (`bin/*.py`) for analysis and visualization.
**Alternatives Considered:**
- Pure Python CLI (e.g., `typer`): would require Python for all invocations, including fast one-shot OS queries where shell tools are faster and more portable.
- Pure Bash: inadequate for AST-based complexity analysis and matplotlib charting.
**Consequences:** Simple extension (add a new subcommand branch + script); requires both Bash and Python 3 on the host.

---

## ADR-002: Timestamped Report Files in a Flat Output Directory

**Status:** Accepted
**Context:** Multiple profiler runs against the same target must not overwrite previous results; reports must be sortable chronologically.
**Decision:** All output files use the pattern `<type>_<YYYYMMDD_HHMMSS>.<ext>` written to a user-configurable output directory (default: `reports/`).
**Alternatives Considered:**
- Named by target only: previous runs silently overwritten.
- Subdirectory per run: more complex tooling needed to find latest report.
**Consequences:** Reports accumulate and must be manually pruned; directory listing is naturally sorted by time.

---

## ADR-003: Python ast Module for Complexity Analysis

**Status:** Accepted
**Context:** Cyclomatic complexity analysis requires accurate parsing of Python control flow. String-matching heuristics miss edge cases (nested comprehensions, walrus operator, match/case).
**Decision:** `bin/complexity_analyzer.py` uses the stdlib `ast` module to walk the AST and count branch nodes (`If`, `For`, `While`, `ExceptHandler`, `With`, `BoolOp`, etc.) per function definition.
**Alternatives Considered:**
- `radon` library: more accurate McCabe score but adds a third-party dependency.
- `lizard` library: multi-language but third-party.
**Decision Rationale:** Zero external dependencies for the Python scripts; `ast` is sufficient for the threshold enforcement use case (flag > 10 cyclomatic). Third-party tools are acceptable as optional enhancements.
**Consequences:** Non-Python language support (Rust, Go, TypeScript) falls back to regex heuristics, which are less accurate but dependency-free.

---

## ADR-004: CSV as the Continuous Monitoring Wire Format

**Status:** Accepted
**Context:** Continuous profiler output must be readable by humans (for spot checks), machine-parseable (for chart generation), and appendable without locking.
**Decision:** `bin/continuous_profiler.py` appends CSV rows to a file opened in append mode. Header is written once at startup.
**Alternatives Considered:**
- JSON Lines: more flexible schema but verbose and harder to inspect in a terminal.
- SQLite: supports queries but adds startup overhead and a lock file.
- InfluxDB line protocol: overkill for local developer profiling.
**Consequences:** CSV is the lowest common denominator; downstream tools (`generate_charts.py`, spreadsheets, pandas) consume it without conversion.

---

## ADR-005: matplotlib-Only Chart Generation

**Status:** Accepted
**Context:** Chart generation must work in any Python environment without requiring a JavaScript runtime, a headless browser, or a plotting server.
**Decision:** `bin/generate_charts.py` uses only `matplotlib` (backend: `Agg` for headless PNG output) and the stdlib `csv` module.
**Alternatives Considered:**
- `plotly`: richer interactive HTML but requires a JS-capable viewer.
- `gnuplot`: no Python dependency but requires a separate binary install.
- `altair` / `vega-lite`: elegant API but heavier dependency chain.
**Consequences:** Output is static PNGs suitable for embedding in GitHub PR comments, CI artifacts, and markdown reports.

---

## ADR-006: `pgrep` for PID Resolution

**Status:** Accepted
**Context:** The profiler is invoked with a human-readable process name (e.g., `codex`, `thegent`) rather than a raw PID. Resolving the name to a PID must be consistent across macOS and Linux.
**Decision:** All Bash scripts use `pgrep -f "$TARGET" | head -1` for PID resolution. Scripts print a warning and degrade gracefully (outputting system-wide stats) when the process is not running.
**Alternatives Considered:**
- `pidof`: Linux-only, not available on macOS.
- `/proc` scan: Linux-only.
- Require the caller to pass a PID: worse UX for the common case.
**Consequences:** `pgrep` is available on both macOS (via proctools) and Linux (via procps). Multi-process matches take only the first PID, which may be unexpected for multi-worker processes.
