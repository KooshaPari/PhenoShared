"""Order creation and processing tools for 4SGM MCP server."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models import OrderResponse
from ..models.order import CartItem as OrderCartItem
from ..exceptions import OrderCreationError, InvalidOrderDataError
from ..repositories import OrderRepository, CartRepository, InventoryRepository

logger = logging.getLogger(__name__)


def register_orders_tools(
    mcp,
    order_repo: OrderRepository,
    cart_repo: CartRepository,
    inventory_repo: InventoryRepository,
):
    """Register order tools with the FastMCP instance."""

    @mcp.tool
    async def create_order(
        cart_id: str,
        user_id: str,
        shipping_address: str,
        items: Optional[list[dict]] = None,
        subtotal: Optional[float] = None,
        tax: Optional[float] = None,
        shipping_cost: Optional[float] = None,
        total: Optional[float] = None,
    ) -> dict:
        """Create order from cart.

        Converts cart into confirmed order with tracking number and status.
        Optionally accepts order totals for validation.

        Args:
            cart_id: Cart identifier to convert (minimum 1 character)
            user_id: User identifier (minimum 1 character)
            shipping_address: Shipping address (minimum 10 characters)
            items: Optional list of order items
            subtotal: Optional order subtotal
            tax: Optional tax amount
            shipping_cost: Optional shipping cost
            total: Optional order total

        Returns:
            OrderResponse with order_id, status, tracking_number, and timestamps.

        Raises:
            CartNotFoundError: If cart doesn't exist
            InvalidOrderDataError: If required fields are invalid
            OrderCreationError: If order creation fails
        """
        try:
            if not order_repo:
                raise OrderCreationError("Order repository not initialized")

            # Validate inputs
            if not cart_id or len(cart_id.strip()) == 0:
                raise InvalidOrderDataError("Cart ID cannot be empty")

            if not user_id or len(user_id.strip()) == 0:
                raise InvalidOrderDataError("User ID cannot be empty")

            if not shipping_address or len(shipping_address.strip()) < 10:
                raise InvalidOrderDataError(
                    "Shipping address must be at least 10 characters"
                )

            # Convert shipping address string to dict
            shipping_address_dict = {"address": shipping_address}

            # Create order
            order = await order_repo.create(
                cart_id=cart_id,
                customer_id=user_id,
                shipping_address=shipping_address_dict,
                items=items,
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                total=total,
            )

            if not order:
                raise OrderCreationError("Failed to create order")

            # Convert items to CartItem objects if present
            order_items = None
            if items:
                order_items = [
                    OrderCartItem(**item) if isinstance(item, dict) else item
                    for item in items
                ]

            # Parse created_at timestamp
            created_at = datetime.now(timezone.utc)
            if order.created_at:
                if isinstance(order.created_at, str):
                    created_at = datetime.fromisoformat(order.created_at)
                elif isinstance(order.created_at, datetime):
                    created_at = order.created_at

            response = OrderResponse(
                order_id=order.id,
                cart_id=cart_id,
                user_id=user_id,
                status=order.status,
                created_at=created_at,
                shipping_address=shipping_address,
                tracking_number=order.tracking_number
                or f"TRK-{uuid.uuid4().hex[:8].upper()}",
                items=order_items,
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                total=total,
            )
            return response.model_dump(exclude_none=True)

        except (InvalidOrderDataError, OrderCreationError):
            raise
        except Exception as e:
            logger.error(f"Error creating order for cart {cart_id}: {str(e)}")
            raise OrderCreationError(f"Failed to create order: {str(e)}")

    # ============================================================================
    # SHIPPING TOOLS (Agent 7)
    # ============================================================================
