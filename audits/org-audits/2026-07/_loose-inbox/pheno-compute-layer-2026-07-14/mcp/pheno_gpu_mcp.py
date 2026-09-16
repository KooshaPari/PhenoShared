#!/usr/bin/env python3
"""
pheno-gpu-mcp - FastMCP server for GPU compute access
Provides GPU status, system info, and remote execution tools

Install:
    uv tool install pheno-gpu-mcp
    # or
    pip install pheno-gpu-mcp

Usage:
    pheno-gpu-mcp  # starts the MCP server

Configure in MCP settings:
    {
        "mcpServers": {
            "pheno-gpu": {
                "command": "pheno-gpu-mcp"
            }
        }
    }
"""

import asyncio
import json
import subprocess
from typing import Any, Optional

# Try to import fastmcp, fall back to minimal implementation
try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False
    # Minimal stub for when fastmcp isn't installed
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
            self._tools = []
        def tool(self, fn):
            self._tools.append(fn)
            return fn
        def run(self, *args, **kwargs):
            print(f"[pheno-gpu-mcp] Running standalone mode...")
            # Run as standalone tool server
            import sys
            for t in self._tools:
                print(f"  - {t.__name__}")

# Configuration
COMPUTE_HOST = "desk"  # or "kooshapari-desk.tail2b570.ts.net"
COMPUTE_IP = "100.96.135.160"

# Create MCP server
mcp = FastMCP("pheno-gpu")


def ssh_exec(cmd: str, timeout: int = 30) -> tuple[str, str, int]:
    """Execute command on remote desktop via SSH."""
    full_cmd = f"ssh {COMPUTE_HOST} \"{cmd}\" 2>&1"
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1


def ssh_exec_wsl(cmd: str, timeout: int = 30) -> tuple[str, str, int]:
    """Execute command on WSL inside Windows desktop."""
    full_cmd = f"ssh {COMPUTE_HOST} \"wsl -e {cmd}\" 2>&1"
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1


#----------------------------------
# GPU Tools
#----------------------------------

@mcp.tool()
async def gpu_status() -> str:
    """Get GPU status - name, memory, temp, utilization."""
    stdout, stderr, code = ssh_exec("nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu,power.draw --format=csv,noheader,nounits")
    if code == 0 and stdout:
        parts = stdout.split(",")
        return json.dumps({
            "name": parts[0].strip(),
            "memory_used_mb": int(parts[1].strip()),
            "memory_total_mb": int(parts[2].strip()),
            "temperature_c": int(parts[3].strip()),
            "utilization_pct": int(parts[4].strip()),
            "power_draw_w": float(parts[5].strip())
        })
    return json.dumps({"error": stderr or "Could not get GPU status"})


@mcp.tool()
async def gpu_full() -> str:
    """Get full nvidia-smi output."""
    stdout, stderr, code = ssh_exec("nvidia-smi")
    if code == 0:
        return stdout
    return f"Error: {stderr}"


@mcp.tool()
async def gpu_processes() -> str:
    """List GPU compute processes."""
    stdout, stderr, code = ssh_exec("nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv")
    if code == 0 and stdout:
        lines = stdout.strip().split("\n")
        return json.dumps({"processes": [{"pid": p.split(",")[0], "name": p.split(",")[1], "memory_mb": p.split(",")[2]} for p in lines[1:]]})
    return json.dumps({"processes": [], "raw": stdout})


#----------------------------------
# System Tools
#----------------------------------

@mcp.tool()
async def system_info() -> str:
    """Get system information."""
    hostname_out, _, _ = ssh_exec("hostname")
    gpu_out, _, _ = gpu_status()
    return json.dumps({
        "hostname": hostname_out,
        "gpu": json.loads(gpu_out) if gpu_out else None
    })


@mcp.tool()
async def check_connection() -> str:
    """Check SSH connection status."""
    stdout, stderr, code = ssh_exec("echo ok", timeout=5)
    connected = code == 0 and "ok" in stdout
    return json.dumps({
        "connected": connected,
        "host": COMPUTE_HOST,
        "ip": COMPUTE_IP
    })


#----------------------------------
# Execution Tools
#----------------------------------

@mcp.tool()
async def run_command(cmd: str, timeout: int = 60) -> str:
    """Run arbitrary command on desktop."""
    stdout, stderr, code = ssh_exec(cmd, timeout=timeout)
    return json.dumps({
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code
    })


@mcp.tool()
async def run_wsl(cmd: str, timeout: int = 60) -> str:
    """Run command in WSL on desktop."""
    stdout, stderr, code = ssh_exec_wsl(cmd, timeout=timeout)
    return json.dumps({
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code
    })


#----------------------------------
# Tailscale Tools
#----------------------------------

@mcp.tool()
async def tailscale_status() -> str:
    """Get Tailscale status."""
    stdout, stderr, code = ssh_exec("tailscale status 2>/dev/null || wsl -e tailscale status 2>/dev/null")
    if code == 0:
        return stdout
    return f"Error: {stderr}"


#----------------------------------
# Python/Pip Tools
#----------------------------------

@mcp.tool()
async def python_versions() -> str:
    """Get Python and pip versions."""
    stdout, stderr, code = ssh_exec("python --version && pip --version")
    if code == 0:
        return stdout
    return f"Error: {stderr}"


@mcp.tool()
async def check_package(package: str) -> str:
    """Check if a Python package is installed."""
    stdout, stderr, code = ssh_exec(f"pip show {package} 2>/dev/null | findstr Version")
    if code == 0 and stdout:
        return stdout
    return f"{package} not installed"


#----------------------------------
# Main
#----------------------------------

if __name__ == "__main__":
    import sys
    
    if HAS_FASTMCP:
        # Run as FastMCP server
        mcp.run()
    else:
        print("[pheno-gpu-mcp] FastMCP not installed. Installing...")
        print("  pip install fastmcp")
        print("  # or")
        print("  uv tool install pheno-gpu-mcp")
        sys.exit(1)
