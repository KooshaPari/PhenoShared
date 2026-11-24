"""Tests for pheno-llms-txt."""

import subprocess
import sys
from pathlib import Path

import pytest
from pheno_llms_txt import LlmConfig, render, load_config, write_llms_txt

PYTHON_AVAILABLE = sys.version_info >= (3, 10)
pytestmark = pytest.mark.skipif(not PYTHON_AVAILABLE, reason="requires Python 3.10+")


def test_render_minimal():
    cfg = LlmConfig(repo_name="myrepo", tagline="A test repo.")
    out = render(cfg)
    assert "# llms.txt — myrepo" in out
    assert "A test repo." in out
    assert "## Install" in out
    assert "## Public API" in out


def test_render_with_overrides():
    cfg = LlmConfig(
        repo_name="thegent",
        tagline="Agent orchestration CLI.",
        install=["pip install thegent"],
        usage=["thegent --help"],
        public_api=["thegent.cli::main"],
        common_errors=[("API key not set", "export THEGENT_API_KEY=...")],
        references=["https://github.com/KooshaPari/thegent"],
    )
    out = render(cfg)
    assert "# llms.txt — thegent" in out
    assert "pip install thegent" in out
    assert "thegent --help" in out
    assert "`thegent.cli::main`" in out
    assert "API key not set" in out
    assert "https://github.com/KooshaPari/thegent" in out


def test_load_config_missing_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.yaml")
    assert cfg.repo_name == "repo"
    assert cfg.tagline == "One-line description."


def test_load_config_real_file(tmp_path):
    cfg_file = tmp_path / "pheno-llms-txt.yaml"
    cfg_file.write_text("""
repo_name: hello
tagline: "Hello world."
install: ["pip install hello"]
""")
    cfg = load_config(cfg_file)
    assert cfg.repo_name == "hello"
    assert "Hello world." in cfg.tagline


def test_write_llms_txt(tmp_path):
    cfg = LlmConfig(repo_name="x", tagline="x test")
    out = tmp_path / "out.txt"
    write_llms_txt(cfg, out)
    assert out.exists()
    text = out.read_text()
    assert "# llms.txt — x" in text


def test_self_validation_under_200_lines():
    """Per V4 §77.2, llms.txt must be ≤200 lines."""
    llms = Path(__file__).resolve().parent.parent / "llms.txt"
    if llms.exists():
        n = sum(1 for _ in llms.read_text().splitlines())
        assert n <= 200, f"llms.txt is {n} lines, must be ≤200"
