"""Canonical bytes and Ed25519 signing for benchmark replay envelopes."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SIGNATURE_ALGORITHM = "ed25519"
_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def canonical_json_bytes(value: Any) -> bytes:
    """Return the v2 JSON representation: sorted, compact UTF-8, no newline."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def replay_hash(events: list[dict[str, Any]]) -> str:
    """Hash the complete event stream, including its terminal ``run_finished`` event."""

    return hashlib.sha256(canonical_json_bytes(events)).hexdigest()


def signed_envelope_bytes(envelope: Mapping[str, Any]) -> bytes:
    """Return v2 signing bytes, omitting the top-level detached signature object."""

    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    return canonical_json_bytes(unsigned)


@dataclass(frozen=True)
class SigningConfig:
    """Injected replay signing material; the key is never emitted or logged."""

    key_id: str
    private_key_b64: str = field(repr=False)

    @classmethod
    def from_env(cls, environment: Mapping[str, str]) -> SigningConfig:
        """Build a SigningConfig from PHENO_REPLAY_SIGNING_KEY_ID + PRIVATE_KEY_B64."""
        key_id = environment.get("PHENO_REPLAY_SIGNING_KEY_ID", "")
        private_key_b64 = environment.get("PHENO_REPLAY_SIGNING_PRIVATE_KEY_B64", "")
        if not key_id:
            raise ValueError("PHENO_REPLAY_SIGNING_KEY_ID is required")
        if not private_key_b64:
            raise ValueError("PHENO_REPLAY_SIGNING_PRIVATE_KEY_B64 is required")
        return cls(key_id=key_id, private_key_b64=private_key_b64)

    def private_key(self) -> Ed25519PrivateKey:
        """Decode the base64 key and return an Ed25519PrivateKey instance."""
        if not _KEY_ID.fullmatch(self.key_id):
            raise ValueError(
                "replay signing key_id must be 1-128 safe identifier characters"
            )
        try:
            raw_key = base64.b64decode(self.private_key_b64, validate=True)
        except ValueError as exc:
            raise ValueError(
                "replay signing private key must be canonical base64"
            ) from exc
        if len(raw_key) != 32:
            raise ValueError("replay signing private key must encode exactly 32 bytes")
        return Ed25519PrivateKey.from_private_bytes(raw_key)


def sign_envelope(envelope: Mapping[str, Any], config: SigningConfig) -> dict[str, Any]:
    """Attach a detached Ed25519 signature without mutating the caller's envelope."""

    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    signature = config.private_key().sign(signed_envelope_bytes(unsigned))
    return {
        **unsigned,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": config.key_id,
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        },
    }
