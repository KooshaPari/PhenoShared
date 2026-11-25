"""V2 signed benchmark replay contract."""

from __future__ import annotations

import base64
import copy
import json

import pytest

pytest.importorskip("cryptography", reason="cryptography not installed in test venv")

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

from bench.benchmark_envelope import suite_result_to_benchmark_run
from bench.replay_contract import (
    SigningConfig,
    canonical_json_bytes,
    replay_hash,
    signed_envelope_bytes,
)
from bench.types import SuiteResult, TaskResult, TaskStatus


def populated_suite() -> SuiteResult:
    return SuiteResult(
        suite="agentora-mlx-deterministic",
        model="mlx.synthetic.echo",
        n=2,
        passed=2,
        pass_at_1=1.0,
        tokens_in=18,
        tokens_out=12,
        task_results=[
            TaskResult(
                task_id="echo-1",
                status=TaskStatus.OK,
                prompt="echo alpha",
                completion="alpha",
                expected="alpha",
                tool_calls=[
                    {
                        "id": "call-echo-1",
                        "name": "echo",
                        "arguments": {"value": "alpha"},
                        "result": "alpha",
                    }
                ],
            ),
            TaskResult(
                task_id="echo-2",
                status=TaskStatus.OK,
                prompt="echo beta",
                completion="beta",
                expected="beta",
                tool_calls=[],
            ),
        ],
    )


def ephemeral_signing_config() -> tuple[SigningConfig, Ed25519PrivateKey]:
    private_key = Ed25519PrivateKey.generate()
    raw_key = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    return (
        SigningConfig(
            key_id="test-rotation-20260803-a",
            private_key_b64=base64.b64encode(raw_key).decode("ascii"),
        ),
        private_key,
    )


def test_v2_envelope_is_canonical_signed_and_replay_complete() -> None:
    config, private_key = ephemeral_signing_config()

    envelope = suite_result_to_benchmark_run(
        populated_suite(), commit="a" * 40, signing_config=config
    )

    assert envelope["schema_version"] == "2.0.0"
    assert envelope["signature"]["algorithm"] == "ed25519"
    assert envelope["signature"]["key_id"] == config.key_id
    assert envelope["events"][-1]["type"] == "run_finished"
    assert "replay_hash" not in envelope["events"][-1]["details"]
    assert envelope["result"]["replay_hash"] == replay_hash(envelope["events"])
    assert envelope["result"]["replay_hash"] != replay_hash(envelope["events"][:-1])
    assert canonical_json_bytes({"z": "mu", "a": "alpha"}) == b'{"a":"alpha","z":"mu"}'

    signature = base64.b64decode(envelope["signature"]["signature_b64"], validate=True)
    private_key.public_key().verify(signature, signed_envelope_bytes(envelope))


def test_tampering_signed_content_invalidates_signature() -> None:
    config, private_key = ephemeral_signing_config()
    envelope = suite_result_to_benchmark_run(
        populated_suite(), commit="a" * 40, signing_config=config
    )
    signature = base64.b64decode(envelope["signature"]["signature_b64"], validate=True)
    tampered = copy.deepcopy(envelope)
    tampered["result"]["status"] = "failed"

    with pytest.raises(InvalidSignature):
        private_key.public_key().verify(signature, signed_envelope_bytes(tampered))


def test_signature_field_is_excluded_from_signed_bytes() -> None:
    config, _ = ephemeral_signing_config()
    envelope = suite_result_to_benchmark_run(
        populated_suite(), commit="a" * 40, signing_config=config
    )
    changed_signature = copy.deepcopy(envelope)
    changed_signature["signature"]["signature_b64"] = "different-wire-value"

    assert signed_envelope_bytes(envelope) == signed_envelope_bytes(changed_signature)


def test_signing_config_is_runtime_injected_and_rejects_missing_values() -> None:
    config, _ = ephemeral_signing_config()
    injected = {
        "PHENO_REPLAY_SIGNING_KEY_ID": config.key_id,
        "PHENO_REPLAY_SIGNING_PRIVATE_KEY_B64": config.private_key_b64,
    }

    assert SigningConfig.from_env(injected) == config
    with pytest.raises(ValueError, match="PHENO_REPLAY_SIGNING_KEY_ID"):
        SigningConfig.from_env({})


def test_v2_schema_declares_non_placeholder_signature_contract() -> None:
    schema_path = __file__.replace(
        "test_signed_benchmark_replay.py", "fixtures/benchmark_run.v2.schema.json"
    )
    schema = json.loads(open(schema_path, encoding="utf-8").read())

    assert schema["properties"]["schema_version"] == {"const": "2.0.0"}
    signature = schema["properties"]["signature"]
    assert signature["required"] == ["algorithm", "key_id", "signature_b64"]
    assert signature["properties"]["algorithm"] == {"const": "ed25519"}


def test_v2_schema_validates_the_signed_producer_output() -> None:
    config, _ = ephemeral_signing_config()
    envelope = suite_result_to_benchmark_run(
        populated_suite(), commit="a" * 40, signing_config=config
    )
    schema_path = __file__.replace(
        "test_signed_benchmark_replay.py", "fixtures/benchmark_run.v2.schema.json"
    )
    schema = json.loads(open(schema_path, encoding="utf-8").read())

    assert list(Draft202012Validator(schema).iter_errors(envelope)) == []
