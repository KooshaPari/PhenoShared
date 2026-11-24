"""Tool modules for 4SGM MCP server.

This package contains all domain-specific MCP tools organized by category:
- products: Product search and retrieval
- inventory: Inventory management
- pricing: Pricing calculations and discounts
- cart: Shopping cart operations
- orders: Order creation and processing
- shipping: Shipping calculations and tracking
- customers: Customer profiles and preferences
- rfq: Request for Quote management
"""

from .products import register_product_tools
from .inventory import register_inventory_tools
from .pricing import register_pricing_tools
from .cart import register_cart_tools
from .orders import register_orders_tools
from .shipping import register_shipping_tools
from .customers import register_customers_tools
from .rfq import register_rfq_tools

__all__ = [
    "register_product_tools",
    "register_inventory_tools",
    "register_pricing_tools",
    "register_cart_tools",
    "register_orders_tools",
    "register_shipping_tools",
    "register_customers_tools",
    "register_rfq_tools",
]
