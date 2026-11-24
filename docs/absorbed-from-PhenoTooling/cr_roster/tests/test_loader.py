"""Tests for cr_roster.loader."""
from __future__ import annotations

import pytest

from cr_roster.loader import load_providers, RosterError


def test_loader_module_imports():
    """The loader module must import cleanly."""
    # If this test runs, the import succeeded.
    assert load_providers is not None
    assert RosterError is not None


def test_providers_yaml_exists(providers_yaml_path):
    """providers.yaml must exist before load_providers() can succeed."""
    assert providers_yaml_path.exists(), (
        f"Missing providers.yaml at {providers_yaml_path}. "
        "Run Task 4 to create it."
    )


def test_load_providers_returns_nonempty_list(providers_yaml_path):
    """load_providers() must return at least one provider (per spec D3 queue)."""
    if not providers_yaml_path.exists():
        pytest.skip("providers.yaml not yet created (Task 4)")
    providers = load_providers()
    assert isinstance(providers, list)
    assert len(providers) >= 6, (
        f"spec D3 lists 6 providers; got {len(providers)}"
    )


def test_load_providers_priority_is_sequential():
    """Per spec D3, providers must be returned in priority order."""
    providers = load_providers()
    priorities = [p["priority"] for p in providers]
    assert priorities == sorted(priorities), (
        f"priorities must be 1..N in order; got {priorities}"
    )
    assert priorities[0] == 1, "first provider must have priority 1"


def test_load_providers_have_required_fields():
    """Every provider must declare the fields the rest of the pipeline consumes."""
    required = {"id", "name", "priority", "free_tier", "quota_per_day", "endpoint"}
    for p in load_providers():
        missing = required - set(p.keys())
        assert not missing, f"provider {p.get('id')!r} missing fields: {missing}"


def test_load_providers_validate_against_schema():
    """The catalog must satisfy its own JSON Schema."""
    try:
        load_providers(validate_schema=True)
    except RosterError as exc:
        pytest.fail(f"schema validation failed: {exc}")

def test_load_providers_rejects_malformed_entry(tmp_path, monkeypatch):
    """A provider missing the 'endpoint' field must be rejected."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        "schema_version: 1\n"
        "providers:\n"
        "  - id: bad\n"
        "    name: Bad\n"
        "    priority: 1\n"
        "    free_tier: 'none'\n"
        "    quota_per_day: 0\n"
        "    auth: api_key\n"
        "    self_hostable: false\n"
    )
    monkeypatch.setattr("cr_roster.loader.PROVIDERS_YAML", bad_yaml)
    with pytest.raises(RosterError):
        load_providers(validate_schema=True)
