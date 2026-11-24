#!/usr/bin/env python3
"""Install repo2rlenv and pull reference Harbor datasets."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import CONFIG_DIR, PHENO_ROOT


def _expand(s: str) -> str:
    return os.path.expandvars(s.replace("${PHENO_ROOT}", str(PHENO_ROOT)))


def _repo2rlenv_cmd() -> list[str]:
    exe = shutil.which("repo2rlenv")
    if exe:
        return [exe]
    scripts = Path(sys.executable).resolve().parent
    for name in ("repo2rlenv.exe", "repo2rlenv"):
        candidate = scripts / name
        if candidate.exists():
            return [str(candidate)]
    raise FileNotFoundError("repo2rlenv not found — pip install repo2rlenv")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-install", action="store_true")
    p.add_argument("--skip-pull", action="store_true")
    args = p.parse_args()

    if not args.skip_install:
        print("Installing repo2rlenv...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "repo2rlenv", "-q"], check=True
        )
        subprocess.run([*_repo2rlenv_cmd(), "--help"], check=False)

    cfg = yaml.safe_load((CONFIG_DIR / "repo2rl.yaml").read_text(encoding="utf-8"))
    if args.skip_pull:
        return 0

    for ref in cfg.get("reference_pull", []):
        hf_id = ref["hf_id"]
        local = Path(_expand(ref["local_dir"]))
        local.mkdir(parents=True, exist_ok=True)
        if any(local.iterdir()):
            print(f"Skip pull (exists): {local}")
            continue
        print(f"Pulling {hf_id} -> {local}")
        r = subprocess.run(
            [*_repo2rlenv_cmd(), "pull", hf_id, str(local)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            print(f"  pull failed: {r.stderr[:500]}")
            print("  Trying huggingface-cli download fallback...")
            r2 = subprocess.run(
                [
                    "huggingface-cli",
                    "download",
                    hf_id,
                    "--repo-type",
                    "dataset",
                    "--local-dir",
                    str(local),
                ],
                capture_output=True,
                text=True,
            )
            if r2.returncode != 0:
                print(f"  HF fallback failed: {r2.stderr[:300]}")
        else:
            print(f"  OK: {local}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
