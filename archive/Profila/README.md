# Complete Profiler System

## All-in-One Profiling

```bash
cd profiler

# Quick start
./profiler.sh help

# Run all profilers
./profiler.sh all codex

# Individual profilers
./profiler.sh quick codex       # Quick metrics
./profiler.sh network codex     # Network analysis  
./profiler.sh disk codex        # Disk I/O
./profiler.sh audit codex      # Full system audit
./profiler.sh complexity . rust  # Code complexity
```

## Profiler Commands

| Command | Output |
|---------|--------|
| `quick` | RSS, CPU, Threads, FDs, Network |
| `full` | All system metrics |
| `network` | Connections, bandwidth |
| `disk` | I/O rates, file usage |
| `audit` | Complete system audit |
| `complexity` | Space/time analysis |
| `continuous` | Live CSV + charts |
| `all` | Run everything |

## Tools

### System Profiling
- **all_metrics.sh** - Core metrics (memory, CPU, FDs)
- **full_system_audit.sh** - Complete audit
- **continuous_profiler.py** - Live monitoring

### Resource Profiling
- **network_profiler.sh** - Network I/O
- **disk_profiler.sh** - Disk I/O
- **complexity_analyzer.py** - Code complexity

### Analysis
- **generate_charts.py** - Visual charts from CSV

## Usage

```bash
# Quick profile
./profiler.sh quick codex

# Full audit
./profiler.sh audit codex reports/

# Network only
./profiler.sh network thegent

# Disk I/O
./profiler.sh disk codex

# Code complexity (Rust)
./profiler.sh complexity . rust

# Code complexity (Python)  
./profiler.sh complexity . python

# Continuous monitoring
python3 bin/continuous_profiler.py codex
```

## Output

```
reports/
├── all_metrics_YYYYMMDD_HHMMSS.txt
├── network_YYYYMMDD_HHMMSS.txt
├── disk_YYYYMMDD_HHMMSS.txt
├── full_audit_YYYYMMDD_HHMMSS.txt
└── codex_metrics_YYYYMMDD_HHMMSS.csv (continuous)
```

## Metrics Tracked

### Memory
- RSS, VMS, VmPeak, VmData, VmStk, VmExe, VmLib
- Memory maps, shared/private

### CPU
- CPU %, threads, context switches
- Per-thread CPU time

### Files
- FD count, types (pipe, socket, anon)
- Open files, CWD, root

### Network
- TCP/UDP connections
- Bandwidth (rx/tx)

### Disk
- Read/write bytes
- I/O rates

### Complexity (code)
- Cyclomatic complexity
- Recursion detection
- Loop/conditional counts

## Comparison Targets

### Codex (Current)
| Metric | Value |
|--------|-------|
| RSS | ~150MB idle |
| CPU | 0.1% idle |
| FDs | 25 |
| Growth | 50MB/hr |

### Our Target
| Metric | Value |
|--------|-------|
| RSS | <20MB |
| CPU | 0% idle |
| FDs | <10 |
| Growth | 0 |
