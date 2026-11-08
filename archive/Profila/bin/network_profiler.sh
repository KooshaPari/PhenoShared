#!/bin/bash
# network_profiler.sh - Network profiling for codex/thegent

TARGET="${1:-codex}"
OUTPUT_DIR="${2:-reports}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Network Profiling: $TARGET ==="

# Get PID
PID=$(pgrep -f "$TARGET" | head -1)

if [ -z "$PID" ]; then
    echo "Process not running. Start $TARGET first."
    exit 1
fi

echo "PID: $PID"
echo "Output: $OUTPUT_DIR/network_${TIMESTAMP}.txt"
echo ""

{
echo "=== NETWORK CONNECTIONS ==="
echo "--- Active Connections ---"
lsof -i -a -p "$PID" 2>/dev/null || echo "No connections"

echo ""
echo "--- Connection States ---"
ss -tnp 2>/dev/null | grep "$PID" || echo "No TCP"

echo ""
echo "--- DNS Resolution ==="
ss -tnp 2>/dev/null | grep "$PID" | awk '{print $5}' | cut -d: -f1 | sort -u

echo ""
echo "--- Bandwidth (30s sample) ==="
# Capture packet counts
if command -v nethogs &> /dev/null; then
    sudo nethogs -d 30 -p "$PID" 2>/dev/null || echo "Need root"
elif command -v iftop &> /dev/null; then
    sudo iftop -i any -d 30 2>/dev/null | head -20 || echo "Need root"
else
    # Fallback to /proc
    RX1=$(cat /proc/net/dev | grep -E '(eth0|en0|wlan0)' | awk '{print $2}')
    TX1=$(cat /proc/net/dev | grep -E '(eth0|en0|wlan0)' | awk '{print $10}')
    sleep 30
    RX2=$(cat /proc/net/dev | grep -E '(eth0|en0|wlan0)' | awk '{print $2}')
    TX2=$(cat /proc/net/dev | grep -E '(eth0|en0|wlan0)' | awk '{print $10}')
    echo "RX: $(( (RX2 - RX1) / 30 )) bytes/sec"
    echo "TX: $(( (TX2 - TX1) / 30 )) bytes/sec"
fi

echo ""
echo "=== SOCKET STATISTICS ==="
ss -s 2>/dev/null | head -10

echo ""
echo "=== NETWORK ERRORS ==="
cat /proc/net/snmp 2>/dev/null | grep -i error || echo "No error stats"

} > "$OUTPUT_DIR/network_${TIMESTAMP}.txt"

echo "Network profile saved to: $OUTPUT_DIR/network_${TIMESTAMP}.txt"
