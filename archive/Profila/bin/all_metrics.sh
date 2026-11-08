#!/bin/bash
# all_metrics.sh - Complete system profiling

TARGET="${1:-codex}"
OUTPUT_DIR="${2:-reports}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PID=$(pgrep -f "$TARGET" | head -1)

echo "=== COMPLETE METRICS: $TARGET ==="
echo "Timestamp: $(date)"
echo "PID: $PID"
echo ""

# Create combined report
{
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║            COMPLETE SYSTEM PROFILE: $TARGET                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 1. MEMORY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. MEMORY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    RSS=$(ps -o rss= -p "$PID" 2>/dev/null || echo 0)
    VMS=$(ps -o vsz= -p "$PID" 2>/dev/null || echo 0)
    MEM=$(ps -o %mem= -p "$PID" 2>/dev/null || echo 0)
    
    echo "  RSS (Resident): $((RSS / 1024)) MB"
    echo "  VMS (Virtual): $((VMS / 1024)) MB"
    echo "  Memory %: $MEM%"
    
    echo ""
    echo "  --- Memory Maps ---"
    cat /proc/$PID/smaps 2>/dev/null | head -30 || echo "N/A"
    
    echo ""
    echo "  --- Memory Details ---"
    cat /proc/$PID/status 2>/dev/null | grep -E "^(VmSize|VmRSS|VmData|VmStk|VmExe|VmLib|VmPTE)" || echo "N/A"
else
    echo "  Process not running"
fi
echo ""

# 2. CPU
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. CPU"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    CPU=$(ps -o %cpu= -p "$PID" 2>/dev/null || echo 0)
    THREADS=$(ps -o nlwp= -p "$PID" 2>/dev/null || echo 0)
    
    echo "  CPU %: $CPU%"
    echo "  Threads: $THREADS"
    
    echo ""
    echo "  --- Top CPU Threads ---"
    ps -Lo pid,tid,pcpu,comm -p "$PID" 2>/dev/null | head -10 || echo "N/A"
    
    echo ""
    echo "  --- CPU Time ---"
    cat /proc/$PID/stat 2>/dev/null | awk '{print "  User: " $14 " jiffies"}'
    cat /proc/$PID/stat 2>/dev/null | awk '{print "  System: " $15 " jiffies"}'
else
    echo "  Process not running"
fi
echo ""

# 3. FILES
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. FILES & DESCRIPTORS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    FD_COUNT=$(ls /proc/$PID/fd 2>/dev/null | wc -l)
    echo "  Total FDs: $FD_COUNT"
    
    echo ""
    echo "  --- FD Types ---"
    ls -l /proc/$PID/fd 2>/dev/null | awk '{print $10}' | sort | uniq -c | sort -rn
    
    echo ""
    echo "  --- Open Files ---"
    ls -la /proc/$PID/fd 2>/dev/null | head -20
    
    echo ""
    echo "  --- CWD ---"
    readlink /proc/$PID/cwd 2>/dev/null || echo "N/A"
    
    echo ""
    echo "  --- Root ---"
    readlink /proc/$PID/root 2>/dev/null || echo "N/A"
fi
echo ""

# 4. NETWORK
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. NETWORK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    NET_COUNT=$(lsof -i -a -p "$PID" 2>/dev/null | grep -v COMMAND | wc -l)
    echo "  Network connections: $NET_COUNT"
    
    echo ""
    echo "  --- Connections ---"
    lsof -i -a -p "$PID" 2>/dev/null | head -10
    
    echo ""
    echo "  --- Socket Stats ---"
    ss -tnp 2>/dev/null | grep "$PID" || echo "  No TCP"
    
    echo ""
    echo "  --- UDP Stats ---"
    ss -unp 2>/dev/null | grep "$PID" || echo "  No UDP"
fi
echo ""

# 5. DISK I/O
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. DISK I/O"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ] && [ -f /proc/$PID/io ]; then
    echo "  --- I/O Stats ---"
    cat /proc/$PID/io 2>/dev/null | grep -E "^(read_bytes|write_bytes|cancelled_write_bytes)"
fi
echo ""

# 6. CONTEXT
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. CONTEXT SWITCHES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    echo "  --- Switches ---"
    cat /proc/$PID/status 2>/dev/null | grep -E "^(voluntary_ctxt_switches|nonvoluntary_ctxt_switches)" || echo "N/A"
fi
echo ""

# 7. SIGNALS
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. SIGNALS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    echo "  --- Pending ---"
    cat /proc/$PID/status 2>/dev/null | grep SigPnd || echo "N/A"
    
    echo "  --- Blocked ---"
    cat /proc/$PID/status 2>/dev/null | grep SigBlk || echo "N/A"
fi
echo ""

# 8. LIMITS
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. RESOURCE LIMITS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    cat /proc/$PID/limits 2>/dev/null || echo "N/A"
fi
echo ""

# 9. ENVIRONMENT
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. ENVIRONMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    echo "  --- Environment ---"
    cat /proc/$PID/environ 2>/dev/null | tr '\0' '\n' | head -20
fi
echo ""

# 10. CMDLINE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "10. COMMAND LINE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$PID" ]; then
    cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' '
    echo ""
    echo "  --- Executable ---"
    readlink /proc/$PID/exe 2>/dev/null || echo "N/A"
fi
echo ""

} > "$OUTPUT_DIR/all_metrics_${TIMESTAMP}.txt"

echo "Complete profile saved to: $OUTPUT_DIR/all_metrics_${TIMESTAMP}.txt"
echo ""
echo "Quick Summary:"
echo "  Memory: $((RSS / 1024)) MB"
echo "  Threads: $THREADS"
echo "  FDs: $FD_COUNT"
echo "  Network: $NET_COUNT"
