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
                if handler.get("type") != "command":
                    continue
                command = handler["commandWindows"]
                encoded = command.split()[-1]
                decoded = base64.b64decode(encoded).decode("utf-16le")
                assert "hooks\\codex-windows.ps1" in decoded
                assert target in decoded


@pytest.mark.skipif(os.name != "nt", reason="Windows command dispatch")
def test_windows_launcher_forwards_input_and_failure(tmp_path):
    powershell = shutil.which("powershell")
    program_files = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles")
    if not powershell or not program_files or not (Path(program_files) / "Git/bin/bash.exe").is_file():
        pytest.skip("Git for Windows and PowerShell required")
    plugin = tmp_path / "plugin with spaces"
    hooks = plugin / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(ROOT / "hooks" / "codex-windows.ps1", hooks)
    (hooks / "sg-python.sh").write_text("cat\nexit 7\n", encoding="utf-8")
    data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["commandWindows"]
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
    payload = '{"hook_event_name":"UserPromptSubmit","text":"Unicode: café 你好"}'
    result = subprocess.run(command, input=payload, encoding="utf-8", capture_output=True,
                            env=env, shell=True, timeout=60)
    assert result.returncode == 7, result.stderr
    assert json.loads(result.stdout) == json.loads(payload)
