#!/bin/bash
# disk_profiler.sh - Disk I/O profiling

TARGET="${1:-codex}"
OUTPUT_DIR="${2:-reports}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Disk I/O Profiling: $TARGET ==="

PID=$(pgrep -f "$TARGET" | head -1)

if [ -z "$PID" ]; then
    echo "Process not running."
    exit 1
fi

echo "PID: $PID"

{
echo "=== FILE DESCRIPTORS ==="
echo "--- FD Count ---"
echo "Total: $(ls /proc/$PID/fd 2>/dev/null | wc -l)"

echo ""
echo "--- FD Types ---"
ls -l /proc/$PID/fd 2>/dev/null | awk '{print $10}' | sort | uniq -c | sort -rn

echo ""
echo "--- Open Files ---"
ls -la /proc/$PID/fd 2>/dev/null

echo ""
echo "=== DISK I/O (30s sample) ==="
if command -v iotop &> /dev/null; then
    sudo iotop -b -o -p $PID 2>/dev/null | head -20 || echo "Need root"
elif [ -f /proc/$PID/io ]; then
    echo "--- I/O Stats ---"
    cat /proc/$PID/io
    
    # Sample for 30s
    R1=$(grep read_bytes /proc/$PID/io 2>/dev/null | awk '{print $2}')
    W1=$(grep write_bytes /proc/$PID/io 2>/dev/null | awk '{print $2}')
    sleep 30
    R2=$(grep read_bytes /proc/$PID/io 2>/dev/null | awk '{print $2}')
    W2=$(grep write_bytes /proc/$PID/io 2>/dev/null | awk '{print $2}')
    
    echo ""
    echo "--- I/O Rate (30s) ---"
    echo "Read:  $(( (R2 - R1) / 30 )) KB/s"
    echo "Write: $(( (W2 - W1) / 30 )) KB/s"
else
    echo "Cannot access /proc/$PID/io"
fi

echo ""
echo "=== DISK USAGE ==="
echo "--- Workspace Size ---"
du -sh ~ 2>/dev/null || echo "N/A"

echo ""
echo "--- Codex Data ---"
du -sh ~/.codex 2>/dev/null || echo "N/A"

echo ""
echo "--- Logs ---"
du -sh ~/.codex/logs 2>/dev/null || echo "N/A"

echo ""
echo "--- Database ---"
du -sh ~/.codex/data.db 2>/dev/null || echo "N/A"

} > "$OUTPUT_DIR/disk_${TIMESTAMP}.txt"

echo "Disk profile saved to: $OUTPUT_DIR/disk_${TIMESTAMP}.txt"
