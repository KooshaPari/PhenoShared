"""Pricing, discounts, and promotions tools for 4SGM MCP server."""

import logging
from typing import Optional

from ..models.pricing import (
    BulkPricingInput,
    CouponInput,
    SavingsCalculationInput,
)
from ..models import (
    PricingResponse,
    DiscountResponse,
)
from ..exceptions import PricingError, InvalidDiscountCodeError, PricingException
from ..repositories import PricingRepository

logger = logging.getLogger(__name__)


def register_pricing_tools(mcp, pricing_repo: PricingRepository):
    """Register pricing tools with the FastMCP instance."""
    """Register pricing tools with the FastMCP instance."""

    @mcp.tool
    async def get_pricing(product_id: str, quantity: int = 1) -> dict:
        """Get product pricing with bulk discounts.

        Calculates pricing with automatic bulk discount application:
        - 5% off for 20+
        - 10% off for 100+
        - 15% off for 500+
        - 20% off for 1000+

        Args:
            product_id: The product identifier
            quantity: Order quantity (default 1, minimum 1)

        Returns:
            PricingResponse with base_price, discount_rate, unit_price, and total.

        Raises:
            ProductNotFoundError: If product not found
            PricingError: If pricing lookup fails
        """
        try:
            if not pricing_repo:
                raise PricingError("Pricing repository not initialized")

            if quantity < 1:
                raise PricingError("Quantity must be at least 1")

            pricing = await pricing_repo.get_pricing(product_id, quantity)

            response = PricingResponse(
                product_id=product_id,
                quantity=quantity,
                base_price=pricing["base_price"],
                discount_rate=pricing["discount_rate"],
                unit_price=pricing["unit_price"],
                total=pricing["total"],
            )
            return response.model_dump()

        except PricingError:
            raise
        except Exception as e:
            logger.error(f"Error calculating pricing for {product_id}: {str(e)}")
            raise PricingError(f"Failed to calculate pricing: {str(e)}")

    @mcp.tool
    async def apply_discount(product_id: str, discount_code: str) -> dict:
        """Apply promotional discount code to product.

        Validates and applies discount codes. Valid codes include:
        SAVE10 (10%), SAVE20 (20%), BULK15 (15%).

        Args:
            product_id: The product identifier
            discount_code: Promotional code to validate and apply

        Returns:
            DiscountResponse with code validity and discount rate applied.

        Raises:
            InvalidDiscountCodeError: If code is invalid
            PricingError: If discount application fails
        """
        try:
            if not pricing_repo:
                raise PricingError("Pricing repository not initialized")

            if not discount_code or len(discount_code.strip()) == 0:
                raise InvalidDiscountCodeError("Discount code cannot be empty")

            discount_rate = await pricing_repo.validate_discount_code(discount_code)

            response = DiscountResponse(
                product_id=product_id,
                code=discount_code,
                discount_rate=discount_rate,
                valid=discount_rate > 0,
            )
            return response.model_dump()

        except InvalidDiscountCodeError:
            raise
        except Exception as e:
            logger.error(f"Error applying discount code '{discount_code}': {str(e)}")
            raise PricingError(f"Failed to apply discount: {str(e)}")

    # ============================================================================
    # CART TOOLS
    # ============================================================================

    @mcp.tool
    async def get_bulk_pricing(product_id: str, quantity: int) -> dict:
        """Get bulk order pricing with applicable discounts.

        Returns tiered pricing based on quantity, including unit price,
        total cost, and savings amount.

        Args:
            product_id: Product ID
            quantity: Order quantity (must be > 0)

        Returns:
            BulkPricingResponse with pricing details and savings

        Raises:
            ValidationException: If input validation fails
            PricingException: If pricing calculation fails
        """
        try:
            if not pricing_repo:
                raise PricingException("Pricing repository not initialized")

            input_data = BulkPricingInput(product_id=product_id, quantity=quantity)
            response = await get_bulk_pricing_impl(input_data, pricing_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, PricingException):
            raise
        except Exception as e:
            logger.error(f"Bulk pricing error: {e}")
            raise PricingException(str(e))

    @mcp.tool
    async def apply_coupon(
        coupon_code: str, cart_total: float, customer_id: Optional[str] = None
    ) -> dict:
        """Apply coupon code to cart and calculate discount.

        Validates coupon code, checks expiration, and calculates
        discount amount and new total.

        Args:
            coupon_code: Coupon code to apply
            cart_total: Current cart total in USD (>= 0)
            customer_id: Optional customer ID for personalized coupons

        Returns:
            CouponResponse with discount details and validation status

        Raises:
            ValidationException: If input validation fails
            PricingException: If coupon application fails
        """
        try:
            if not pricing_repo:
                raise PricingException("Pricing repository not initialized")

            input_data = CouponInput(
                coupon_code=coupon_code,
                cart_total=cart_total,
                customer_id=customer_id,
            )

            response = await apply_coupon_impl(input_data, pricing_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, PricingException):
            raise
        except Exception as e:
            logger.error(f"Coupon application error: {e}")
            raise PricingException(str(e))

    @mcp.tool
    async def get_promotions() -> list[dict]:
        """Get all active promotions.

        Returns current promotional offers with discount rates,
        minimum order requirements, and validity dates.

        Returns:
            List of active promotions

        Raises:
            PricingException: If retrieval fails
        """
        try:
            if not pricing_repo:
                raise PricingException("Pricing repository not initialized")

            response = await get_promotions_impl(pricing_repo)
            return [p.model_dump(exclude_none=True) for p in response]

        except PricingException:
            raise
        except Exception as e:
            logger.error(f"Promotions retrieval error: {e}")
            raise PricingException(str(e))

    @mcp.tool
    async def calculate_savings(
        original_price: float, discount_rate: float, quantity: int = 1
    ) -> dict:
        """Calculate potential savings from a discount.

        Returns per-unit and total savings, final prices after discount.

        Args:
            original_price: Original price in USD (> 0)
            discount_rate: Discount rate as decimal (0.0 to 1.0)
            quantity: Number of units (default: 1)

        Returns:
            SavingsCalculationResponse with savings details

        Raises:
            ValidationException: If input validation fails
            PricingException: If calculation fails
        """
        try:
            if not pricing_repo:
                raise PricingException("Pricing repository not initialized")

            input_data = SavingsCalculationInput(
                original_price=original_price,
                discount_rate=discount_rate,
                quantity=quantity,
            )

            response = await calculate_savings_impl(input_data, pricing_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, PricingException):
            raise
        except Exception as e:
            logger.error(f"Savings calculation error: {e}")
            raise PricingException(str(e))

    # ============================================================================
    # CUSTOMER TOOLS (Agent 7)
    # ============================================================================
