# Functional Requirements — profiler

**Total FRs:** 18
**Implementation Status:** IN PROGRESS
**Last Updated:** 2026-03-26

Traces to: `PRD.md` epics E1-E5.

---

## FR-MET: System Metrics Collection

- **FR-MET-001:** The system SHALL accept a process name as the primary target argument and resolve it to a PID via `pgrep`. Traces to: E1.1.
- **FR-MET-002:** The system SHALL exit with a non-zero status code and print an error message to stderr when the target process is not found. Traces to: E1.1.
- **FR-MET-003:** The quick metrics command SHALL report RSS (MB), VMS (MB), CPU%, thread count, and open file-descriptor count. Traces to: E1.1.
- **FR-MET-004:** The full metrics command SHALL include memory-map detail (`/proc/<pid>/smaps` on Linux, `vmmap` on macOS) and kernel CPU scheduling stats. Traces to: E1.2.
- **FR-MET-005:** All metric report files SHALL be written to the configured output directory with filename pattern `<type>_<YYYYMMDD_HHMMSS>.txt`. Traces to: E1.1, E1.2, E1.3, E1.4.

---

## FR-NET: Network Profiling

- **FR-NET-001:** The network profiler SHALL list all open TCP and UDP connections for the target PID. Traces to: E1.3.
- **FR-NET-002:** The network profiler SHALL report per-network-interface byte counters (RX/TX). Traces to: E1.3.

---

## FR-DSK: Disk Profiling

- **FR-DSK-001:** The disk profiler SHALL report read and write throughput (MB/s) for the target PID over a one-second sampling window. Traces to: E1.4.
- **FR-DSK-002:** The disk profiler SHALL report the count of open file handles for the target PID. Traces to: E1.4.

---

## FR-AUD: System Audit

- **FR-AUD-001:** The `audit` command SHALL invoke `all_metrics.sh`, `network_profiler.sh`, and `disk_profiler.sh` in sequence and produce a single consolidated report file. Traces to: E1.5.
- **FR-AUD-002:** The `all` command SHALL invoke network and disk profilers in addition to the full metrics script and print a completion message to stdout. Traces to: E1.5.

---

## FR-CPX: Code Complexity Analysis

- **FR-CPX-001:** The complexity analyzer SHALL parse Python source files using the `ast` module and compute per-function cyclomatic complexity. Traces to: E2.1.
- **FR-CPX-002:** The complexity analyzer SHALL flag any function whose cyclomatic complexity exceeds 10 or whose loop/conditional nesting implies cognitive complexity exceeding 15 as `[HIGH]`. Traces to: E2.1.
- **FR-CPX-003:** The complexity analyzer SHALL exit with status code 1 if any `[HIGH]` function is found; exit 0 otherwise. Traces to: E2.1.
- **FR-CPX-004:** The complexity analyzer SHALL accept a `--lang` flag supporting `python`, `rust`, `go`, and `typescript`, applying regex heuristics for non-Python languages. Traces to: E2.2.

---

## FR-CNT: Continuous Monitoring

- **FR-CNT-001:** The continuous profiler SHALL write a CSV with header row `timestamp,pid,rss_mb,vms_mb,cpu_pct,threads,fds` to `reports/continuous_<target>_<timestamp>.csv`. Traces to: E3.1.
- **FR-CNT-002:** The continuous profiler SHALL append one data row every 5 seconds (default; configurable) until SIGINT is received. Traces to: E3.1.
- **FR-CNT-003:** Upon SIGINT the continuous profiler SHALL flush the output file and exit cleanly without raising an unhandled exception. Traces to: E3.1.

---

## FR-CHT: Chart Generation

- **FR-CHT-001:** The chart generator SHALL accept one or more CSV file paths (glob-expanded by the shell) and produce one PNG per input file. Traces to: E4.1.
- **FR-CHT-002:** Each chart SHALL contain separate line series for RSS (MB), CPU%, and thread count over the timestamp axis. Traces to: E4.1.
- **FR-CHT-003:** The chart generator SHALL depend only on `matplotlib` from the standard scientific Python stack and SHALL NOT require additional third-party libraries. Traces to: E4.1.
