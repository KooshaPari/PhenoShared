#!/usr/bin/env python3
"""DAG-93: preflight probes for the Desktop NVIDIA dual-GPU lane.

Runs six readiness probes for the Qwen3.5 dual-GPU lane contract:

    1. probe_nvidia_smi             — >=2 GPUs visible via nvidia-smi
       + PCIe link width and VRAM probe for RTX 3090 Ti + GTX 1080 Ti
    2. probe_cuda_visible_devices   — CUDA_VISIBLE_DEVICES parses to >=1 idx
    3. probe_disk_space             — >=10 GB free under the HF model cache
    4. probe_worktree_clean         — ``git status --porcelain`` is empty
    5. probe_lane_config_loads      — config/desktop_nvidia_qwen35_lane.yaml
                                       parses and exposes ``schema_version``
    6. probe_host_manifest_present  — evidence/dual_gpu/host_manifest.yaml
                                       exists (written by check.sh / DAG-92)

Exit code:
    0  all probes pass
    1  any probe fails

Flags:
    --dry-run       skip side-effecting / slow probes (1 and 3) and prefix
                    every probe line with ``[dry-run]``. Read-only probes
                    (2, 4, 5, 6) still execute so the operator can confirm
                    environment state without touching the GPU stack.
    --verbose       print per-probe status (default: only failures).
    --exit-on-warn  future-proof: treat [warn] probes as failures. No
                    probes emit [warn] today, so this is a no-op unless a
                    later probe is downgraded to warning severity.

Stdlib-only apart from PyYAML (declared in requirements.txt; used by
probe_lane_config_loads per the DAG-93 spec). Deliberately avoids
``nvidia-ml-py3`` / ``pynvml`` / ``psutil`` so the probe can run on any
host with a ``git`` + ``nvidia-smi`` PATH, including the Apple Silicon
dev workstation that orchestrates the LLM host remotely.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_CONFIG = REPO_ROOT / "config" / "desktop_nvidia_qwen35_lane.yaml"
HOST_MANIFEST = REPO_ROOT / "evidence" / "dual_gpu" / "host_manifest.yaml"
HF_CACHE_DEFAULT = Path.home() / ".cache" / "huggingface"
DISK_MIN_FREE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
EXPECTED_GPU_COUNT = 2
EXPECTED_GPUS: dict[str, dict[str, Any]] = {
    "gtx_1080_ti": {"substr": "1080 Ti", "vram_mib": 11264},
    "rtx_3090_ti": {"substr": "3090 Ti", "vram_mib": 24564},
}
PCIE_MIN_WIDTH = 8  # AGENTS.md §2.3 dual-GPU baseline


def _parse_vram_mib(token):
    token = token.strip().lower().replace("mib", "").strip()
    try:
        return int(token.split()[0])
    except Exception:
        return None


def _parse_pcie_width(token):
    tt = token.strip().lower().replace("x", "").strip()
    try:
        return int(tt.split()[0])
    except Exception:
        return None


ProbeFn = Callable[[bool], tuple[bool, str]]


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def probe_nvidia_smi(_dry_run: bool) -> tuple[bool, str]:
    """Probe 1: run ``nvidia-smi`` and assert >=2 GPUs are visible.

    Parses ``nvidia-smi --query-gpu=index,name,memory.total,
    pcie.link.gen.current,pcie.link.width.current`` CSV output for the
    dual-GPU contract (RTX 3090 Ti + GTX 1080 Ti). Validates count,
    name substrings, VRAM, and PCIe width. Exits non-zero on count or
    name/PCIe mismatch, and on VRAM mismatch when PREFLIGHT_STRICT=1.
    Falls back to 3-column query if PCIe query unsupported.
    """
    primary_cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,pcie.link.gen.current,pcie.link.width.current",
        "--format=csv,noheader",
    ]
    fallback_cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total",
        "--format=csv,noheader",
    ]
    proc = None
    for cmd in (primary_cmd, fallback_cmd):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except FileNotFoundError:
            return False, "nvidia-smi not on PATH (LLM host side required)"
        except subprocess.TimeoutExpired:
            return False, "nvidia-smi timed out after 15s"
        if proc.returncode == 0:
            break
        if cmd is primary_cmd:
            continue
        stderr = (proc.stderr or "").strip().splitlines()
        tail = stderr[-1] if stderr else "unknown error"
        return False, f"nvidia-smi exit={proc.returncode}: {tail}"
    assert proc is not None
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().splitlines()
        tail = stderr[-1] if stderr else "unknown error"
        return False, f"nvidia-smi exit={proc.returncode}: {tail}"
    rows = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(rows) < EXPECTED_GPU_COUNT:
        return (
            False,
            f"expected >= {EXPECTED_GPU_COUNT} GPUs, saw {len(rows)}: "
            f"{proc.stdout.strip()[:200] or '<empty>'}",
        )
    strict = os.environ.get("PREFLIGHT_STRICT", "").strip() == "1"
    issues: list[str] = []
    seen_names: list[str] = []
    seen_vram: list[int | None] = []
    seen_widths: list[int | None] = []
    for row in rows:
        parts = [p.strip() for p in row.split(",")]
        name = parts[1] if len(parts) > 1 else ""
        vram_tok = parts[2] if len(parts) > 2 else ""
        seen_names.append(name)
        vram = _parse_vram_mib(vram_tok) if vram_tok else None
        seen_vram.append(vram)
        width: int | None = None
        if len(parts) > 3:
            for tok in parts[3:]:
                cand = _parse_pcie_width(tok)
                if cand is not None and 1 <= cand <= 32:
                    width = cand
                    break
        seen_widths.append(width)
    for key, exp in EXPECTED_GPUS.items():
        substr = exp["substr"]
        if not any(substr.lower() in n.lower() for n in seen_names):
            issues.append(f"missing {key} ({substr!r}) in {seen_names}")
    expected_vrams = sorted(v["vram_mib"] for v in EXPECTED_GPUS.values())
    actual_vrams = sorted(v for v in seen_vram if v is not None)
    if actual_vrams and actual_vrams != expected_vrams:
        msg = f"VRAM mismatch: expected {expected_vrams} MiB, saw {actual_vrams} MiB"
        if strict:
            issues.append(msg)
    for idx, w in enumerate(seen_widths):
        if w is not None and w < PCIE_MIN_WIDTH:
            issues.append(f"GPU {idx} PCIe width {w}x < {PCIE_MIN_WIDTH}x")
    sample = rows[0].strip()
    detail = f"{len(rows)} GPU(s) visible; sample='{sample[:80]}'; names={seen_names}; vram_mib={seen_vram}; pcie_width={seen_widths}"
    if issues:
        if strict:
            return False, f"{detail} | mismatches: {'; '.join(issues)}"
        name_issues = [i for i in issues if i.startswith("missing")]
        pcie_issues = [i for i in issues if "PCIe" in i]
        if name_issues or pcie_issues:
            return False, f"{detail} | mismatches: {'; '.join(issues)}"
        detail += f" | warn: {'; '.join(issues)}"
    return True, detail


def probe_cuda_visible_devices(_dry_run: bool) -> tuple[bool, str]:
    """Probe 2: ``CUDA_VISIBLE_DEVICES`` parses to >=1 integer index."""
    raw = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if not raw:
        return (
            False,
            "CUDA_VISIBLE_DEVICES unset (lane contract requires explicit "
            "device visibility)",
        )
    indices: list[int] = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            indices.append(int(tok))
        except ValueError:
            return (
                False,
                f"CUDA_VISIBLE_DEVICES contains non-integer token: {tok!r}",
            )
    if not indices:
        return False, "CUDA_VISIBLE_DEVICES parsed to zero indices"
    return True, f"CUDA_VISIBLE_DEVICES={raw} ({len(indices)} idx)"


def probe_disk_space(_dry_run: bool) -> tuple[bool, str]:
    """Probe 3: HF model cache root has >=10 GB free bytes."""
    cache_root = Path(os.environ.get("HF_HOME", str(HF_CACHE_DEFAULT)))
    if not cache_root.exists():
        # The cache may legitimately not exist yet; create is a side effect
        # so we only stat the parent (which must exist for the cache to be
        # reachable at all).
        cache_root = cache_root.parent
    usage = shutil.disk_usage(cache_root)
    free_gib = usage.free / (1024**3)
    if usage.free < DISK_MIN_FREE_BYTES:
        return (
            False,
            f"{free_gib:.2f} GiB free under {cache_root} "
            f"(need >= {DISK_MIN_FREE_BYTES // (1024**3)} GiB)",
        )
    return True, f"{free_gib:.2f} GiB free under {cache_root}"


def probe_worktree_clean(_dry_run: bool) -> tuple[bool, str]:
    """Probe 4: ``git status --porcelain`` is empty in REPO_ROOT."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
    except FileNotFoundError:
        return False, "git not on PATH"
    except subprocess.TimeoutExpired:
        return False, "git status timed out after 10s"
    if proc.returncode != 0:
        return False, f"git status exit={proc.returncode}"
    dirty = [line for line in proc.stdout.splitlines() if line.strip()]
    if dirty:
        sample = "; ".join(dirty[:3])
        return (
            False,
            f"worktree dirty ({len(dirty)} entries; first: {sample})",
        )
    return True, "git status --porcelain is empty"


