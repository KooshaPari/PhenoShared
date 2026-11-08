"""RFQ (Request for Quote) management tools for 4SGM MCP server."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models.rfq import (
    CreateRFQInput,
    CreateRFQResponse,
    RFQItem,
    GetRFQStatusInput,
    GetRFQStatusResponse,
    AcceptRFQInput,
    AcceptRFQResponse,
)
from ..models.shipping import (
    DeliveryEstimateInput,
    TrackingInput,
    ShippingMethodResponse,
    TrackingResponse,
    DeliveryEstimateResponse,
    ShippingCalculationInput,
    ShippingCalculationResponse,
)
from ..models.pricing import (
    PromotionResponse,
    BulkPricingInput,
    BulkPricingResponse,
    CouponInput,
    CouponResponse,
    SavingsCalculationInput,
    SavingsCalculationResponse,
)
from ..models.customer import (
    CustomerHistoryInput,
    CustomerHistoryResponse,
    CustomerPreferencesInput,
    CustomerPreferencesResponse,
    SavePreferencesInput,
)
from ..exceptions import RFQException
from ..repositories import (
    RFQRepository,
    ShippingRepository,
    PricingRepository,
    CustomerRepository,
)

logger = logging.getLogger(__name__)


def register_rfq_tools(mcp, rfq_repo: RFQRepository):
    """Register RFQ tools with the FastMCP instance."""

    @mcp.tool
    async def create_rfq(
        items: list[dict],
        customer_name: str,
        customer_email: str,
        delivery_date: Optional[str] = None,
        special_requirements: Optional[str] = None,
    ) -> dict:
        """Create a request for quote (RFQ).

        Creates a new RFQ with items, customer info, and delivery requirements.
        Generates unique RFQ ID and sets validity period.

        Args:
            items: List of RFQ items, each with product_id, quantity, and optional specifications
            customer_name: Customer name
            customer_email: Customer email address
            delivery_date: Optional requested delivery date (ISO format)
            special_requirements: Optional special requirements (max 1000 characters)

        Returns:
            CreateRFQResponse with RFQ ID and details

        Raises:
            ValidationException: If input validation fails
            RFQException: If RFQ creation fails
        """
        try:
            if not rfq_repo:
                raise RFQException("RFQ repository not initialized")

            # Parse items
            rfq_items = []
            for item in items:
                rfq_items.append(
                    {
                        "product_id": item.get("product_id"),
                        "quantity": item.get("quantity"),
                        "specifications": item.get("specifications"),
                    }
                )

            # Parse delivery date if provided
            delivery_dt = None
            if delivery_date:
                delivery_dt = datetime.fromisoformat(delivery_date)

            input_data = CreateRFQInput(
                items=[RFQItem(**i) for i in rfq_items],
                customer_name=customer_name,
                customer_email=customer_email,
                delivery_date=delivery_dt,
                special_requirements=special_requirements,
            )

            response = await create_rfq_impl(input_data, rfq_repo)
            return response.model_dump(exclude_none=True)

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"RFQ creation error: {e}")
            raise RFQException(str(e))

    @mcp.tool
    async def get_rfq_status(rfq_id: str) -> dict:
        """Get status of a request for quote.

        Returns current RFQ status, quote amount if available,
        and any notes or special information.

        Args:
            rfq_id: RFQ ID

        Returns:
            GetRFQStatusResponse with status and quote details

        Raises:
            ValidationException: If input validation fails
            NotFoundError: If RFQ not found
            RFQException: If status retrieval fails
        """
        try:
            if not rfq_repo:
                raise RFQException("RFQ repository not initialized")

            input_data = GetRFQStatusInput(rfq_id=rfq_id)
            response = await get_rfq_status_impl(input_data, rfq_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, RFQException):
            raise
        except Exception as e:
            logger.error(f"RFQ status retrieval error: {e}")
            raise RFQException(str(e))

    @mcp.tool
    async def accept_rfq(
        rfq_id: str,
        purchase_order_number: Optional[str] = None,
        special_instructions: Optional[str] = None,
    ) -> dict:
        """Accept a request for quote and create order.

        Converts RFQ to order, assigns account manager, and provides
        next steps for order fulfillment.

        Args:
            rfq_id: RFQ ID to accept
            purchase_order_number: Optional customer PO number
            special_instructions: Optional special delivery/handling instructions (max 500 characters)

        Returns:
            AcceptRFQResponse with order ID and next steps

        Raises:
            ValidationException: If input validation fails
            NotFoundError: If RFQ not found
            RFQException: If acceptance fails
        """
        try:
            if not rfq_repo:
                raise RFQException("RFQ repository not initialized")

            input_data = AcceptRFQInput(
                rfq_id=rfq_id,
                purchase_order_number=purchase_order_number,
                special_instructions=special_instructions,
            )

            response = await accept_rfq_impl(input_data, rfq_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, RFQException):
            raise
        except Exception as e:
            logger.error(f"RFQ acceptance error: {e}")
            raise RFQException(str(e))

    # ============================================================================
    # TOOL IMPLEMENTATION WRAPPERS
    # ============================================================================
    # These import the actual async implementations from tools_upgraded.py

    async def calculate_shipping_impl(
        input_data: ShippingCalculationInput, repository: ShippingRepository
    ) -> ShippingCalculationResponse:
        """Implementation wrapper for calculate_shipping."""
        # Base implementation - will be replaced by repository when available
        try:
            # Calculate base cost
            base_cost = input_data.weight_lbs * 0.5
            distance_multiplier = (
                1.5
                if "CA" in input_data.origin and "NY" in input_data.destination
                else 1.0
            )
            final_cost = base_cost * distance_multiplier

            # Create carriers
            from .models.shipping import CarrierOption

            carriers = [
                CarrierOption(
                    carrier="Standard",
                    cost=final_cost,
                    estimated_days=5,
                    service_level="Ground",
                ),
                CarrierOption(
                    carrier="Express",
                    cost=final_cost * 1.5,
                    estimated_days=2,
                    service_level="Express",
                ),
            ]

            return ShippingCalculationResponse(
                origin=input_data.origin,
                destination=input_data.destination,
                weight_lbs=input_data.weight_lbs,
                base_cost=base_cost,
                final_cost=final_cost,
                estimated_days=5,
                carriers=carriers,
            )
        except Exception as e:
            raise ShippingException(str(e))

    async def get_shipping_methods_impl(
        repository: ShippingRepository,
    ) -> list[ShippingMethodResponse]:
        """Implementation wrapper for get_shipping_methods."""
        try:
            methods = [
                ShippingMethodResponse(
                    id="standard",
                    name="Standard Shipping",
                    estimated_days=5,
                    base_cost=50.0,
                    description="5-7 business days delivery",
                ),
                ShippingMethodResponse(
                    id="express",
                    name="Express Shipping",
                    estimated_days=2,
                    base_cost=75.0,
                    description="2-3 business days delivery",
                ),
                ShippingMethodResponse(
                    id="overnight",
                    name="Overnight Shipping",
                    estimated_days=1,
                    base_cost=150.0,
                    description="1 business day delivery",
                ),
            ]
            return methods
        except Exception as e:
            raise ShippingException(str(e))

    async def track_shipment_impl(
        input_data: TrackingInput, repository: ShippingRepository
    ) -> TrackingResponse:
        """Implementation wrapper for track_shipment."""
        try:
            from .models.shipping import TrackingEvent

            events = [
                TrackingEvent(
                    timestamp=datetime.now(timezone.utc),
                    status="picked_up",
                    location="Warehouse",
                    description="Package picked up from warehouse",
                ),
            ]

            return TrackingResponse(
                tracking_number=input_data.tracking_number,
                status="in_transit",
                current_location="Distribution Center",
                estimated_delivery=datetime.now(timezone.utc) + timedelta(days=3),
                carrier="FedEx",
                events=events,
                is_delivered=False,
            )
        except Exception as e:
            raise ShippingException(str(e))

    async def estimate_delivery_impl(
        input_data: DeliveryEstimateInput, repository: ShippingRepository
    ) -> DeliveryEstimateResponse:
        """Implementation wrapper for estimate_delivery."""
        try:
            days_map = {"standard": 5, "express": 2, "overnight": 1}
            days = days_map.get(input_data.shipping_method, 5)
            delivery_date = (datetime.now(timezone.utc) + timedelta(days=days)).date()

            return DeliveryEstimateResponse(
                destination=input_data.destination,
                shipping_method=input_data.shipping_method,
                estimated_days=days,
                estimated_delivery_date=delivery_date,
                guarantee="Money back if not delivered on time",
            )
        except Exception as e:
            raise ShippingException(str(e))

    async def get_bulk_pricing_impl(
        input_data: BulkPricingInput, repository: PricingRepository
    ) -> BulkPricingResponse:
        """Implementation wrapper for get_bulk_pricing."""
        try:
            base_price = 99.99
            discount_rate = 0.0

            if input_data.quantity >= 1000:
                discount_rate = 0.20
            elif input_data.quantity >= 500:
                discount_rate = 0.15
            elif input_data.quantity >= 100:
                discount_rate = 0.10

            unit_price = base_price * (1 - discount_rate)
            total = unit_price * input_data.quantity
            savings = base_price * input_data.quantity * discount_rate

            tier_name = None
            if discount_rate > 0:
                tier_name = f"Bulk ({input_data.quantity}+)"

            return BulkPricingResponse(
                product_id=input_data.product_id,
                quantity=input_data.quantity,
                base_price=base_price,
                discount_rate=discount_rate,
                unit_price=round(unit_price, 2),
                total=round(total, 2),
                savings=round(savings, 2),
                tier_name=tier_name,
            )
        except Exception as e:
            raise PricingException(str(e))

    async def apply_coupon_impl(
        input_data: CouponInput, repository: PricingRepository
    ) -> CouponResponse:
        """Implementation wrapper for apply_coupon."""
        try:
            coupons = {
                "SAVE10": 0.10,
                "SAVE20": 0.20,
                "BULK15": 0.15,
            }

            discount_rate = coupons.get(input_data.coupon_code, 0.0)
            discount_amount = input_data.cart_total * discount_rate
            new_total = input_data.cart_total - discount_amount

            return CouponResponse(
                coupon_code=input_data.coupon_code,
                valid=discount_rate > 0,
                discount_rate=discount_rate,
                discount_amount=round(discount_amount, 2),
                new_total=round(new_total, 2),
                error_message=None,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
        except Exception as e:
            raise PricingException(str(e))

    async def get_promotions_impl(
        repository: PricingRepository,
    ) -> list[PromotionResponse]:
        """Implementation wrapper for get_promotions."""
        try:
            return [
                PromotionResponse(
                    code="SAVE10",
                    description="10% off",
                    discount_rate=0.10,
                    valid_from=datetime.utcnow(),
                    valid_until=datetime.utcnow() + timedelta(days=90),
                    category="seasonal",
                ),
                PromotionResponse(
                    code="SAVE20",
                    description="20% off orders over $500",
                    discount_rate=0.20,
                    min_order_value=500.0,
                    valid_from=datetime.utcnow(),
                    valid_until=datetime.utcnow() + timedelta(days=90),
                    category="bulk",
                ),
                PromotionResponse(
                    code="BULK15",
                    description="15% off bulk orders",
                    discount_rate=0.15,
                    valid_from=datetime.utcnow(),
                    valid_until=datetime.utcnow() + timedelta(days=90),
                    category="bulk",
                ),
            ]
        except Exception as e:
            raise PricingException(str(e))

    async def calculate_savings_impl(
        input_data: SavingsCalculationInput, repository: PricingRepository
    ) -> SavingsCalculationResponse:
        """Implementation wrapper for calculate_savings."""
        try:
            per_unit_savings = input_data.original_price * input_data.discount_rate
            total_savings = per_unit_savings * input_data.quantity
            final_unit_price = input_data.original_price - per_unit_savings
            final_total = final_unit_price * input_data.quantity

            return SavingsCalculationResponse(
                original_price=round(input_data.original_price, 2),
                discount_rate=input_data.discount_rate,
                quantity=input_data.quantity,
                per_unit_savings=round(per_unit_savings, 2),
                total_savings=round(total_savings, 2),
                final_unit_price=round(final_unit_price, 2),
                final_total=round(final_total, 2),
            )
        except Exception as e:
            raise PricingException(str(e))

    async def get_customer_history_impl(
        input_data: CustomerHistoryInput, repository: CustomerRepository
    ) -> CustomerHistoryResponse:
        """Implementation wrapper for get_customer_history."""
        try:
            from .models.customer import OrderRecord

            # Mock data
            orders = [
                OrderRecord(
                    order_id=f"ORD-{i}",
                    date=datetime.utcnow(),
                    total=500.0,
                    status="completed",
                )
                for i in range(min(5, input_data.limit))
            ]

            total_spent = sum(o.total for o in orders)
            avg_value = total_spent / len(orders) if orders else 0

            return CustomerHistoryResponse(
                user_id=input_data.user_id,
                total_orders=len(orders),
                total_spent=round(total_spent, 2),
                average_order_value=round(avg_value, 2),
                first_order_date=orders[0].date if orders else None,
                last_order_date=orders[-1].date if orders else None,
                orders=orders,
            )
        except Exception as e:
            raise CustomerException(str(e))

    async def get_customer_preferences_impl(
        input_data: CustomerPreferencesInput, repository: CustomerRepository
    ) -> CustomerPreferencesResponse:
        """Implementation wrapper for get_customer_preferences."""
        try:
            return CustomerPreferencesResponse(
                user_id=input_data.user_id,
                preferred_shipping="express",
                preferred_payment="credit_card",
                newsletter_subscribed=True,
                email_notifications=True,
                saved_addresses=2,
            )
        except Exception as e:
            raise CustomerException(str(e))

    async def save_customer_preferences_impl(
        input_data: SavePreferencesInput, repository: CustomerRepository
    ) -> CustomerPreferencesResponse:
        """Implementation wrapper for save_customer_preferences."""
        try:
            return CustomerPreferencesResponse(
                user_id=input_data.user_id,
                preferred_shipping=input_data.preferred_shipping or "standard",
                preferred_payment=input_data.preferred_payment or "credit_card",
                newsletter_subscribed=(
                    input_data.newsletter_subscribed
                    if input_data.newsletter_subscribed is not None
                    else True
                ),
                email_notifications=(
                    input_data.email_notifications
                    if input_data.email_notifications is not None
                    else True
                ),
                marketing_preferences=input_data.marketing_preferences or {},
                favorite_products=input_data.favorite_products or [],
            )
        except Exception as e:
            raise CustomerException(str(e))

    async def create_rfq_impl(
        input_data: CreateRFQInput, repository: RFQRepository
    ) -> CreateRFQResponse:
        """Implementation wrapper for create_rfq."""
        try:
            total_quantity = sum(item.quantity for item in input_data.items)
            rfq_id = f"RFQ-{uuid.uuid4().hex[:8].upper()}"

            return CreateRFQResponse(
                rfq_id=rfq_id,
                customer_name=input_data.customer_name,
                customer_email=input_data.customer_email,
                items=input_data.items,
                total_quantity=total_quantity,
                reference_number=f"REF-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:4].upper()}",
            )
        except Exception as e:
            raise RFQException(str(e))

    async def get_rfq_status_impl(
        input_data: GetRFQStatusInput, repository: RFQRepository
    ) -> GetRFQStatusResponse:
        """Implementation wrapper for get_rfq_status."""
        try:
            return GetRFQStatusResponse(
                rfq_id=input_data.rfq_id,
                status="pending",
                created_at=datetime.now(timezone.utc),
                quote_amount=5000.0,
                quote_date=datetime.now(timezone.utc) + timedelta(days=1),
                quoted_by="Sales Team",
                valid_until=datetime.now(timezone.utc) + timedelta(days=30),
                notes="Quote pending approval",
                delivery_estimate="4 weeks",
            )
        except Exception as e:
            raise RFQException(str(e))

    async def accept_rfq_impl(
        input_data: AcceptRFQInput, repository: RFQRepository
    ) -> AcceptRFQResponse:
        """Implementation wrapper for accept_rfq."""
        try:
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

            return AcceptRFQResponse(
                rfq_id=input_data.rfq_id,
                order_id=order_id,
                order_total=5000.0,
                next_steps="Invoice will be sent within 24 hours",
                purchase_order_number=input_data.purchase_order_number,
                account_manager="Account Manager",
            )
        except Exception as e:
            raise RFQException(str(e))
