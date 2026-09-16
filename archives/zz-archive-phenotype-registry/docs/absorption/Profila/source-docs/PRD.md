# Product Requirements Document — profiler

**Status:** ACTIVE
**Owner:** Phenotype Engineering
**Last Updated:** 2026-03-26

---

## Overview

`profiler` is a unified shell-and-Python profiling toolkit for the Phenotype agent ecosystem. It collects system-level resource metrics (memory, CPU, network, disk I/O), measures code complexity, generates machine-readable CSV output, and produces visual charts — all from a single entry-point script targeting a named process or codebase.

Primary consumers: agent performance audits on `codex`, `thegent`, `heliosCLI`, and similar Phenotype processes running on macOS/Linux developer machines and CI runners.

---

## Epics

### E1: System Resource Profiling

**Goal:** Snapshot and continuously monitor OS-level resource usage for a running process.

#### E1.1: Quick Metrics Snapshot
**As** a developer, **I want** a one-shot snapshot of memory, CPU, thread count, and file-descriptor usage for a named process **so that** I can assess resource health without writing custom scripts.

**Acceptance Criteria:**
- `./profiler.sh quick <target>` prints RSS (MB), VMS (MB), CPU%, thread count, and FD count.
- Output is human-readable to stdout and simultaneously written to `reports/all_metrics_<timestamp>.txt`.
- Exits non-zero if the named process is not found.

#### E1.2: Full Metrics Report
**As** a developer, **I want** a detailed report including memory maps, CPU scheduling stats, and kernel-level thread breakdown **so that** I can diagnose regressions in agent memory layout.

**Acceptance Criteria:**
- `./profiler.sh full <target>` runs `all_metrics.sh` and captures `/proc/<pid>/smaps`, `/proc/<pid>/status`, and top-thread breakdown on Linux; `vm_stat` and `top` on macOS.
- Report file written to `reports/all_metrics_<timestamp>.txt`.

#### E1.3: Network Profiling
**As** a developer, **I want** a network I/O snapshot (open connections, bandwidth usage) **so that** I can identify agents that leak sockets or generate unexpected traffic.

**Acceptance Criteria:**
- `./profiler.sh network <target>` runs `network_profiler.sh`.
- Output includes active TCP/UDP connections and per-interface byte counts.
- Written to `reports/network_<timestamp>.txt`.

#### E1.4: Disk I/O Profiling
**As** a developer, **I want** disk read/write rate metrics for a target process **so that** I can catch agents with pathological file churn.

**Acceptance Criteria:**
- `./profiler.sh disk <target>` runs `disk_profiler.sh`.
- Output includes read/write MB/s and file-open count.
- Written to `reports/disk_<timestamp>.txt`.

#### E1.5: Full System Audit
**As** a QA engineer, **I want** a single command that runs all resource profilers **so that** I can collect a complete baseline in one invocation.

**Acceptance Criteria:**
- `./profiler.sh audit <target>` runs `full_system_audit.sh`.
- Produces a consolidated report aggregating memory, CPU, network, and disk sections.

---

### E2: Code Complexity Analysis

**Goal:** Measure cyclomatic and cognitive complexity of Phenotype codebases to enforce the complexity ratchet.

#### E2.1: Python Complexity Analysis
**As** a developer, **I want** per-function cyclomatic complexity scores for a Python codebase **so that** I can identify functions exceeding the 10-cyclomatic / 15-cognitive limits.

**Acceptance Criteria:**
- `./profiler.sh complexity <dir> python` invokes `bin/complexity_analyzer.py`.
- Output lists each function with: file, line, complexity score, cyclomatic score, loop count, recursion flag.
- Functions exceeding thresholds (cyclomatic > 10, cognitive > 15) are flagged `[HIGH]`.
- Exit code 1 if any function is flagged HIGH.

#### E2.2: Multi-Language Complexity (Rust, Go, TypeScript)
**As** a developer, **I want** complexity analysis for Rust, Go, and TypeScript files **so that** the ratchet applies uniformly across Phenotype's polyglot repos.

**Acceptance Criteria:**
- `bin/complexity_analyzer.py` accepts `--lang rust|go|typescript` flag.
- Uses regex-based heuristics for non-Python files: function definitions, branching keywords, loop constructs.
- Output format matches Python output.

---

### E3: Continuous Monitoring

**Goal:** Stream live metrics to CSV for time-series analysis.

#### E3.1: Continuous CSV Streaming
**As** a developer, **I want** a live monitoring mode that writes resource metrics to a CSV file every N seconds **so that** I can observe agent behavior over a full task run.

**Acceptance Criteria:**
- `./profiler.sh continuous <target>` runs `bin/continuous_profiler.py`.
- Appends one row per interval (default: 5 s) with columns: `timestamp, pid, rss_mb, vms_mb, cpu_pct, threads, fds`.
- Writes to `reports/continuous_<target>_<timestamp>.csv`.
- Ctrl-C cleanly flushes and exits.

---

### E4: Chart Generation

**Goal:** Convert CSV reports to visual charts for presentation and regression tracking.

#### E4.1: Chart Generation from CSV
**As** a developer, **I want** to generate line charts from continuous profiler CSV output **so that** I can include resource trends in pull-request comments and reports.

**Acceptance Criteria:**
- `./profiler.sh charts <csv_glob>` runs `bin/generate_charts.py`.
- Produces one PNG per CSV file in the same directory as the CSV.
- Charts include: RSS over time, CPU% over time, thread count over time.
- Requires only `matplotlib` (no additional deps).

---

### E5: Build Instrumentation

**Goal:** Compile and launch binaries with profiling flags enabled.

#### E5.1: Instrumented Build
**As** a developer, **I want** to compile a Rust or Go binary with debug symbols and profiling flags before running the profiler **so that** perf profiles include symbol resolution.

**Acceptance Criteria:**
- `bin/build_for_profiling.sh <target>` builds the binary with `--debug` (Rust) or `-gcflags="-N -l"` (Go).
- Prints the resulting binary path.

---

## Success Criteria

- All eight `profiler.sh` subcommands (`quick`, `full`, `network`, `disk`, `audit`, `complexity`, `continuous`, `all`, `charts`) execute without error on macOS and Linux.
- `complexity` subcommand exits 1 when any function exceeds configured thresholds.
- Continuous mode produces a valid, header-first CSV on Ctrl-C interrupt.
- Chart generation produces at least one PNG per CSV input.
- All report files are timestamped and written to the configured output directory.

---

## Out of Scope

- Web dashboard or UI for viewing reports.
- Distributed tracing or OpenTelemetry integration.
- Windows support.
- Agent auto-remediation based on profiler findings.
