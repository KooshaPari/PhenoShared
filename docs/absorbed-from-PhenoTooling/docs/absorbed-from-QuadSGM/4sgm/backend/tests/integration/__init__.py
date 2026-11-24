"""Integration tests for MCP chain workflows.

This module contains comprehensive integration tests that validate multi-tool
workflow chains across the 4SGM MCP system. Tests verify:

1. Product → Cart → Order workflow
2. Shipping calculation workflows
3. Pricing → Discount workflows
4. RFQ creation → acceptance workflows
5. Error recovery in chains
6. Cross-tool data consistency

Tests use the mock repository adapter to avoid database dependencies while
maintaining realistic workflow scenarios.
"""
