import base64
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_windows_commands_cover_all_handlers():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for event, groups in hooks.items():
        target = "ensure_agent_sdk.py" if event == "SessionStart" else "security_reminder_hook.py"
        for group in groups:
            for handler in group["hooks"]:
                if handler.get("type") == "command":
                    decoded = base64.b64decode(handler["commandWindows"].split()[-1]).decode("utf-16le")
                    assert "hooks\\codex-windows.ps1" in decoded
                    assert target in decoded


def git_root():
    git = shutil.which("git.exe")
    if not git:
        return None
    for root in list(Path(git).parents)[:3]:
        if (root / "bin/bash.exe").is_file() and (root / "cmd/git.exe").is_file():
            return root
    return None


def launch(tmp_path, env):
    plugin = tmp_path / "plugin with spaces"
    hooks = plugin / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(ROOT / "hooks" / "codex-windows.ps1", hooks)
    (hooks / "sg-python.sh").write_text("cat\nexit 7\n", encoding="utf-8")
    data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["commandWindows"]
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
    payload = '{"hook_event_name":"UserPromptSubmit","text":"Unicode: café 你好"}'
    return subprocess.run(command, input=payload, encoding="utf-8", capture_output=True,
                          env=env, shell=True, timeout=60), payload


@pytest.mark.skipif(os.name != "nt", reason="Windows command dispatch")
def test_windows_launcher_custom_git_and_failure(tmp_path):
    root = git_root()
    if not shutil.which("powershell") or not root:
        pytest.skip("Git for Windows and PowerShell required")
    custom = tmp_path / "custom git location"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(custom), str(root)],
                   check=True, capture_output=True)
    env = os.environ.copy()
    env["PATH"] = str(custom / "cmd") + os.pathsep + env["PATH"]
    env["ProgramW6432"] = str(tmp_path / "no standard git")
    env["ProgramFiles"] = str(tmp_path / "no standard git")
    env["ProgramFiles(x86)"] = str(tmp_path / "no standard git")
    result, payload = launch(tmp_path, env)
    assert result.returncode == 7, result.stderr
    assert json.loads(result.stdout) == json.loads(payload)


@pytest.mark.skipif(os.name != "nt", reason="Windows command dispatch")
def test_windows_launcher_rejects_bare_bash(tmp_path):
    powershell = shutil.which("powershell")
    if not powershell:
        pytest.skip("PowerShell required")
    fake = tmp_path / "unrelated bash"
    fake.mkdir()
    shutil.copy2(os.environ["COMSPEC"], fake / "bash.exe")
    env = os.environ.copy()
    env["PATH"] = str(fake) + os.pathsep + str(Path(powershell).parent)
    for key in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        env[key] = str(tmp_path / "no standard git")
    result, _ = launch(tmp_path, env)
    assert result.returncode != 0
    assert "requires Git for Windows" in result.stderr

@pytest.mark.skipif(os.name != "nt", reason="Windows command dispatch")
def test_windows_launcher_rejects_unrelated_git_and_ancestor_bash(tmp_path):
    powershell = shutil.which("powershell")
    if not powershell:
        pytest.skip("PowerShell required")
    decoy = tmp_path / "decoy"
    (decoy / "tools").mkdir(parents=True)
    (decoy / "bin").mkdir()
    shutil.copy2(os.environ["COMSPEC"], decoy / "tools/git.exe")
    shutil.copy2(os.environ["COMSPEC"], decoy / "bin/bash.exe")
    env = os.environ.copy()
    env["PATH"] = str(decoy / "tools") + os.pathsep + str(Path(powershell).parent)
    for key in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        env[key] = str(tmp_path / "no standard git")
    result, _ = launch(tmp_path, env)
    assert result.returncode != 0
    assert "requires Git for Windows" in result.stderr
