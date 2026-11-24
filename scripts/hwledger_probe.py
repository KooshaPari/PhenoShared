#!/usr/bin/env python3
"""hwLedger-compatible inventory probe for Win/WSL/Linux (bootstrap until Rust CLI).

Emits JSON matching the control-plane contract so one tool can manage inference
endpoints across the trio. Does not revive phenotype-omlx for CUDA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config" / "hwledger_control_plane.yaml"
DEFAULT_ADMISSION = ROOT / "state" / "runtime_admission_2026-07-19.json"
LAUNCHER = ROOT / "scripts" / "start_dual_gpu_stack.ps1"
LANE_IDS = ("rtx3090_qwen35_9b_vllm_c0", "gtx1080_qwen35_08b_llama_helper")

from typing import Any

from pheno.runtime_admission import validate_runtime_admission


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cfg(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lane_admitted(row: dict[str, Any]) -> bool:
    checks = row.get("checks")
    try:
        now = datetime.now(UTC)
        route_expires = datetime.fromisoformat(
            str(row.get("route", {}).get("expires_at")).replace("Z", "+00:00")
        )
        lease_expires = datetime.fromisoformat(
            str(row.get("endpoint_lease", {}).get("expires_at")).replace("Z", "+00:00")
        )
        unexpired = now <= route_expires.astimezone(
            UTC
        ) and now <= lease_expires.astimezone(UTC)
    except (TypeError, ValueError):
        unexpired = False
    return bool(
        row.get("decision") == "admitted"
        and row.get("action_permitted") is True
        and isinstance(checks, dict)
        and checks
        and all(value is True for value in checks.values())
        and row.get("blockers") == []
        and row.get("authorization", {}).get("launch", {}).get("granted") is True
        and row.get("authorization", {}).get("route", {}).get("granted") is True
        and row.get("endpoint_lease", {}).get("bound") is True
        and row.get("route", {}).get("active") is True
        and unexpired
    )


def runtime_admission_gate(
    *, cfg: dict[str, Any], profile: str, admission_path: Path, config_path: Path
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        admission = json.loads(admission_path.read_text(encoding="utf-8"))
        admission = validate_runtime_admission(admission, root=ROOT)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        admission = {}
        blockers.append("runtime_admission_missing_invalid_or_stale")
    rows = admission.get("lanes", [])
    exact = {
        lane_id: [row for row in rows if row.get("lane_id") == lane_id]
        for lane_id in LANE_IDS
    }
    primary_id, helper_id = LANE_IDS
    primary_admitted = len(exact[primary_id]) == 1 and _lane_admitted(
        exact[primary_id][0]
    )
    helper_admitted = len(exact[helper_id]) == 1 and _lane_admitted(exact[helper_id][0])
    if len(exact[primary_id]) != 1:
        blockers.append(f"{primary_id}:lane_missing_or_duplicate")
    elif not primary_admitted:
        blockers.append(f"{primary_id}:launch_route_not_admitted")
    # Admission is lane-scoped here: the helper is optional, so an aggregate
    # document flag must not override an exhaustively admitted required lane.
    # Canonical validation above remains mandatory and _lane_admitted checks
    # every authority, lease, route, expiry, check and blocker on that lane.
    if profile != "dual-gpu":
        blockers.append("profile_not_exact_dual_gpu")
    engines = (cfg.get("profiles", {}).get(profile, {}) or {}).get("engines", [])
    expected = {
        ("llama_1080", "legacy_helper", 18081),
        ("sglang_3090", "primary", 8000),
        ("pheno_proxy", "router", 21080),
    }
    observed = {
        (row.get("id"), row.get("device_role"), row.get("port")) for row in engines
    }
    if observed != expected:
        blockers.append("control_plane_engine_identity_mismatch")
    launcher_hash = _sha256(LAUNCHER) if LAUNCHER.is_file() else None
    config_hash = _sha256(config_path) if config_path.is_file() else None
    lanes_requiring_hash_binding = [primary_id] + (
        [helper_id] if helper_admitted else []
    )
    for lane_id in lanes_requiring_hash_binding:
        if len(exact[lane_id]) == 1:
            sources = exact[lane_id][0].get("source_bindings", {})
            if sources.get("launcher", {}).get("file_sha256") != launcher_hash:
                blockers.append(f"{lane_id}:launcher_hash_not_bound")
            if sources.get("control_plane", {}).get("file_sha256") != config_hash:
                blockers.append(f"{lane_id}:control_plane_hash_not_bound")
        else:
            # A missing/invalid admission row cannot satisfy the primary
            # launcher's physical source binding. Keep both blockers explicit
            # so denial remains auditable rather than collapsing to absence.
            blockers.append(f"{lane_id}:launcher_hash_not_bound")
            blockers.append(f"{lane_id}:control_plane_hash_not_bound")
    blockers = sorted(set(blockers))
    mode = (
        "not_runnable"
        if blockers
        else ("ready_dual" if helper_admitted else "ready_primary_only")
    )
    return {
        "admitted": not blockers,
        "mode": mode,
        "primary_admitted": primary_admitted,
        "helper_admitted": helper_admitted,
        "admission_sha256": admission.get("admission_sha256"),
        "launcher_sha256": launcher_hash,
        "control_plane_sha256": config_hash,
        "blockers": blockers,
    }


def _tcp_open(host: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.5) -> dict[str, Any]:
    try:
        with (
            urllib.request.urlopen(url, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = resp.read(512)
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "snippet": body[:120].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "snippet": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "snippet": str(e)}


def _nvidia_smi_executable() -> str | None:
    direct = shutil.which("nvidia-smi")
    if direct:
        return direct
    if os.name != "nt":
        return None
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "System32" / "nvidia-smi.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "NVIDIA Corporation"
        / "NVSMI"
        / "nvidia-smi.exe",
    ]
    driver_store = windir / "System32" / "DriverStore" / "FileRepository"
    if driver_store.is_dir():
        candidates.extend(driver_store.glob("nv*\\nvidia-smi.exe"))
    return next((str(path) for path in candidates if path.is_file()), None)


def _nvidia_smi() -> list[dict]:
    executable = _nvidia_smi_executable()
    if executable is None:
        return [{"error": "nvidia-smi executable not found"}]
    try:
        out = subprocess.check_output(
            [
                executable,
                "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as e:
        return [{"error": str(e)}]
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        gpus.append(
            {
                "nvidia_index": int(parts[0]),
                "name": parts[1],
                "memory_total_mib": int(float(parts[2])),
                "memory_used_mib": int(float(parts[3])),
                "util_gpu_pct": int(float(parts[4])),
            }
        )
    return gpus


def _wsl_venv_exists(distro: str = "Ubuntu-22.04") -> bool:
    try:
        r = subprocess.run(
            ["wsl", "-d", distro, "--", "bash", "-lc", "test -d ~/.pheno-serve-venv"],
            capture_output=True,
            timeout=20,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def probe_engine(eng: dict[str, Any]) -> dict[str, Any]:
    port = int(eng.get("port", 0))
    health = eng.get("health")
    base = eng.get("openai_base")
    rec = {
        "id": eng.get("id"),
        "kind": eng.get("kind"),
        "platform": eng.get("platform"),
        "device_role": eng.get("device_role"),
        "port": port,
        "tcp_open": _tcp_open("127.0.0.1", port) if port else False,
        "health": None,
        "openai_base": base,
        "cuda_visible_devices": eng.get("cuda_visible_devices"),
        "cuda_map": eng.get("cuda_map"),
    }
    if health:
        rec["health"] = _http_ok(health)
    return rec


def cmd_status(
    cfg: dict[str, Any],
    profile: str,
    *,
    admission_path: Path = DEFAULT_ADMISSION,
    config_path: Path = DEFAULT_CFG,
) -> dict[str, Any]:
    profiles = cfg.get("profiles") or {}
    if profile not in profiles:
        raise SystemExit(f"unknown profile {profile!r}; have {list(profiles)}")
    prof = profiles[profile]
    gate = runtime_admission_gate(
        cfg=cfg, profile=profile, admission_path=admission_path, config_path=config_path
    )
    if not gate["admitted"]:
        engines = [
            {
                "id": e.get("id"),
                "kind": e.get("kind"),
                "platform": e.get("platform"),
                "device_role": e.get("device_role"),
                "admission_state": "denied",
            }
            for e in prof.get("engines") or []
        ]
        return {
            "schema_version": "pheno.hwledger.inventory.v1",
            "timestamp": _now(),
            "profile": profile,
            "platforms": prof.get("platforms"),
            "admission": gate,
            "engines": engines,
            "operations": {
                "process": False,
                "device": False,
                "network": False,
                "endpoint": False,
            },
            "action_permitted": False,
        }
    admitted_engines = [
        e
        for e in prof.get("engines") or []
        if gate["helper_admitted"] or e.get("device_role") != "legacy_helper"
    ]
    engines = [probe_engine(e) for e in admitted_engines]
    return {
        "schema_version": "pheno.hwledger.inventory.v1",
        "timestamp": _now(),
        "profile": profile,
        "platforms": prof.get("platforms"),
        "gpus": _nvidia_smi(),
        "wsl_pheno_serve_venv": _wsl_venv_exists() if sys.platform == "win32" else None,
        "omlx_policy": cfg.get("omlx"),
        "cuda_index_maps": cfg.get("cuda_index_maps"),
        "engines": engines,
        "admission": gate,
        "consumers": cfg.get("consumers"),
        "manage_hint": "python scripts/hwledger_probe.py up --profile dual-gpu",
    }


def cmd_up(
    cfg: dict[str, Any],
    profile: str,
    *,
    admission_path: Path = DEFAULT_ADMISSION,
    config_path: Path = DEFAULT_CFG,
) -> dict[str, Any]:
    gate = runtime_admission_gate(
        cfg=cfg, profile=profile, admission_path=admission_path, config_path=config_path
    )
    if not gate["admitted"]:
        return {
            "schema_version": "pheno.hwledger.up-result.v1",
            "profile": profile,
            "status": "runtime_admission_denied",
            "action_permitted": False,
            "admission": gate,
            "operations": {
                "process": False,
                "device": False,
                "network": False,
                "endpoint": False,
            },
        }
    script = LAUNCHER
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(ROOT),
    )
    inv = cmd_status(
        cfg, profile, admission_path=admission_path, config_path=config_path
    )
    inv["up_exit_code"] = proc.returncode
    return inv


def main() -> int:
    ap = argparse.ArgumentParser(
        description="hwLedger trio probe (Win/WSL/Linux bootstrap)"
    )
    ap.add_argument("--config", type=Path, default=DEFAULT_CFG)
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status", help="inventory + health")
    st.add_argument("--profile", default="dual-gpu")
    up = sub.add_parser("up", help="start dual-gpu stack via start_dual_gpu_stack.ps1")
    up.add_argument("--profile", default="dual-gpu")
    args = ap.parse_args()
    cfg = _load_cfg(args.config)
    if args.cmd == "status":
        result = cmd_status(
            cfg, args.profile, admission_path=DEFAULT_ADMISSION, config_path=args.config
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("action_permitted", True) else 2
    if args.cmd == "up":
        result = cmd_up(
            cfg, args.profile, admission_path=DEFAULT_ADMISSION, config_path=args.config
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("action_permitted", True) else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
