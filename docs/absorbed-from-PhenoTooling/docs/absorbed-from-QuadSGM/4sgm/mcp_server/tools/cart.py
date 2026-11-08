"""Shopping cart management tools for 4SGM MCP server."""

import logging

from ..models import (
    CartResponse,
    AddToCartResponse,
    RemoveFromCartResponse,
    CartTotalResponse,
    CartValidationResponse,
)
from ..exceptions import CartError, CartNotFoundError, CartValidationError
from ..repositories import CartRepository

logger = logging.getLogger(__name__)


def register_cart_tools(mcp, cart_repo: CartRepository):
    """Register cart tools with the FastMCP instance."""

    @mcp.tool
    async def create_cart(user_id: str) -> dict:
        """Create a new shopping cart.

        Initializes new cart for user with unique ID, timestamp, and empty item list.

        Args:
            user_id: The user identifier (minimum 1 character)

        Returns:
            CartResponse with new cart_id, user_id, creation timestamp, and empty items.

        Raises:
            CartError: If cart creation fails
        """
        try:
            if not cart_repo:
                raise CartError("Cart repository not initialized")

            if not user_id or len(user_id.strip()) == 0:
                raise CartError("User ID cannot be empty")

            cart = await cart_repo.create_cart(user_id)

            response = CartResponse(
                cart_id=cart["cart_id"],
                user_id=cart["user_id"],
                items=cart.get("items", []),
                total=cart.get("total", 0.0),
                created_at=cart.get("created_at", datetime.now(timezone.utc)),
            )
            return response.model_dump()

        except CartError:
            raise
        except Exception as e:
            logger.error(f"Error creating cart for user {user_id}: {str(e)}")
            raise CartError(f"Failed to create cart: {str(e)}")

    @mcp.tool
    async def add_to_cart(cart_id: str, product_id: str, quantity: int) -> dict:
        """Add item to cart.

        Adds product to cart with specified quantity. Updates existing item if
        product already in cart.

        Args:
            cart_id: Cart identifier (minimum 1 character)
            product_id: Product to add (minimum 1 character)
            quantity: Quantity to add (minimum 1)

        Returns:
            AddToCartResponse with product_id, quantity, unit_price, line_total.

        Raises:
            CartNotFoundError: If cart doesn't exist
            CartError: If add operation fails
        """
        try:
            if not cart_repo:
                raise CartError("Cart repository not initialized")

            if not cart_id or len(cart_id.strip()) == 0:
                raise CartError("Cart ID cannot be empty")

            if not product_id or len(product_id.strip()) == 0:
                raise CartError("Product ID cannot be empty")

            if quantity < 1:
                raise CartError("Quantity must be at least 1")

            # Get product pricing first
            if not _pricing_repo:
                raise CartError("Pricing repository not initialized")

            pricing = await _pricing_repo.get_pricing(product_id, 1)
            unit_price = pricing["unit_price"]

            # Add to cart
            await cart_repo.add_item(cart_id, product_id, quantity, unit_price)

            response = AddToCartResponse(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=unit_price * quantity,
                status="added",
            )
            return response.model_dump()

        except CartNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error adding to cart {cart_id}: {str(e)}")
            raise CartError(f"Failed to add to cart: {str(e)}")

    @mcp.tool
    async def remove_from_cart(cart_id: str, product_id: str) -> dict:
        """Remove item from cart.

        Removes product from cart completely (all quantities).

        Args:
            cart_id: Cart identifier (minimum 1 character)
            product_id: Product to remove (minimum 1 character)

        Returns:
            RemoveFromCartResponse with removal status.

        Raises:
            CartNotFoundError: If cart doesn't exist
            CartError: If removal fails
        """
        try:
            if not cart_repo:
                raise CartError("Cart repository not initialized")

            if not cart_id or len(cart_id.strip()) == 0:
                raise CartError("Cart ID cannot be empty")

            if not product_id or len(product_id.strip()) == 0:
                raise CartError("Product ID cannot be empty")

            removed = await cart_repo.remove_item(cart_id, product_id)
            if not removed:
                raise CartError(f"Product {product_id} not in cart")

            response = RemoveFromCartResponse(
                cart_id=cart_id,
                product_id=product_id,
                status="removed",
            )
            return response.model_dump()

        except CartError:
            raise
        except Exception as e:
            logger.error(f"Error removing from cart {cart_id}: {str(e)}")
            raise CartError(f"Failed to remove from cart: {str(e)}")

    @mcp.tool
    async def calculate_cart_total(cart_id: str, items: list[dict]) -> dict:
        """Calculate cart total with tax and shipping.

        Computes subtotal from items, applies 8% tax, adds $50 flat shipping,
        and returns final total.

        Args:
            cart_id: Cart identifier (minimum 1 character)
            items: List of cart items with quantity and price keys

        Returns:
            CartTotalResponse with subtotal, tax, shipping, and total.

        Raises:
            CartValidationError: If items list is invalid
            CartError: If calculation fails
        """
        try:
            if not cart_id or len(cart_id.strip()) == 0:
                raise CartError("Cart ID cannot be empty")

            if not items or len(items) == 0:
                raise CartValidationError("Cart must contain at least one item")

            subtotal = 0.0
            for item in items:
                quantity = item.get("quantity", 1)
                price = item.get("price", 0)

                if quantity < 1:
                    raise CartValidationError("Item quantity must be at least 1")

                if price < 0:
                    raise CartValidationError("Item price cannot be negative")

                subtotal += quantity * price

            tax = subtotal * 0.08
            shipping = 50.0
            total = subtotal + tax + shipping

            response = CartTotalResponse(
                cart_id=cart_id,
                subtotal=round(subtotal, 2),
                tax=round(tax, 2),
                shipping=shipping,
                total=round(total, 2),
            )
            return response.model_dump()

        except (CartValidationError, CartError):
            raise
        except Exception as e:
            logger.error(f"Error calculating cart total for {cart_id}: {str(e)}")
            raise CartError(f"Failed to calculate cart total: {str(e)}")

    @mcp.tool
    async def validate_cart(cart_id: str, items: list[dict]) -> dict:
        """Validate cart contents.

        Ensures cart is not empty and all items have valid quantities.
        Inventory availability must be checked separately with get_inventory.

        Args:
            cart_id: Cart identifier (minimum 1 character)
            items: List of cart items to validate

        Returns:
            CartValidationResponse with validation status and any errors.

        Raises:
            CartError: If validation operation fails
        """
        try:
            if not cart_id or len(cart_id.strip()) == 0:
                raise CartError("Cart ID cannot be empty")

            errors = []
            item_count = len(items)

            if item_count == 0:
                errors.append("Cart is empty")

            for idx, item in enumerate(items):
                quantity = item.get("quantity", 0)

                if quantity <= 0:
                    errors.append(f"Item {idx + 1}: quantity must be greater than 0")

                if not item.get("product_id"):
                    errors.append(f"Item {idx + 1}: product_id is required")

                if "price" in item and item["price"] < 0:
                    errors.append(f"Item {idx + 1}: price cannot be negative")

            valid = len(errors) == 0

            response = CartValidationResponse(
                cart_id=cart_id,
                valid=valid,
                item_count=item_count,
                errors=errors,
            )
            return response.model_dump()

        except CartError:
            raise
        except Exception as e:
            logger.error(f"Error validating cart {cart_id}: {str(e)}")
            raise CartError(f"Failed to validate cart: {str(e)}")

    # ============================================================================
    # ORDER TOOLS
    # ============================================================================
