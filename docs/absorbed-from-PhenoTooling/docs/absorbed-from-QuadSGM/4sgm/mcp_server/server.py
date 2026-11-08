"""FastMCP 2.13 Server for 4SGM with domain-specific tools."""

from fastmcp import FastMCP
import logging
from typing import Optional

from .repositories import (
    ProductRepository,
    InventoryRepository,
    PricingRepository,
    CartRepository,
    OrderRepository,
    ShippingRepository,
    CustomerRepository,
    RFQRepository,
)
from .repositories.impl import (
    InMemoryProductRepository,
    InMemoryInventoryRepository,
    InMemoryPricingRepository,
    InMemoryCartRepository,
    InMemoryOrderRepository,
    InMemoryShippingRepository,
    InMemoryCustomerRepository,
    InMemoryRFQRepository,
)
from .tools import (
    register_product_tools,
    register_inventory_tools,
    register_pricing_tools,
    register_cart_tools,
    register_orders_tools,
    register_shipping_tools,
    register_customers_tools,
    register_rfq_tools,
)

logger = logging.getLogger(__name__)


# Initialize FastMCP server
mcp = FastMCP(
    "4SGM MCP Server 🚀",
    instructions="""
You are a helpful 4SGM e-commerce assistant with access to comprehensive product,
inventory, shipping, and order management tools. Help customers find products,
manage carts, process orders, and handle inquiries.
""",
)

# Initialize repository instances with in-memory implementations
_product_repo: ProductRepository = InMemoryProductRepository()
_inventory_repo: InventoryRepository = InMemoryInventoryRepository()
_pricing_repo: PricingRepository = InMemoryPricingRepository()
_cart_repo: CartRepository = InMemoryCartRepository()
_order_repo: OrderRepository = InMemoryOrderRepository()
_shipping_repo: Optional[ShippingRepository] = InMemoryShippingRepository()
_customer_repo: Optional[CustomerRepository] = InMemoryCustomerRepository()
_rfq_repo: Optional[RFQRepository] = InMemoryRFQRepository()


def set_repositories(
    product_repo: ProductRepository,
    inventory_repo: InventoryRepository,
    pricing_repo: PricingRepository,
    cart_repo: CartRepository,
    order_repo: OrderRepository,
    shipping_repo: Optional[ShippingRepository] = None,
    customer_repo: Optional[CustomerRepository] = None,
    rfq_repo: Optional[RFQRepository] = None,
):
    """Set repository implementations (called by dependency injection framework)."""
    global _product_repo, _inventory_repo, _pricing_repo, _cart_repo, _order_repo
    global _shipping_repo, _customer_repo, _rfq_repo
    _product_repo = product_repo
    _inventory_repo = inventory_repo
    _pricing_repo = pricing_repo
    _cart_repo = cart_repo
    _order_repo = order_repo
    _shipping_repo = shipping_repo
    _customer_repo = customer_repo
    _rfq_repo = rfq_repo


# Register all tool modules
register_product_tools(mcp, _product_repo)
register_inventory_tools(mcp, _inventory_repo)
register_pricing_tools(mcp, _pricing_repo)
register_cart_tools(mcp, _cart_repo)
register_orders_tools(mcp, _order_repo, _cart_repo, _inventory_repo)
register_shipping_tools(mcp, _shipping_repo)
register_customers_tools(mcp, _customer_repo)
register_rfq_tools(mcp, _rfq_repo)


if __name__ == "__main__":
    # Run the MCP server
    import asyncio

    asyncio.run(mcp.run())
