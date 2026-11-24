"""Tests for teammates module."""

import asyncio
from pathlib import Path

import pytest
from harness.teammates import (
    MAX_TASK_DESCRIPTION_BYTES,
    CodexExecutor,
    DelegationProtocol,
    DelegationRequest,
    DelegationStatus,
    HealthMonitor,
    HealthStatus,
    Priority,
    Teammate,
    TeammateRegistry,
)
from pydantic import ValidationError


class TestTeammate:
    """Test Teammate model."""

    def test_teammate_creation(self):
        t = Teammate(id="test-agent", name="Test Agent", role="coder", description="A test agent")
        assert t.id == "test-agent"
        assert t.role == "coder"

    def test_teammate_defaults(self):
        t = Teammate(id="default-agent", name="Default", role="general", description="Test")
        assert t.max_concurrent == 1
        assert t.timeout_seconds == 300
        assert t.tools == []


class TestDelegationRequest:
    """Test DelegationRequest model."""

    def test_delegation_request_defaults(self):
        req = DelegationRequest(teammate_id="agent-1", task_description="Do something")
        assert req.priority == Priority.NORMAL
        assert req.timeout_seconds == 300

    def test_delegation_request_custom(self):
        req = DelegationRequest(
            teammate_id="agent-1",
            task_description="Do something",
            priority=Priority.HIGH,
            timeout_seconds=600,
        )
        assert req.priority == Priority.HIGH
        assert req.timeout_seconds == 600

    def test_delegation_request_rejects_oversized_prompt(self):
        with pytest.raises(ValidationError, match="task_description"):
            DelegationRequest(teammate_id="agent-1", task_description="x" * 32769)


class TestTeammateRegistry:
    """Test TeammateRegistry."""

    def test_registry_empty_init(self):
        registry = TeammateRegistry()
        assert registry._teammates == {}

    def test_registry_discover_empty_dir(self, tmp_path):
        registry = TeammateRegistry(agents_dir=tmp_path)
        teammates = registry.discover()
        assert teammates == {}

    def test_registry_get_nonexistent(self):
        registry = TeammateRegistry()
        assert registry.get("nonexistent") is None

    def test_registry_list_all_empty(self):
        registry = TeammateRegistry()
        assert registry.list_all() == []

    def test_registry_list_by_role_empty(self):
        registry = TeammateRegistry()
        assert registry.list_by_role("coder") == []


class TestDelegationProtocol:
    """Test DelegationProtocol."""

    def test_protocol_init(self):
        protocol = DelegationProtocol()
        assert protocol._delegations == {}
        assert protocol._results == {}

    def test_protocol_get_status_none(self):
        protocol = DelegationProtocol()
        assert protocol.get_status("fake-id") is None

    def test_protocol_cancel_delegation_not_found(self):
        protocol = DelegationProtocol()
        result = protocol.cancel_delegation("fake-id")
        assert result is False

    def test_protocol_cancel_delegation_found(self, tmp_path):
        protocol = DelegationProtocol(state_dir=tmp_path)
        # Add a fake delegation
        req = DelegationRequest(teammate_id="test", task_description="test")
        protocol._delegations["test-id"] = req

        result = protocol.cancel_delegation("test-id")
        assert result is True
        assert protocol.get_status("test-id").status == DelegationStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_protocol_status_survives_new_process_instance(self, tmp_path):
        class Executor:
            async def execute(self, _request):
                return {"output": "done", "evidence": []}

        first = DelegationProtocol(state_dir=tmp_path)
        result = await first.delegate(
            DelegationRequest(teammate_id="test", task_description="test"), Executor()
        )

        restored = DelegationProtocol(state_dir=tmp_path).get_status(result.delegation_id)
        assert restored is not None
        assert restored.status == DelegationStatus.COMPLETED


class TestCodexExecutor:
    """Test CodexExecutor."""

    def test_executor_init_default(self):
        executor = CodexExecutor()
        assert executor.profile == "default"

    def test_executor_init_custom(self):
        executor = CodexExecutor(profile="custom", workdir=Path("/tmp"))
        assert executor.profile == "custom"

    @pytest.mark.asyncio
    async def test_executor_prompt_cap_preserves_utf8_byte_limit(self, monkeypatch):
        # Traces to: FR-HELIOS-IO-006 (bounded delegated evidence input).
        captured = {}

        class Process:
            returncode = 0

            async def communicate(self):
                return b"", b""

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured["args"] = args
            return Process()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        request = DelegationRequest.model_construct(
            teammate_id="agent-1", task_description="x" + "é" * (MAX_TASK_DESCRIPTION_BYTES // 2)
        )

        await CodexExecutor().execute(request)

        prompt = captured["args"][-1]
        assert len(prompt.encode("utf-8")) <= MAX_TASK_DESCRIPTION_BYTES
        assert "�" not in prompt


class TestHealthMonitor:
    """Test HealthMonitor."""

    def test_monitor_init(self):
        monitor = HealthMonitor()
        assert monitor._agents == {}

    def test_monitor_register_agent(self):
        monitor = HealthMonitor()
        monitor.register_agent("agent-1", 12345)
        assert "agent-1" in monitor._agents

    def test_monitor_unregister_agent(self):
        monitor = HealthMonitor()
        monitor.register_agent("agent-1", 12345)
        monitor.unregister_agent("agent-1")
        assert "agent-1" not in monitor._agents

    @pytest.mark.asyncio
    async def test_monitor_check_health_unknown(self):
        monitor = HealthMonitor()
        status = await monitor.check_health("nonexistent")
        assert status == HealthStatus.UNKNOWN


class TestPriority:
    """Test Priority enum."""

    def test_priority_values(self):
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.NORMAL.value == "normal"
        assert Priority.LOW.value == "low"


class TestDelegationStatus:
    """Test DelegationStatus enum."""

    def test_status_values(self):
        assert DelegationStatus.PENDING.value == "pending"
        assert DelegationStatus.RUNNING.value == "running"
        assert DelegationStatus.COMPLETED.value == "completed"
        assert DelegationStatus.FAILED.value == "failed"
        assert DelegationStatus.CANCELLED.value == "cancelled"


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.SLOW.value == "slow"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.CRASHED.value == "crashed"
