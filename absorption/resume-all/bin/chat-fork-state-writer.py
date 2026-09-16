#!/usr/bin/env python3
"""chat-fork-state-writer.py — Python fallback for the chat-fork-state snapshot.

Produces a JSON snapshot at ~/.local/share/resume-all/chat-fork-state.json that
matches the shape of `chat-fork-state.ts --json` from the OmniRoute fork.

This Python fallback exists so the MCP server (thegent-mcp) resource
`chat://fork-state` has data even when the upstream TypeScript build isn't
running. When the fork IS running and `chat-fork-state.ts --save` is invoked,
that file just overwrites this one with richer data (live cache state, etc.).

Snapshot shape (matches chatForkState.ts):

  {
    "version": "1.0.0",
    "generatedAtMs": 1786314353352,
    "combosCache": {
      "hasCachedPromise": false,
      "cachedAtMs": 0,
      "cachedVersion": 0,
      "ttlMs": 10000
    },
    "breakerPredicates": {
      "statusCodes": [408, 425, 429, 500, 502, 503, 504],
      "size": 7,
      "sampleTrue": {"status": 503, "tripsBreaker": true},
      "sampleFalse": {"status": 200, "tripsBreaker": false}
    },
    "cooldownHelpers": {
      "sampleFormatSeconds": {"inputMs": 7500, "outputSec": 8},
      "sampleDescribeWait": {"output": "wait 8s before retry"},
      "sampleNoRetry": {"output": "no cooldown retry needed"}
    }
  }

Also writes a poll tick to chat-fork-state-poll.json with the same shape + ts.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

OUT_DIR = Path(os.environ.get("RESUME_ALL_DIR", "/Users/kooshapari/.local/share/resume-all"))
SNAPSHOT_FILE = OUT_DIR / "chat-fork-state.json"
POLL_FILE = OUT_DIR / "chat-fork-state-poll.json"

# Mirror PROVIDER_BREAKER_FAILURE_STATUSES from chatPredicates.ts
PROVIDER_BREAKER_FAILURE_STATUSES = {408, 425, 429, 500, 502, 503, 504}
COMBOS_CACHE_TTL_MS = 10_000
FORK_CHAT_STATE_VERSION = "1.0.0"


def build_snapshot() -> dict:
    """Build a snapshot dict matching chatForkState.ts getForkChatState() shape."""
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    sorted_codes = sorted(PROVIDER_BREAKER_FAILURE_STATUSES)
    return {
        "version": FORK_CHAT_STATE_VERSION,
        "generatedAtMs": now_ms,
        "combosCache": {
            "hasCachedPromise": False,
            "cachedAtMs": 0,
            "cachedVersion": 0,
            "ttlMs": COMBOS_CACHE_TTL_MS,
        },
        "breakerPredicates": {
            "statusCodes": sorted_codes,
            "size": len(sorted_codes),
            "sampleTrue": {"status": 503, "tripsBreaker": True},
            "sampleFalse": {"status": 200, "tripsBreaker": False},
        },
        "cooldownHelpers": {
            "sampleFormatSeconds": {"inputMs": 7500, "outputSec": 8},
            "sampleDescribeWait": {"output": "wait 8s before retry"},
            "sampleNoRetry": {"output": "no cooldown retry needed"},
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snap = build_snapshot()

    # Write snapshot
    SNAPSHOT_FILE.write_text(json.dumps(snap, indent=2) + "\n")

    # Write poll tick with ts wrapper
    poll = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ts_epoch": snap["generatedAtMs"] // 1000,
        "snapshot": snap,
    }
    POLL_FILE.write_text(json.dumps(poll, indent=2) + "\n")

    print(f"chat-fork-state-writer: wrote {SNAPSHOT_FILE}")
    print(f"  size: {SNAPSHOT_FILE.stat().st_size:,} bytes")
    print(f"  version: {FORK_CHAT_STATE_VERSION}")
    print(f"  breaker statuses: {sorted(PROVIDER_BREAKER_FAILURE_STATUSES)}")
    print(f"chat-fork-state-writer: wrote {POLL_FILE}")
    print(f"  size: {POLL_FILE.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
