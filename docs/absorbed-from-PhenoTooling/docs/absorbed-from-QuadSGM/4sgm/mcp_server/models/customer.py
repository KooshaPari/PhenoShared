"""Customer Pydantic models for 4SGM MCP Server."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict


class OrderRecord(BaseModel):
    """Customer order record."""

    order_id: str = Field(..., description="Order ID")
    date: datetime = Field(..., description="Order date")
    total: float = Field(..., ge=0, description="Order total in USD")
    status: str = Field(..., description="Order status (e.g., 'completed', 'shipped')")
    item_count: int = Field(default=1, ge=1, description="Number of items in order")


class CustomerHistoryInput(BaseModel):
    """Customer history request."""

    user_id: str = Field(..., description="Customer user ID")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of orders to return"
    )
    include_returns: bool = Field(default=False, description="Include returned orders")


class CustomerHistoryResponse(BaseModel):
    """Customer order history response."""

    user_id: str
    total_orders: int = Field(..., ge=0, description="Total number of orders")
    total_spent: float = Field(..., ge=0, description="Total amount spent in USD")
    average_order_value: float = Field(..., ge=0, description="Average order value")
    first_order_date: Optional[datetime] = Field(
        None, description="Date of first order"
    )
    last_order_date: Optional[datetime] = Field(
        None, description="Date of most recent order"
    )
    orders: List[OrderRecord] = Field(default_factory=list, description="Recent orders")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "USR-123",
                "total_orders": 5,
                "total_spent": 2500.0,
                "average_order_value": 500.0,
                "first_order_date": "2024-01-15T10:00:00",
                "last_order_date": "2025-01-10T14:00:00",
                "orders": [
                    {
                        "order_id": "ORD-001",
                        "date": "2025-01-10T14:00:00",
                        "total": 500.0,
                        "status": "shipped",
                        "item_count": 3,
                    }
                ],
            }
        }
    )


class CustomerPreferencesInput(BaseModel):
    """Customer preferences request."""

    user_id: str = Field(..., description="Customer user ID")


class CustomerPreferencesResponse(BaseModel):
    """Customer preferences response."""

    user_id: str
    preferred_shipping: str = Field(
        default="standard", description="Preferred shipping method"
    )
    preferred_payment: str = Field(
        default="credit_card", description="Preferred payment method"
    )
    newsletter_subscribed: bool = Field(
        default=True, description="Newsletter subscription status"
    )
    email_notifications: bool = Field(
        default=True, description="Email notifications enabled"
    )
    saved_addresses: int = Field(
        default=0, ge=0, description="Number of saved addresses"
    )
    favorite_products: List[str] = Field(
        default_factory=list, description="Favorite product IDs"
    )
    marketing_preferences: Dict[str, bool] = Field(
        default_factory=dict, description="Marketing channel preferences"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "USR-123",
                "preferred_shipping": "express",
                "preferred_payment": "credit_card",
                "newsletter_subscribed": True,
                "email_notifications": True,
                "saved_addresses": 2,
                "favorite_products": ["PROD-123", "PROD-456"],
                "marketing_preferences": {
                    "email": True,
                    "sms": False,
                    "push": True,
                },
                "last_updated": "2025-01-10T10:00:00",
            }
        }
    )


class SavePreferencesInput(BaseModel):
    """Save customer preferences request."""

    user_id: str = Field(..., description="Customer user ID")
    preferred_shipping: Optional[str] = Field(
        None, description="Preferred shipping method"
    )
    preferred_payment: Optional[str] = Field(
        None, description="Preferred payment method"
    )
    newsletter_subscribed: Optional[bool] = Field(
        None, description="Newsletter subscription"
    )
    email_notifications: Optional[bool] = Field(None, description="Email notifications")
    marketing_preferences: Optional[Dict[str, bool]] = Field(
        None, description="Marketing preferences"
    )
    favorite_products: Optional[List[str]] = Field(
        None, description="Favorite product IDs"
    )

    @field_validator("preferred_shipping")
    @classmethod
    def validate_shipping(cls, v):
        if v and v not in ["standard", "express", "overnight", "economy"]:
            raise ValueError("Invalid shipping method")
        return v

    @field_validator("preferred_payment")
    @classmethod
    def validate_payment(cls, v):
        if v and v not in [
            "credit_card",
            "debit_card",
            "paypal",
            "wire_transfer",
            "bank_account",
        ]:
            raise ValueError("Invalid payment method")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "USR-123",
                "preferred_shipping": "express",
                "preferred_payment": "credit_card",
                "newsletter_subscribed": True,
                "email_notifications": True,
                "marketing_preferences": {
                    "email": True,
                    "sms": False,
                },
                "favorite_products": ["PROD-123"],
            }
        }
    )
