#!/usr/bin/env python3
"""
System Metrics Collector
=========================

Collects CPU, memory, and disk usage using the psutil library
and exports results as JSON.

Usage::

    python3 system_metrics.py                    # print to stdout
    python3 system_metrics.py --output metrics.json
    python3 system_metrics.py --watch 5          # collect every 5 seconds
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

try:
    import psutil  # wraps: psutil (latest stable)
except ImportError:
    print("psutil is required: pip install psutil", file=sys.stderr)
    sys.exit(1)


def collect() -> dict[str, Any]:
    """Collect a single snapshot of system metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_times = psutil.cpu_times()._asdict()
    cpu_count = psutil.cpu_count(logical=True)

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disk_usage: dict[str, Any] = {}
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disk_usage[part.mountpoint] = {
                "device": part.device,
                "fstype": part.fstype,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "percent": usage.percent,
            }
        except PermissionError:
            continue

    net = psutil.net_io_counters()

    return {
        "timestamp": time.time(),
        "cpu": {
            "percent": cpu_percent,
            "count_logical": cpu_count,
            "count_physical": psutil.cpu_count(logical=False),
            "times": cpu_times,
        },
        "memory": {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "free_bytes": mem.free,
            "percent": mem.percent,
        },
        "swap": {
            "total_bytes": swap.total,
            "used_bytes": swap.used,
            "free_bytes": swap.free,
            "percent": swap.percent,
        },
        "disk": disk_usage,
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect system metrics as JSON")
    parser.add_argument("--output", "-o", help="Write JSON to this file (default: stdout)")
    parser.add_argument(
        "--watch",
        "-w",
        type=float,
        default=0,
        metavar="SECONDS",
        help="Repeat collection every N seconds (0 = one-shot)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    indent = 2 if args.pretty else None

    def emit(data: dict[str, Any]) -> None:
        payload = json.dumps(data, indent=indent)
        if args.output:
            with open(args.output, "w") as fh:
                fh.write(payload + "\n")
        else:
            print(payload)

    if args.watch > 0:
        try:
            while True:
                emit(collect())
                time.sleep(args.watch)
        except KeyboardInterrupt:
            pass
    else:
        emit(collect())


if __name__ == "__main__":
    main()
