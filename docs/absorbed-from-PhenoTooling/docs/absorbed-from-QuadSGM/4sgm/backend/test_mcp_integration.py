#!/usr/bin/env python
"""Tests for MCP integration."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_mcp_client_wrapper():
    """Test MCP client wrapper."""
    print("\nTesting MCP Client Wrapper...")
    try:
        from mcp_client_wrapper import MCPClientWrapper

        # Create wrapper
        wrapper = MCPClientWrapper("http://localhost:3000/mcp")

        # Test connection
        connected = await wrapper.connect()
        assert connected, "Should connect to MCP server"
        print("✅ MCP client connected")

        # Test tool loading
        tools = await wrapper.load_tools()
        assert len(tools) > 0, "Should load tools"
        print(f"✅ Loaded {len(tools)} tools")

        # Test tool listing
        tool_list = await wrapper.list_tools()
        assert len(tool_list) > 0, "Should list tools"
        print(f"✅ Listed {len(tool_list)} tools")

        # Test tool names
        tool_names = [t["name"] for t in tool_list]
        expected_tools = [
            "get_product",
            "search_products",
            "get_inventory",
            "create_cart",
            "add_to_cart",
            "calculate_shipping",
            "create_order",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Should have {tool_name} tool"

        print("✅ All expected tools present")

        await wrapper.close()
        return True
    except Exception as e:
        print(f"❌ MCP client wrapper test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_mcp_tool_calling():
    """Test calling MCP tools."""
    print("\nTesting MCP Tool Calling...")
    try:
        from mcp_client_wrapper import MCPClientWrapper

        wrapper = MCPClientWrapper("http://localhost:3000/mcp")
        await wrapper.connect()

        # Test get_product tool
        result = await wrapper.call_tool("get_product", product_id="PROD-001")
        assert result is not None, "Should get product"
        assert "id" in result, "Result should have id"
        print(f"✅ get_product tool works: {result}")

        # Test search_products tool
        result = await wrapper.call_tool("search_products", query="laptop", limit=5)
        assert isinstance(result, list), "Should return list"
        assert len(result) > 0, "Should find products"
        print(f"✅ search_products tool works: found {len(result)} products")

        # Test get_inventory tool
        result = await wrapper.call_tool("get_inventory", product_id="PROD-001")
        assert "in_stock" in result, "Should have inventory info"
        print(f"✅ get_inventory tool works: {result['in_stock']} in stock")

        # Test create_cart tool
        result = await wrapper.call_tool("create_cart", user_id="USER-123")
        assert "cart_id" in result, "Should create cart"
        print(f"✅ create_cart tool works: {result['cart_id']}")

        await wrapper.close()
        return True
    except Exception as e:
        print(f"❌ MCP tool calling test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_mcp_pricing_tools():
    """Test pricing and discount tools."""
    print("\nTesting MCP Pricing Tools...")
    try:
        from mcp_client_wrapper import MCPClientWrapper

        wrapper = MCPClientWrapper("http://localhost:3000/mcp")
        await wrapper.connect()

        # Test get_pricing
        result = await wrapper.call_tool("get_pricing", product_id="PROD-001", quantity=100)
        assert "unit_price" in result, "Should have unit price"
        assert "total" in result, "Should have total"
        print(f"✅ get_pricing: ${result['unit_price']} per unit, ${result['total']} total")

        # Test apply_discount
        result = await wrapper.call_tool(
            "apply_discount", product_id="PROD-001", discount_code="SAVE10"
        )
        assert "discount_rate" in result, "Should have discount rate"
        print(f"✅ apply_discount: {result['discount_rate'] * 100}% off")

        # Test get_promotions
        result = await wrapper.call_tool("get_promotions")
        assert isinstance(result, list), "Should return list"
        assert len(result) > 0, "Should have promotions"
        print(f"✅ get_promotions: {len(result)} active promotions")

        await wrapper.close()
        return True
    except Exception as e:
        print(f"❌ MCP pricing tools test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_mcp_shipping_tools():
    """Test shipping tools."""
    print("\nTesting MCP Shipping Tools...")
    try:
        from mcp_client_wrapper import MCPClientWrapper

        wrapper = MCPClientWrapper("http://localhost:3000/mcp")
        await wrapper.connect()

        # Test calculate_shipping
        result = await wrapper.call_tool(
            "calculate_shipping", origin="CA", destination="NY", weight_lbs=10.0
        )
        assert "cost" in result, "Should have cost"
        print(f"✅ calculate_shipping: ${result['cost']}")

        # Test get_shipping_methods
        result = await wrapper.call_tool("get_shipping_methods")
        assert isinstance(result, list), "Should return list"
        assert len(result) > 0, "Should have methods"
        print(f"✅ get_shipping_methods: {len(result)} methods available")

        # Test estimate_delivery
        result = await wrapper.call_tool(
            "estimate_delivery", destination="NY", shipping_method="express"
        )
        assert "estimated_days" in result, "Should have estimated days"
        print(f"✅ estimate_delivery: {result['estimated_days']} days")

        await wrapper.close()
        return True
    except Exception as e:
        print(f"❌ MCP shipping tools test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Integration Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("MCP Client Wrapper", await test_mcp_client_wrapper()))
    results.append(("MCP Tool Calling", await test_mcp_tool_calling()))
    results.append(("MCP Pricing Tools", await test_mcp_pricing_tools()))
    results.append(("MCP Shipping Tools", await test_mcp_shipping_tools()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return all(result for _, result in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
