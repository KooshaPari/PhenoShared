"""Core renderer for pheno-llms-txt.

Implements §77.2 of `FLEET_100TASK_DAG_V4.md`.
See: https://llmstxt.org for the spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


TEMPLATE = """# llms.txt — {repo_name}

> {tagline}

## Install
{install_block}

## Usage
{usage_block}

## Public API
{api_block}

## Common errors
{errors_block}

## See also
{refs_block}
"""


@dataclass
class LlmConfig:
    """Schema for `pheno-llms-txt.yaml` config."""

    repo_name: str = "repo"
    tagline: str = "One-line description."
    install: list[str] = field(default_factory=lambda: ["pip install <pkg>"])
    usage: list[str] = field(default_factory=lambda: ["<cli> --help"])
    public_api: list[str] = field(default_factory=lambda: ["<module>::<symbol>"])
    common_errors: list[tuple[str, str]] = field(default_factory=lambda: [
        ("error-message", "fix"),
    ])
    references: list[str] = field(default_factory=lambda: [
        "https://llmstxt.org (llms.txt spec)",
    ])

    @classmethod
    def from_dict(cls, d: dict) -> "LlmConfig":
        return cls(
            repo_name=d.get("repo_name", "repo"),
            tagline=d.get("tagline", "One-line description."),
            install=d.get("install", ["pip install <pkg>"]),
            usage=d.get("usage", ["<cli> --help"]),
            public_api=d.get("public_api", ["<module>::<symbol>"]),
            common_errors=[(e, f) for e, f in d.get("common_errors", [["error", "fix"]])],
            references=d.get("references", ["https://llmstxt.org"]),
        )


def render(config: LlmConfig) -> str:
    """Render the llms.txt content."""
    install_block = "\n".join(f"```\n{x}\n```" for x in config.install)
    usage_block = "\n".join(f"```{x}```" if not x.startswith("```") else f"{x}" for x in config.usage)
    api_block = "\n".join(f"- `{x}`" for x in config.public_api)
    errors_block = "\n".join(f"- `{e}`: {f}" for e, f in config.common_errors)
    refs_block = "\n".join(f"- {r}" for r in config.references)
    return TEMPLATE.format(
        repo_name=config.repo_name,
        tagline=config.tagline,
        install_block=install_block,
        usage_block=usage_block,
        api_block=api_block,
        errors_block=errors_block,
        refs_block=refs_block,
    )


def load_config(path: Path | str) -> LlmConfig:
    """Load a `pheno-llms-txt.yaml` from disk, or return defaults if missing."""
    p = Path(path)
    if not p.exists():
        return LlmConfig()
    raw = p.read_text()
    return LlmConfig.from_dict(yaml.safe_load(raw) or {})


def write_llms_txt(config: LlmConfig, dest: Path | str) -> None:
    """Render and write llms.txt to `dest`."""
    p = Path(dest)
    p.write_text(render(config))
