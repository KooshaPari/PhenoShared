#!/bin/bash
# full_system_audit.sh - Complete system audit with all metrics

TARGET="${1:-codex}"
OUTPUT_DIR="${2:-reports}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PID=$(pgrep -f "$TARGET" | head -1)

echo "=== FULL SYSTEM AUDIT: $TARGET ==="
echo "Timestamp: $(date)"
echo "PID: ${PID:-none}"
echo ""

{
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║              COMPLETE SYSTEM AUDIT: $TARGET                 ║"
    echo "║                    $TIMESTAMP                             ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"

    # ═══════════════════════════════════════════════════════════════
    # 1. CORE METRICS
    # ═══════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "1. CORE METRICS"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        RSS=$(ps -o rss= -p "$PID" 2>/dev/null || echo 0)
        VMS=$(ps -o vsz= -p "$PID" 2>/dev/null || echo 0)
        CPU=$(ps -o %cpu= -p "$PID" 2>/dev/null || echo 0)
        MEM=$(ps -o %mem= -p "$PID" 2>/dev/null || echo 0)
        THREADS=$(ps -o nlwp= -p "$PID" 2>/dev/null || echo 0)
        FDS=$(ls /proc/"$PID"/fd 2>/dev/null | wc -l || echo 0)

        echo "  Process:"
        echo "    RSS:      $((RSS / 1024)) MB"
        echo "    VMS:      $((VMS / 1024)) MB"
        echo "    CPU:      $CPU%"
        echo "    Memory:    $MEM%"
        echo "    Threads:   $THREADS"
        echo "    FDs:      $FDS"
    else
        echo "  [Process not running]"
    fi

    # ═══════════════════════════════════════════════════════════════
    # 2. MEMORY BREAKDOWN
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "2. MEMORY BREAKDOWN"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  VmPeak:    $(grep VmPeak /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmSize:    $(grep VmSize /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmRSS:     $(grep VmRSS /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmData:   $(grep VmData /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmStk:    $(grep VmStk /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmExe:    $(grep VmExe /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmLib:    $(grep VmLib /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"
        echo "  VmPTE:    $(grep VmPTE /proc/"$PID"/status 2>/dev/null | awk '{print $2 $3}')"

        echo ""
        echo "  Maps:"
        cat /proc/"$PID"/smaps 2>/dev/null | grep -E "^(Size|Rss|Shared|Private|Pss)" | head -20
    fi

    # ═══════════════════════════════════════════════════════════════
    # 3. CPU & THREADS
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "3. CPU & THREADS"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  Thread list:"
        ps -Lo pid,tid,pcpu,comm -p "$PID" 2>/dev/null | head -15

        echo ""
        echo "  Context switches:"
        grep -E "ctxt_switches" /proc/"$PID"/status 2>/dev/null

        echo ""
        echo "  CPU affinity:"
        taskset -p -c $PID 2>/dev/null || echo "    N/A"
    fi

    # ═══════════════════════════════════════════════════════════════
    # 4. FILES & FDs
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "4. FILES & DESCRIPTORS"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  FD count: $FDS"
        echo "  FD types:"
        ls -l /proc/"$PID"/fd 2>/dev/null | awk '{print $10}' | sort | uniq -c | sort -rn | head -10

        echo ""
        echo "  Recent files:"
        ls -la /proc/"$PID"/fd 2>/dev/null | head -15

        echo ""
        echo "  CWD: $(readlink /proc/"$PID"/cwd 2>/dev/null)"
        echo "  Root: $(readlink /proc/"$PID"/root 2>/dev/null)"
    fi

    # ═══════════════════════════════════════════════════════════════
    # 5. NETWORK
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "5. NETWORK"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  Connections: $(lsof -i -a -p $PID 2>/dev/null -c COMMAND)"
        echo "  TCP:"
        ss -tnp 2>/dev/null | grep "$PID" | head -10

        echo "  UDP:"
        ss -unp 2>/dev/null | grep "$PID" | head -5
    fi

    # ═══════════════════════════════════════════════════════════════
    # 6. DISK I/O
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "6. DISK I/O"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ] && [ -f /proc/"$PID"/io ]; then
        cat /proc/"$PID"/io 2>/dev/null | grep -E "^(read_bytes|write_bytes|cancelled|syscall)"
    fi

    # ═══════════════════════════════════════════════════════════════
    # 7. SIGNALS & LIMITS
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "7. SIGNALS & LIMITS"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  Limits:"
        cat /proc/"$PID"/limits 2>/dev/null | grep -E "(Max file|Max process|Max memory)"

        echo ""
        echo "  Pending signals:"
        grep SigPnd /proc/"$PID"/status 2>/dev/null

        echo "  Blocked signals:"
        grep SigBlk /proc/"$PID"/status 2>/dev/null
    fi

    # ═══════════════════════════════════════════════════════════════
    # 8. COMMAND & ENVIRONMENT
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "8. COMMAND & ENVIRONMENT"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  Cmdline:"
        cat /proc/"$PID"/cmdline 2>/dev/null | tr '\0' ' ' | fold -s -w 80

        echo ""
        echo "  Executable: $(readlink /proc/"$PID"/exe 2>/dev/null)"
    fi

    # ═══════════════════════════════════════════════════════════════
    # 9. SECURITY & NAMESPACE
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "9. SECURITY & NAMESPACE"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  UID/GID:"
        grep -E "^(Uid|Gid)" /proc/"$PID"/status 2>/dev/null

        echo ""
        echo "  Capabilities:"
        cat /proc/"$PID"/status 2>/dev/null | grep Cap

        echo ""
        echo "  Namespace:"
        ls -la /proc/"$PID"/ns 2>/dev/null | wc -l
    fi

    # ═══════════════════════════════════════════════════════════════
    # 10. TIMING
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "10. TIMING & STATISTICS"
    echo "════════════════════════════════════════════════════════════"

    if [ -n "$PID" ]; then
        echo "  Start time:"
        ps -o lstart= -p "$PID" 2>/dev/null

        echo "  Elapsed:"
        ps -o etime= -p "$PID" 2>/dev/null

        echo ""
        echo "  I/O wait:"
        pidstat -p "$PID" 1 1 2>/dev/null | tail -2
    fi

    # ═══════════════════════════════════════════════════════════════
    # 11. SYSTEM
    # ═════════════════════════════════════════════════════════════
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "11. SYSTEM STATE"
    echo "══════════════════════════════════════════════════════"

    echo "  Load: $(cat /proc/loadavg)"
    echo "  Memory: $(free -h | head -2)"
    echo "  Disk: $(df -h . | tail -1)"
    echo "  Uptime: $(uptime)"

    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "AUDIT COMPLETE"
    echo "════════════════════════════════════════════════════════════"

} | tee "$OUTPUT_DIR/full_audit_${TIMESTAMP}.txt"

echo ""
echo "Saved to: $OUTPUT_DIR/full_audit_${TIMESTAMP}.txt"