def probe_lane_config_loads(_dry_run: bool) -> tuple[bool, str]:
    """Probe 5: lane config YAML parses and exposes ``schema_version``."""
    if not LANE_CONFIG.is_file():
        return False, f"missing lane config: {LANE_CONFIG.relative_to(REPO_ROOT)}"
    try:
        data = yaml.safe_load(LANE_CONFIG.read_text())
    except yaml.YAMLError as exc:
        return False, f"YAML parse error in lane config: {exc}"
    if not isinstance(data, dict):
        return False, "lane config top-level is not a mapping"
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        return False, "lane config missing non-empty schema_version"
    return True, f"lane config schema_version={schema_version.strip()!r}"


def probe_host_manifest_present(_dry_run: bool) -> tuple[bool, str]:
    """Probe 6: ``evidence/dual_gpu/host_manifest.yaml`` exists (DAG-92)."""
    if not HOST_MANIFEST.is_file():
        return (
            False,
            f"missing host manifest: {HOST_MANIFEST.relative_to(REPO_ROOT)} "
            f"(run evidence/dual_gpu/check.sh or DAG-92 writer)",
        )
    size = HOST_MANIFEST.stat().st_size
    return True, f"host manifest present ({size} bytes)"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


PROBES: list[tuple[str, ProbeFn]] = [
    ("probe_nvidia_smi", probe_nvidia_smi),
    ("probe_cuda_visible_devices", probe_cuda_visible_devices),
    ("probe_disk_space", probe_disk_space),
    ("probe_worktree_clean", probe_worktree_clean),
    ("probe_lane_config_loads", probe_lane_config_loads),
    ("probe_host_manifest_present", probe_host_manifest_present),
]
# Probes skipped (not executed) under --dry-run. Their entries still print.
DRY_RUN_SKIP_NAMES = frozenset({"probe_nvidia_smi", "probe_disk_space"})


