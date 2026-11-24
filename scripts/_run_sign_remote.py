#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transfer GitHub PAT + sign script to MacBook via Tailscale SSH, run them."""
import base64
import os
import subprocess
import sys
import time

# Force UTF-8 stdio for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

MAC = "<REDACTED>@100.112.14.98"
WORK_DIR = "~/CodeProjects/Phenotype/repos/pheno-harness"

def transfer_token():
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    token = r.stdout.strip()
    b64 = base64.b64encode(token.encode()).decode()
    print(f"Token ({len(token)} bytes) -> /tmp/gh_token on MacBook...")
    # Write to stdin via SSH
    ssh = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", MAC, "base64 -d > /tmp/gh_token"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    ssh.communicate(b64, timeout=15)
    # Verify
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", MAC,
         "bash -c 'wc -c /tmp/gh_token; head -c 4 /tmp/gh_token; echo ...'"],
        capture_output=True, text=True, timeout=15,
    )
    print("On MacBook:", r.stdout.strip())
    print("STDERR:", r.stderr[:200])

def run_on_mac(cmd: str, env: dict = None, timeout: int = 600):
    # Read token directly
    if os.path.exists("/tmp/gh_token"):
        with open("/tmp/gh_token") as fh:
            token = fh.read().strip()
    else:
        token = ""
    full_env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:~/bin:$PATH",
        "GH_TOKEN": token,
        "GITHUB_TOKEN": token,
        "COSIGN_PASSWORD": "test-password",
        "LANG": "en_US.UTF-8",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if env:
        full_env.update(env)
    # Build the env exports
    exports = " ".join(f'{k}={v!r}' for k, v in full_env.items())
    wrapped = f"export {exports} && {cmd}"
    print(f"\n=== Running on MacBook: {cmd[:100]}...")
    # Use --noprofile --norc to skip .bashrc errors
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", MAC,
         f"bash --noprofile --norc -c {wrapped!r}"],
        capture_output=True, text=True, timeout=timeout,
    )
    print(r.stdout[-3000:])
    if r.returncode != 0:
        print(f"RETURN CODE: {r.returncode}")
        print("STDERR:", r.stderr[-1000:])
    return r

def main():
    transfer_token()
    # Push latest scripts to MacBook via SCP-like transfer (since SCP is broken)
    print("\n=== Pushing latest scripts to MacBook...")
    local_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sign_and_upload.py")
    with open(local_script, "rb") as fh:
        script_b64 = base64.b64encode(fh.read()).decode()
    ssh = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", MAC,
         f"base64 -d > {WORK_DIR}/scripts/sign_and_upload.py && chmod +x {WORK_DIR}/scripts/sign_and_upload.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    ssh.communicate(script_b64, timeout=15)
    # Pull latest
    run_on_mac(f"cd {WORK_DIR} && git pull origin main 2>&1 | tail -5", timeout=60)
    # Sign and upload
    r = run_on_mac(
        f"cd {WORK_DIR} && python3 scripts/sign_and_upload.py v0.41-pheno-harness-summit 2>&1",
        timeout=600,
    )
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())
