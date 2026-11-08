"""Shipping calculation and tracking tools for 4SGM MCP server."""

import logging
from typing import Optional

from ..models.shipping import (
    ShippingCalculationInput,
    TrackingInput,
    DeliveryEstimateInput,
)
from ..exceptions import ShippingException
from ..repositories import ShippingRepository

logger = logging.getLogger(__name__)


def register_shipping_tools(mcp, shipping_repo: ShippingRepository):
    """Register shipping tools with the FastMCP instance."""

    @mcp.tool
    async def calculate_shipping(
        origin: str,
        destination: str,
        weight_lbs: float,
        dimensions_inches: Optional[tuple[float, float, float]] = None,
    ) -> dict:
        """Calculate shipping costs and delivery time.

        Validates origin, destination, and weight. Returns multiple carrier options
        with pricing and estimated delivery days. Includes surcharges for special
        routes (e.g., remote areas, long distances).

        Args:
            origin: Origin location (city, state, or ZIP)
            destination: Destination location (city, state, or ZIP)
            weight_lbs: Package weight in pounds (max 150 lbs)
            dimensions_inches: Optional tuple of (length, width, height) in inches

        Returns:
            ShippingCalculationResponse with carrier options and costs

        Raises:
            ValidationException: If input validation fails
            ShippingException: If calculation fails
        """
        try:
            if not shipping_repo:
                raise ShippingException("Shipping repository not initialized")

            input_data = ShippingCalculationInput(
                origin=origin,
                destination=destination,
                weight_lbs=weight_lbs,
                dimensions_inches=dimensions_inches,
            )

            response = await calculate_shipping_impl(input_data, shipping_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, ShippingException):
            raise
        except Exception as e:
            logger.error(f"Shipping calculation error: {e}")
            raise ShippingException(str(e))

    @mcp.tool
    async def get_shipping_methods() -> list[dict]:
        """Get all available shipping methods.

        Returns current shipping methods with estimated delivery times,
        base costs, and availability status.

        Returns:
            List of available shipping methods

        Raises:
            ShippingException: If retrieval fails
        """
        try:
            if not shipping_repo:
                raise ShippingException("Shipping repository not initialized")

            response = await get_shipping_methods_impl(shipping_repo)
            return [m.model_dump(exclude_none=True) for m in response]

        except ShippingException:
            raise
        except Exception as e:
            logger.error(f"Shipping methods retrieval error: {e}")
            raise ShippingException(str(e))

    @mcp.tool
    async def track_shipment(tracking_number: str) -> dict:
        """Track a shipment status and delivery progress.

        Returns current location, status, estimated delivery date, and
        complete event history for a shipment.

        Args:
            tracking_number: Tracking number (minimum 5 characters)

        Returns:
            TrackingResponse with current status and event history

        Raises:
            ValidationException: If tracking number is invalid
            NotFoundError: If shipment not found
            ShippingException: If tracking fails
        """
        try:
            if not shipping_repo:
                raise ShippingException("Shipping repository not initialized")

            input_data = TrackingInput(tracking_number=tracking_number)
            response = await track_shipment_impl(input_data, shipping_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, ShippingException):
            raise
        except Exception as e:
            logger.error(f"Shipment tracking error: {e}")
            raise ShippingException(str(e))

    @mcp.tool
    async def estimate_delivery(
        destination: str, shipping_method: str, quantity: int = 1
    ) -> dict:
        """Estimate delivery date based on destination and shipping method.

        Returns estimated delivery date and guarantee information
        for a given shipping method.

        Args:
            destination: Destination location (city, state, or ZIP)
            shipping_method: Shipping method ID (e.g., 'standard', 'express')
            quantity: Number of packages (default: 1)

        Returns:
            DeliveryEstimateResponse with estimated delivery date

        Raises:
            ValidationException: If input validation fails
            ShippingException: If estimation fails
        """
        try:
            if not shipping_repo:
                raise ShippingException("Shipping repository not initialized")

            input_data = DeliveryEstimateInput(
                destination=destination,
                shipping_method=shipping_method,
                quantity=quantity,
            )

            response = await estimate_delivery_impl(input_data, shipping_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, ShippingException):
            raise
        except Exception as e:
            logger.error(f"Delivery estimation error: {e}")
            raise ShippingException(str(e))

    # ============================================================================
    # PRICING TOOLS (Agent 7)
    # ============================================================================
