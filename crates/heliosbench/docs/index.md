# HeliosBench

HeliosBench is a benchmark harness for CLI agents and terminal workflows. It
measures runtime behavior around latency, CPU, memory, file descriptors, threads,
and leak patterns while running Terminal-Bench-style tasks.

## What It Proves

- Agent CLI startup and task latency.
- Resource usage across repeated benchmark runs.
- Memory and file descriptor leak pressure.
- Side-by-side behavior between two binaries.
- JSON output that can be consumed by CI or local analysis scripts.

## Quick Start

```bash
pip install -e .
helios-bench tasks
helios-bench run --binary /path/to/codex --task palindrome --runs 5
```

Use the repo Taskfile for local checks:

```bash
task test
task lint
task build
```

## Project Surfaces

- [Install and run guide](./guide.md)
- [Benchmark task catalog](./tasks.md)
- [Source repository](https://github.com/KooshaPari/heliosBench)
