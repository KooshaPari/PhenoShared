"""Tools module for pheno-mcp.

Provides FastMCP decorators and tool registry abstraction.
"""

from . import tool_registry
from .decorators import mcp_tool

__all__ = ["mcp_tool", "tool_registry"]
