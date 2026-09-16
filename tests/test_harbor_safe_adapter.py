from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "harness" / "harbor" / "terminus_safe.py").read_text(encoding="utf-8")
LAUNCHER = (ROOT / "harbor_cli" / "run_tbench_local.ps1").read_text(encoding="utf-8")
SHIM = (ROOT / "scripts" / "harbor_podman_compat.py").read_text(encoding="utf-8")


def test_safe_adapter_bounds_output_recovery_and_preserves_partial_context():
    assert "class SafeTerminus2(Terminus2)" in SOURCE
    assert "max_output_retries: int = 2" in SOURCE
    assert "for attempt in range(self._max_output_retries + 1)" in SOURCE
    assert 'chat.messages.append({"role": "assistant", "content": truncated})' in SOURCE
    assert "return await self._query_llm" not in SOURCE
    assert "asyncio.wait_for" in SOURCE
    assert "terminal_command_timeout_sec" in SOURCE


def test_local_launcher_uses_repo_adapter_and_nonzero_completion_budget():
    assert "harness.harbor.terminus_safe:SafeTerminus2" in LAUNCHER
    assert '"--agent-kwarg", "max_output_retries=$MaxOutputRetries"' in LAUNCHER
    assert '"--agent-kwarg", "record_terminal_session=false"' in LAUNCHER
    assert '"--agent-kwarg", "terminal_command_timeout_sec=30"' in LAUNCHER
    assert "[int]$MaxTokens = 2048" in LAUNCHER
    assert "$env:PYTHONPATH = $Root" in LAUNCHER
    assert "[int]$ServerReadyTimeoutSec = 300" in LAUNCHER
    assert "Wait-LocalServer -TimeoutSec $ServerReadyTimeoutSec" in LAUNCHER
    assert "[string[]]$IncludeTaskName" in LAUNCHER
    assert "foreach ($taskName in $IncludeTaskName)" in LAUNCHER
    assert '-Recurse -Filter "harbor.exe"' not in LAUNCHER
    assert "Prefer the validated Harbor 0.18.0 environment" in LAUNCHER
    assert '"run", "-c", $Config' in LAUNCHER
    assert '"-p", $DatasetPath' in LAUNCHER
    assert "$probe.WaitForExit(120000)" in LAUNCHER
    assert "Start-Job -ScriptBlock" not in LAUNCHER
    assert "scripts\\harbor_podman_compat.py" in LAUNCHER


def test_podman_shim_only_bypasses_duplicate_harbor_preflight():
    assert "from harbor.cli.main import app" in SHIM
    assert "DockerEnvironment.preflight = classmethod(_validated_by_launcher)" in SHIM
    assert 'command[:3] == ["up", "--detach", "--wait"]' in SHIM
    assert 'command = ["up", "--detach", *command[3:]]' in SHIM
    assert "app()" in SHIM
    assert "subprocess" not in SHIM
