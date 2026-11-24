"""Entrypoint for ``python -m pheno_mcp``.

Starts the configured pheno_mcp server over MCP stdio transport so that
any MCP client (Claude Desktop, mcp-use, etc.) can connect by launching:

    python -m pheno_mcp

Environment variables read at startup:

- ``PARPOURA_BASE_URL`` — base URL for Parpoura API calls (default
  ``http://localhost:8001``).
- ``PHENO_MCP_HOST`` — host to bind (default ``127.0.0.1``).
- ``PHENO_MCP_PORT`` — port to bind for HTTP transport (default ``8000``).
"""

from __future__ import annotations

import os

from pheno_mcp.server import ServerConfig
from pheno_mcp.transport import run_stdio


def main() -> None:
    """Run pheno_mcp over MCP stdio transport."""
    config = ServerConfig(
        name="pheno-mcp",
        host=os.environ.get("PHENO_MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PHENO_MCP_PORT", "8000")),
    )
    run_stdio(config)


if __name__ == "__main__":
    main()
