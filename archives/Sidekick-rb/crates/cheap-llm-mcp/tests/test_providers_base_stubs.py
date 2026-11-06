"""Provider base protocol stubs for SIDE-TEST-002 (audit remediation)."""

from __future__ import annotations

from cheap_llm_mcp.providers.base import Completion, Message


def test_providers_base_stub_message_dataclass() -> None:
    msg = Message(role="user", content="audit stub")
    assert msg.role == "user"
    assert msg.content == "audit stub"


def test_providers_base_stub_completion_dataclass() -> None:
    completion = Completion(
        text="hello",
        model="stub-model",
        provider="stub-provider",
        input_tokens=10,
        output_tokens=5,
        finish_reason="stop",
    )
    assert completion.text == "hello"
    assert completion.input_tokens == 10
    assert completion.output_tokens == 5
    assert completion.finish_reason == "stop"


def test_providers_base_stub_message_roles_are_documented() -> None:
    for role in ("system", "user", "assistant"):
        msg = Message(role=role, content="x")
        assert msg.role == role