def _format_status(
    name: str,
    passed: bool,
    message: str,
    *,
    dry_run: bool,
    skipped: bool,
) -> str:
    if skipped:
        prefix = "[dry-run]"
        body = "skipped (side-effecting / slow)"
    else:
        prefix = "[ok]" if passed else "[fail]"
        body = message
    return f"{prefix:<10} {name}: {body}"


def run_preflight(
    dry_run: bool = False,
    verbose: bool = False,
    exit_on_warn: bool = False,
) -> int:
    """Execute every probe and return the process exit code (0/1)."""
    failures = 0
    for name, fn in PROBES:
        skipped = dry_run and name in DRY_RUN_SKIP_NAMES
        if skipped:
            passed, message = True, ""
        else:
            try:
                passed, message = fn(dry_run)
            except Exception as exc:  # pragma: no cover - defensive
                passed, message = False, f"probe raised {type(exc).__name__}: {exc}"
        line = _format_status(
            name,
            passed,
            message,
            dry_run=dry_run,
            skipped=skipped,
        )
        if verbose or not passed:
            print(line)
        if not passed:
            failures += 1
    # Future-proof hook: today every probe is binary, but if a [warn]
    # tier is ever added, --exit-on-warn promotes it to a failure.
    del exit_on_warn  # silence linters; reserved for future use
    if failures:
        print(f"preflight: {failures} probe(s) failed")
        return 1
    print("preflight: all probes passed")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "DAG-93 preflight probes for the Desktop NVIDIA dual-GPU lane. "
            "Exits 0 iff every probe passes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Skip side-effecting / slow probes (nvidia-smi, disk space) and "
            "prefix every probe line with [dry-run]."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-probe status (default: print only failures).",
    )
    parser.add_argument(
        "--exit-on-warn",
        action="store_true",
        help=(
            "Treat [warn] probes as failures. No probe emits [warn] today; "
            "this flag is reserved for future probes that down-grade to "
            "warning severity."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return run_preflight(
        dry_run=args.dry_run,
        verbose=args.verbose,
        exit_on_warn=args.exit_on_warn,
    )


if __name__ == "__main__":
    sys.exit(main())
