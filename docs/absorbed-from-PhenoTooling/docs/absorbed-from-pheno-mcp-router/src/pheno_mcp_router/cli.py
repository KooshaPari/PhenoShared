from __future__ import annotations

from pathlib import Path

import click

from pheno_mcp_router import config as _config

SERVER_TEMPLATE = '''from pheno_mcp_router import McpRouter

router = McpRouter(
    name="{name}",
    backend_url="{backend_url}",
)
router.add_tier("default", {{"model": "replace-with-model-id"}})
router.serve()
'''

PYPROJECT_TEMPLATE = '''[project]
name = "{name}"
version = "0.1.0"
dependencies = ["pheno-mcp-router"]

[project.scripts]
{name} = "{module}.server:router.serve"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''


@click.group()
def cli() -> None:
    """Create small MCP backend router wrappers."""


@cli.command("init")
@click.argument("name")
def init(name: str) -> None:
    """Scaffold a new MCP server using McpRouter."""
    module = name.replace("-", "_")
    root = Path(name)
    package = root / "src" / module
    package.mkdir(parents=True, exist_ok=False)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "server.py").write_text(
        SERVER_TEMPLATE.format(name=name, backend_url=_config.DEFAULT_BACKEND_URL),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(name=name, module=module),
        encoding="utf-8",
    )
    click.echo(f"created {root}")


if __name__ == "__main__":
    cli()
