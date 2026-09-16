#!/usr/bin/env python3
"""Run one local llama.cpp model through the smoke perf and quality probes."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def wait_ready(base_url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    url = base_url.rstrip("/") + "/health"
    while time.monotonic() < deadline:
        try:
            with (
                urllib.request.urlopen(url, timeout=2) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    raise TimeoutError(f"server readiness timeout after {timeout_s:.0f}s: {url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--device", default="CUDA0")
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--readiness-timeout-s", type=float, default=120)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--probe-output", type=Path, required=True)
    parser.add_argument("--quality-output", type=Path, required=True)
    parser.add_argument("--server-stdout", type=Path, required=True)
    parser.add_argument("--server-stderr", type=Path, required=True)
    args = parser.parse_args()
    for path in (
        args.probe_output,
        args.quality_output,
        args.server_stdout,
        args.server_stderr,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(args.binary),
        "-m",
        str(args.model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--alias",
        args.alias,
        "-ngl",
        "99",
        "-dev",
        args.device,
        "-c",
        str(args.context),
        "-fa",
        "on",
        "--reasoning-format",
        "none",
        "--no-webui",
    ]
    with (
        args.server_stdout.open("w", encoding="utf-8") as stdout,
        args.server_stderr.open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        try:
            wait_ready(f"http://127.0.0.1:{args.port}", args.readiness_timeout_s)
            probe_command = [
                sys.executable,
                "scripts/perf_probe.py",
                "--base-url",
                f"http://127.0.0.1:{args.port}",
                "--model",
                args.alias,
                "--fixture",
                str(args.fixture),
                "--output",
                str(args.probe_output),
                "--batch-size",
                "1",
                "--warmup",
                "1",
                "--timeout-s",
                "60",
                "--engine-label",
                "llama.cpp",
                "--reasoning-format",
                "none",
            ]
            subprocess.run(probe_command, check=True)
            score_command = [
                sys.executable,
                "scripts/score_smoke_fixture.py",
                "--fixture",
                str(args.fixture),
                "--probe",
                str(args.probe_output),
                "--output",
                str(args.quality_output),
            ]
            subprocess.run(score_command, check=True)
            return 0
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
