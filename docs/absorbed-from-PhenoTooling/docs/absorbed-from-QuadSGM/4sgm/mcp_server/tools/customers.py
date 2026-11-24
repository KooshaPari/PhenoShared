"""Customer profile and history tools for 4SGM MCP server."""

import logging
from typing import Optional

from ..models.customer import (
    CustomerHistoryInput,
    CustomerPreferencesInput,
    SavePreferencesInput,
)
from ..exceptions import CustomerException
from ..repositories import CustomerRepository

logger = logging.getLogger(__name__)


def register_customers_tools(mcp, customer_repo: CustomerRepository):
    """Register customer tools with the FastMCP instance."""

    @mcp.tool
    async def get_customer_history(
        user_id: str, limit: int = 10, include_returns: bool = False
    ) -> dict:
        """Get customer order history and statistics.

        Returns total orders, total spent, average order value,
        and detailed list of recent orders.

        Args:
            user_id: Customer user ID
            limit: Maximum number of orders to return (1-100, default: 10)
            include_returns: Include returned orders (default: False)

        Returns:
            CustomerHistoryResponse with order history

        Raises:
            ValidationException: If input validation fails
            CustomerException: If retrieval fails
        """
        try:
            if not customer_repo:
                raise CustomerException("Customer repository not initialized")

            input_data = CustomerHistoryInput(
                user_id=user_id,
                limit=limit,
                include_returns=include_returns,
            )

            response = await get_customer_history_impl(input_data, customer_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, CustomerException):
            raise
        except Exception as e:
            logger.error(f"Customer history retrieval error: {e}")
            raise CustomerException(str(e))

    @mcp.tool
    async def get_customer_preferences(user_id: str) -> dict:
        """Get customer preferences and settings.

        Returns shipping, payment, and communication preferences.

        Args:
            user_id: Customer user ID

        Returns:
            CustomerPreferencesResponse with preferences

        Raises:
            ValidationException: If input validation fails
            NotFoundError: If customer not found
            CustomerException: If retrieval fails
        """
        try:
            if not customer_repo:
                raise CustomerException("Customer repository not initialized")

            input_data = CustomerPreferencesInput(user_id=user_id)
            response = await get_customer_preferences_impl(input_data, customer_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, CustomerException):
            raise
        except Exception as e:
            logger.error(f"Customer preferences retrieval error: {e}")
            raise CustomerException(str(e))

    @mcp.tool
    async def save_customer_preferences(
        user_id: str,
        preferred_shipping: Optional[str] = None,
        preferred_payment: Optional[str] = None,
        newsletter_subscribed: Optional[bool] = None,
        email_notifications: Optional[bool] = None,
        marketing_preferences: Optional[dict] = None,
        favorite_products: Optional[list[str]] = None,
    ) -> dict:
        """Save customer preferences and settings.

        Updates customer's preferred shipping method, payment method,
        and communication preferences.

        Args:
            user_id: Customer user ID
            preferred_shipping: Preferred shipping method (standard/express/overnight/economy)
            preferred_payment: Preferred payment method (credit_card/debit_card/paypal/wire_transfer/bank_account)
            newsletter_subscribed: Newsletter subscription status
            email_notifications: Email notifications enabled
            marketing_preferences: Marketing channel preferences dict
            favorite_products: List of favorite product IDs

        Returns:
            Updated CustomerPreferencesResponse

        Raises:
            ValidationException: If input validation fails
            NotFoundError: If customer not found
            CustomerException: If save fails
        """
        try:
            if not customer_repo:
                raise CustomerException("Customer repository not initialized")

            input_data = SavePreferencesInput(
                user_id=user_id,
                preferred_shipping=preferred_shipping,
                preferred_payment=preferred_payment,
                newsletter_subscribed=newsletter_subscribed,
                email_notifications=email_notifications,
                marketing_preferences=marketing_preferences,
                favorite_products=favorite_products,
            )

            response = await save_customer_preferences_impl(input_data, customer_repo)
            return response.model_dump(exclude_none=True)

        except (ValidationException, NotFoundError, CustomerException):
            raise
        except Exception as e:
            logger.error(f"Customer preferences save error: {e}")
            raise CustomerException(str(e))

    # ============================================================================
    # RFQ TOOLS (Agent 7)
    # ============================================================================
