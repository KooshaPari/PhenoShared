# Watcher wrapper for N22 disk-budget watchdog (Windows Task Scheduler).
# Loops the read-only disk_budget_watch.ps1 check every 30 min; survives
# until the session ends (Task Scheduler only restarts on next logon).
# Register via:
#   schtasks /create /tn "PhenoDiskBudgetWatch" /tr '"C:\\Python313\\pythonw.exe" "C:\\Users\\koosh\\pheno-harness\\scripts\\_disk_budget_loop.py"' /sc onlogon /f
# Verify with: schtasks /query /tn "PhenoDiskBudgetWatch" /fo LIST
# Restored 2026-08-19 after wipe — includes rotation keep 200.

import pathlib
import subprocess
import sys
import time

SCRIPT = r"C:\Users\koosh\pheno-harness\scripts\disk_budget_watch.ps1"
STATE_DIR = pathlib.Path(r"C:\Users\koosh\pheno-harness\state\disk_budget_log")
INTERVAL_S = 30 * 60
KEEP_STATUS = 200  # ~4 days at 30m cadence


def prune_status_log() -> None:
    try:
        if not STATE_DIR.is_dir():
            return
        files = sorted(
            STATE_DIR.glob("disk_budget_status_*.json"), key=lambda p: p.stat().st_mtime
        )
        excess = len(files) - KEEP_STATUS
        for p in files[: max(0, excess)]:
            try:
                p.unlink()
            except Exception:
                pass
    except Exception:
        pass


def run_once() -> None:
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SCRIPT],
        capture_output=True,
        text=True,
        timeout=180,
    )
    prune_status_log()


if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            sys.stderr.write(f"disk_budget_loop tick error: {e!r}\n")
        time.sleep(INTERVAL_S)
