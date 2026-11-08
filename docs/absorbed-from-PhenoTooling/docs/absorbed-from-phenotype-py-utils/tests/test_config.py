"""Tests for :mod:`phenotype_py_utils.config`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from phenotype_py_utils.config import ConfigError, load_config


@pytest.fixture(autouse=True)
def _clean_phenotype_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wipe PHENOTYPE_* env vars that may leak from the host environment.

    The host shell often exports ``PHENOTYPE_SOPS_SECRETS=...`` and similar
    config paths; these would otherwise pollute every ``load_config`` call.
    Tests that exercise env-override behavior explicitly set the keys they
    need via ``monkeypatch.setenv``.
    """
    for key in list(os.environ):
        if key.startswith("PHENOTYPE_"):
            monkeypatch.delenv(key, raising=False)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_toml(path: Path, data: str) -> None:
    path.write_text(data, encoding="utf-8")


def test_load_yaml(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"log": {"level": "INFO"}, "port": 8080})
    cfg = load_config(p)
    assert cfg == {"log": {"level": "INFO"}, "port": 8080}


def test_load_yml_extension(tmp_path: Path) -> None:
    p = tmp_path / "config.yml"
    _write_yaml(p, {"a": 1})
    assert load_config(p) == {"a": 1}


def test_load_json(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    _write_json(p, {"name": "phenotype", "version": "0.1.0"})
    assert load_config(p) == {"name": "phenotype", "version": "0.1.0"}


def test_load_toml(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    _write_toml(p, '[log]\nlevel = "INFO"\n')
    cfg = load_config(p)
    assert cfg == {"log": {"level": "INFO"}}


def test_env_override_top_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"log": {"level": "INFO"}})
    monkeypatch.setenv("PHENOTYPE_LOG__LEVEL", "DEBUG")
    cfg = load_config(p)
    assert cfg["log"]["level"] == "DEBUG"


def test_env_override_creates_nested_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {})
    monkeypatch.setenv("PHENOTYPE_NEW__SECTION__KEY", "value")
    cfg = load_config(p)
    assert cfg["new"]["section"]["key"] == "value"


def test_env_override_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"log": {"level": "INFO"}})
    monkeypatch.setenv("PHENOTYPE_LOG__LEVEL", "DEBUG")
    cfg = load_config(p, env_override=False)
    assert cfg["log"]["level"] == "INFO"


def test_env_override_custom_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {})
    monkeypatch.setenv("MYAPP_KEY", "val")
    cfg = load_config(p, env_prefix="MYAPP_")
    assert cfg["key"] == "val"


def test_env_override_unrelated_vars_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"x": 1})
    monkeypatch.setenv("PATH", "/tmp")  # unrelated
    cfg = load_config(p)
    assert cfg == {"x": 1}


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_unsupported_format_raises(tmp_path: Path) -> None:
    p = tmp_path / "config.ini"
    p.write_text("[section]\nkey=val\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Unsupported"):
        load_config(p)


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("key: : :", encoding="utf-8")
    with pytest.raises(ConfigError, match="Could not parse"):
        load_config(p)


def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="Could not parse"):
        load_config(p)


def test_non_dict_root_raises(tmp_path: Path) -> None:
    p = tmp_path / "list.yaml"
    _write_yaml(p, [1, 2, 3])  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="mapping"):
        load_config(p)


def test_empty_yaml_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    assert load_config(p) == {}


def test_env_override_replaces_non_dict_with_dict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the env path crosses a non-dict key, the path is rewritten as a dict."""
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"log": "INFO"})
    monkeypatch.setenv("PHENOTYPE_LOG__LEVEL", "DEBUG")
    cfg = load_config(p)
    assert cfg["log"] == {"level": "DEBUG"}


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib stdlib test only on 3.11+")
def test_toml_3_11_no_extra_dep(tmp_path: Path) -> None:
    """On 3.11+, TOML works without the [toml] extra."""
    p = tmp_path / "c.toml"
    _write_toml(p, 'key = "value"\n')
    assert load_config(p) == {"key": "value"}


def test_env_override_case_insensitive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var parts are lowercased to match YAML / JSON key case."""
    p = tmp_path / "config.yaml"
    _write_yaml(p, {"log": {"level": "INFO"}})
    monkeypatch.setenv("PHENOTYPE_LOG__LEVEL", "DEBUG")
    cfg = load_config(p)
    assert cfg["log"]["level"] == "DEBUG"


def test_unreadable_file_raises_config_error(tmp_path: Path) -> None:
    """If the file is a directory or otherwise unreadable, raise ConfigError."""
    p = tmp_path / "config.yaml"
    p.mkdir()  # a directory, not a file
    with pytest.raises(ConfigError, match="Could not read"):
        load_config(p)
