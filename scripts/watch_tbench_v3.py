#!/usr/bin/env python3
"""Append the current Terminal-Bench 3.x watch state."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.tbench_v3_watch import record_status

if __name__ == "__main__":
    print(record_status())
