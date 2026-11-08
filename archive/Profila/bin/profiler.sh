#!/bin/bash
# profiler.sh - Main profiling script for Codex and thegent

set -e

TARGET="${1:-codex}"
MODE="${2:-quick}"  # quick, full, memory, cpu, latency

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILER_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORTS_DIR="$PROFILER_DIR/reports"

mkdir -p "$REPORTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORTS_DIR/${TARGET}_${MODE}_${TIMESTAMP}.txt"

log() { echo "[$(date +%H:%M:%S)] $1"; }

log "=== Profiling $TARGET (mode: $MODE) ==="

# Get PID if profiling running process
get_pid() {
    if [ "$TARGET" = "codex" ]; then
        pgrep -f "codex" | head -1
    elif [ "$TARGET" = "thegent" ]; then
        pgrep -f "thegent" | head -1
    else
        echo "$TARGET"
    fi
}

profile_system() {
    local pid="$1"
    log "System metrics for PID: $pid"
    
    # Memory
    local rss=$(ps -o rss= -p "$pid" 2>/dev/null || echo "0")
    local vms=$(ps -o vsz= -p "$pid" 2>/dev/null || echo "0")
    local mem_mb=$((rss / 1024))
    
    # CPU
    local cpu=$(ps -o %cpu= -p "$pid" 2>/dev/null || echo "0")
    
    # Threads
    local threads=$(ps -o nlwp= -p "$pid" 2>/dev/null || echo "0")
    
    # FDs
    local fds=$(ls /proc/$pid/fd 2>/dev/null | wc -l || echo "0")
    
    # Network
    local net=$(lsof -i -a -p "$pid" 2>/dev/null | grep -v COMMAND | wc -l || echo "0")
    
    echo "  RSS: ${mem_mb}MB"
    echo "  VMS: ${vms}KB"
    echo "  CPU: ${cpu}%"
    echo "  Threads: ${threads}"
    echo "  FDs: ${fds}"
    echo "  Network: ${net} connections"
}

case "$MODE" in
    quick)
        log "Quick system profile..."
        PID=$(get_pid)
        if [ -n "$PID" ]; then
            profile_system "$PID"
        else
            log "Target not running. Starting quick profile..."
            # Quick flamegraph if we have a binary
            if command -v cargo-flamegraph &> /dev/null; then
                cargo flamegraph --title "quick_profile" 2>/dev/null || true
            fi
        fi
        ;;
        
    cpu)
        log "CPU profiling (30s)..."
        PID=$(get_pid)
        if [ -n "$PID" ]; then
            # Use perf or samply
            if command -v perf &> /dev/null; then
                sudo perf record -g -p "$PID" -- sleep 30
                sudo perf report > "$REPORT_FILE"
            elif command -v samply &> /dev/null; then
                samply record -p "$PID" -- sleep 30 2>/dev/null || true
            else
                log "No CPU profiler available"
            fi
        else
            log "Target not running"
        fi
        ;;
        
    memory)
        log "Memory profiling..."
        PID=$(get_pid)
        if [ -n "$PID" ]; then
            # Heaptrack if available
            if command -v heaptrack &> /dev/null; then
                heaptrack -p "$PID" "$REPORT_FILE" 2>/dev/null || true
            fi
        else
            log "Target not running"
        fi
        ;;
        
    latency)
        log "Latency measurement..."
        # Measure tool execution time
        if [ "$TARGET" = "codex" ]; then
            time codex -p "hello" 2>&1 | head -5
        fi
        ;;
        
    full)
        log "Full profiling suite..."
        
        PID=$(get_pid)
        
        # System metrics
        if [ -n "$PID" ]; then
            profile_system "$PID"
        fi
        
        # CPU flamegraph
        if command -v cargo-flamegraph &> /dev/null; then
            log "Generating CPU flamegraph..."
            cargo flamegraph --title "full_profile" 2>/dev/null || true
        fi
        
        # Latency test
        log "Latency test..."
        if [ "$TARGET" = "codex" ]; then
            for i in 1 2 3; do
                start=$(date +%s%N)
                codex -p "hi" 2>/dev/null
                end=$(date +%s%N)
                echo "  Run $i: $(( (end - start) / 1000000 ))ms"
            done
        fi
        
        log "Full profile complete"
        ;;
        
    continuous)
        log "Continuous monitoring (Ctrl+C to stop)..."
        while true; do
            PID=$(get_pid)
            if [ -n "$PID" ]; then
                ts=$(date +%H:%M:%S)
                rss=$(ps -o rss= -p "$PID" 2>/dev/null || echo "0")
                cpu=$(ps -o %cpu= -p "$PID" 2>/dev/null || echo "0")
                echo "$ts,$rss,$cpu" >> "$REPORTS_DIR/${TARGET}_continuous_${TIMESTAMP}.csv"
            fi
            sleep 10
        done
        ;;
        
    *)
        log "Unknown mode: $MODE"
        echo "Usage: $0 <target> <mode>"
        echo "  target: codex, thegent, or PID"
        echo "  mode:  quick, cpu, memory, latency, full, continuous"
        ;;
esac

log "Report saved to: $REPORT_FILE"
