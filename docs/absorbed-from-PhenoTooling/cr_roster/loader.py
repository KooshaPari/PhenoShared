"""Loader for the cr_roster provider catalog.

Public API:
    load_providers(validate_schema: bool = False) -> list[dict]

Raises:
    RosterError: when the YAML is missing, malformed, or fails schema validation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import json

import yaml

ROSTER_ROOT = Path(__file__).resolve().parent
PROVIDERS_YAML = ROSTER_ROOT / "providers.yaml"
SCHEMA_JSON = ROSTER_ROOT / "schema.json"


class RosterError(Exception):
    """Raised when the roster cannot be loaded or validated."""


def load_providers(validate_schema: bool = False) -> list[dict[str, Any]]:
    """Load and return the provider catalog as a list of dicts.

    Args:
        validate_schema: When True, validate the YAML against schema.json.

    Returns:
        Providers sorted by ascending ``priority`` (1 = highest).

    Raises:
        RosterError: if the file is missing, malformed, or fails validation.
    """
    if not PROVIDERS_YAML.exists():
        raise RosterError(
            f"providers.yaml not found at {PROVIDERS_YAML}. "
            "See docs/superpowers/specs/2026-09-09-automated-code-review-workflow-orchestration-design.md §3 SP1."
        )

    try:
        with PROVIDERS_YAML.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise RosterError(f"providers.yaml is malformed: {exc}") from exc

    if not isinstance(data, dict) or "providers" not in data:
        raise RosterError(
            "providers.yaml must be a mapping with a top-level 'providers' key"
        )

    providers = data["providers"]
    if not isinstance(providers, list):
        raise RosterError("'providers' must be a list")

    if validate_schema:
        _validate_against_schema(data)

    providers.sort(key=lambda p: p.get("priority", 10_000))
    return providers


def _validate_against_schema(data: dict[str, Any]) -> None:
    """Validate the loaded YAML data against schema.json.

    Performs JSON Schema validation and additional business-rule checks:
    - provider IDs must be unique
    - provider priorities must be unique and contiguous starting at 1
    """
    schema_version = data.get("schema_version")
    providers = data["providers"]

    if not SCHEMA_JSON.exists():
        raise RosterError(
            f"schema.json not found at {SCHEMA_JSON}; cannot validate."
        )
    try:
        import jsonschema  # local import so the dep is optional for non-validating callers
    except ImportError as exc:
        raise RosterError(
            "jsonschema is not installed; install with `pip install jsonschema`"
        ) from exc

    with SCHEMA_JSON.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    # Validate against the actual declared schema_version, not a hardcoded value.
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors({"schema_version": schema_version, "providers": providers}),
        key=lambda e: e.path,
    )

    # --- Business-rule checks beyond JSON Schema ---
    # Unique provider IDs
    ids = [p.get("id") for p in providers]
    seen_ids: set[str] = set()
    for idx, pid in enumerate(ids):
        if pid in seen_ids:
            errors.append(
                jsonschema.ValidationError(
                    f"Duplicate provider id '{pid}' at index {idx}",
                    path=[idx, "id"],
                )
            )
        seen_ids.add(pid)

    # Unique, contiguous priorities starting at 1
    priorities = sorted(p.get("priority", 0) for p in providers)
    expected = list(range(1, len(providers) + 1))
    if priorities != expected:
        errors.append(
            jsonschema.ValidationError(
                f"Provider priorities must be unique and contiguous 1..{len(providers)}; "
                f"got {priorities}",
                path=["providers"],
            )
        )

    if errors:
        msgs = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
        raise RosterError("schema validation failed:\n  - " + "\n  - ".join(msgs))
