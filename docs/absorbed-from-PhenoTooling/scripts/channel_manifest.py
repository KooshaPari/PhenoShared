"""Generate channel manifest JSON for WP-28 streaming release channels.

Reads release-please state + tags from GitHub, emits a manifest file at
.github/channel-manifest.json describing the current version available on
each channel (stable / beta / nightly) per release stream.

Schema:
{
  "generated_at": "2026-07-04T12:34:56Z",
  "streams": {
    "core-stream": {
      "stable":  {"version": "0.3.0", "tag": "core-stream-v0.3.0",
                  "released_at": "2026-07-04T10:00:00Z"},
      "beta":    {"version": "0.4.0-beta.3", "tag": "core-stream-v0.4.0-beta.3"},
      "nightly": {"version": "0.5.0-nightly.20260704", "commit": "abc123"}
    },
    ...
  }
}

Stable channel = highest released tag whose version does NOT contain
  pre-release identifiers (alpha, beta, rc).
Beta channel   = highest released tag with -beta.* suffix.
Nightly channel = the latest commit on main, formatted as 0.X.0-nightly.YYYYMMDD.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_STREAMS = ("core-stream", "cli-stream", "ops-stream")
DEFAULT_OUT = Path(".github/channel-manifest.json")
REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> str:
    """Run a shell command and return stdout, aborting on error."""
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(
            f"command failed: {' '.join(cmd)}\n"
            f"  stderr: {res.stderr}\n"
        )
        sys.exit(res.returncode)
    return res.stdout.strip()


def is_stable(tag: str) -> bool:
    """Stable = released + no pre-release suffix."""
    if not tag:
        return False
    lowered = tag.lower()
    return not any(p in lowered for p in ("alpha", "beta", "rc", "nightly"))


def is_beta(tag: str) -> bool:
    return "beta" in tag.lower()


def is_nightly_tag(tag: str) -> bool:
    return "nightly" in tag.lower()


def fetch_stream_tags(stream: str) -> list[str]:
    """Return all tags matching '<stream>-v*' from origin, sorted newest-first."""
    out = run([
        "git", "ls-remote", "--tags", "--sort=-v:refname",
        "origin", f"refs/tags/{stream}-v*",
    ])
    return [
        line.split("refs/tags/")[-1]
        for line in out.splitlines()
        if line.strip()
    ]


def latest_main_sha() -> str:
    return run(["git", "rev-parse", "origin/main"])


def latest_main_short_sha() -> str:
    return run(["git", "rev-parse", "--short", "origin/main"])[:9]


def stream_record(stream: str, tags: list[str], main_sha: str) -> dict[str, Any]:
    """Build the channel record for one stream."""
    stable = next((t for t in tags if is_stable(t)), None)
    beta = next((t for t in tags if is_beta(t)), None)
    nightly = next((t for t in tags if is_nightly_tag(t)), None)

    def derive(tag: str) -> str:
        # tag format: '<stream>-v<version>' or '<stream>-v<version>-beta.N'
        if not tag:
            return ""
        parts = tag.split("-v", 1)
        return parts[1] if len(parts) == 2 else tag

    out: dict[str, Any] = {}
    if stable:
        out["stable"] = {"version": derive(stable), "tag": stable}
    if beta:
        out["beta"] = {"version": derive(beta), "tag": beta}
    if nightly:
        out["nightly"] = {"version": derive(nightly), "tag": nightly}

    # Always include a nightly pointer to the latest main commit if no
    # explicit nightly tag exists yet.
    if "nightly" not in out and main_sha:
        today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        major_minor = "0.5"
        # Extract major.minor from the latest stable tag, if present.
        if stable:
            ver = derive(stable)
            if ver and ver[0].isdigit():
                mm = ver.split(".")[:2]
                if len(mm) == 2:
                    major_minor = f"{mm[0]}.{int(mm[1]) + 1}"
        out["nightly"] = {
            "version": f"{major_minor}.0-nightly.{today}",
            "commit": main_sha,
        }

    return out


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate streaming channel manifest.")
    p.add_argument(
        "--streams",
        nargs="+",
        default=list(DEFAULT_STREAMS),
        help="Streams to include in the manifest",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for the manifest JSON",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    streams_data: dict[str, Any] = {}
    main_sha = ""
    try:
        main_sha = latest_main_short_sha()
    except SystemExit:
        main_sha = ""

    for stream in args.streams:
        try:
            tags = fetch_stream_tags(stream)
        except SystemExit:
            tags = []
        streams_data[stream] = stream_record(stream, tags, main_sha)

    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "streams": streams_data,
        "schema_version": 1,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())