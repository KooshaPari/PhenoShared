"""Pricing Pydantic models for 4SGM MCP Server."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class BulkPricingInput(BaseModel):
    """Bulk pricing request."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Order quantity")


class BulkPricingResponse(BaseModel):
    """Bulk pricing response."""

    product_id: str
    quantity: int = Field(..., gt=0, description="Requested quantity")
    base_price: float = Field(..., ge=0, description="Base unit price")
    discount_rate: float = Field(
        ..., ge=0, le=1, description="Applied discount rate (0.0-1.0)"
    )
    unit_price: float = Field(..., ge=0, description="Final unit price after discount")
    total: float = Field(..., ge=0, description="Total price (unit_price * quantity)")
    savings: float = Field(..., ge=0, description="Total savings amount")
    tier_name: Optional[str] = Field(
        None, description="Pricing tier name (e.g., 'Bulk')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "PROD-123",
                "quantity": 500,
                "base_price": 99.99,
                "discount_rate": 0.15,
                "unit_price": 84.99,
                "total": 42495.0,
                "savings": 7500.0,
                "tier_name": "Bulk (500+)",
            }
        }
    )


class CouponInput(BaseModel):
    """Coupon validation and application request."""

    coupon_code: str = Field(
        ..., min_length=1, max_length=50, description="Coupon code"
    )
    cart_total: float = Field(..., ge=0, description="Current cart total in USD")
    customer_id: Optional[str] = Field(
        None, description="Customer ID for personalized coupons"
    )


class CouponResponse(BaseModel):
    """Coupon application response."""

    coupon_code: str
    valid: bool = Field(..., description="Whether coupon is valid")
    discount_rate: float = Field(
        default=0.0, ge=0, le=1, description="Discount rate (0.0-1.0)"
    )
    discount_amount: float = Field(
        default=0.0, ge=0, description="Discount amount in USD"
    )
    new_total: float = Field(..., ge=0, description="New cart total after discount")
    error_message: Optional[str] = Field(
        None, description="Error message if coupon is invalid"
    )
    expires_at: Optional[datetime] = Field(None, description="Coupon expiration date")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "coupon_code": "SAVE20",
                "valid": True,
                "discount_rate": 0.20,
                "discount_amount": 100.0,
                "new_total": 400.0,
                "error_message": None,
                "expires_at": "2025-12-31T23:59:59",
            }
        }
    )


class PromotionResponse(BaseModel):
    """Active promotion."""

    code: str = Field(..., description="Promotion code")
    description: str = Field(..., description="Promotion description")
    discount_rate: Optional[float] = Field(
        None, ge=0, le=1, description="Discount rate if applicable"
    )
    min_order_value: float = Field(
        default=0.0, ge=0, description="Minimum order value to qualify"
    )
    valid_from: Optional[datetime] = Field(None, description="Promotion start date")
    valid_until: Optional[datetime] = Field(None, description="Promotion end date")
    category: Optional[str] = Field(
        None, description="Applicable category (e.g., 'bulk', 'seasonal')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "SAVE20",
                "description": "20% off orders over $500",
                "discount_rate": 0.20,
                "min_order_value": 500.0,
                "valid_from": "2025-01-01T00:00:00",
                "valid_until": "2025-12-31T23:59:59",
                "category": "seasonal",
            }
        }
    )


class SavingsCalculationInput(BaseModel):
    """Savings calculation request."""

    original_price: float = Field(..., gt=0, description="Original price in USD")
    discount_rate: float = Field(..., ge=0, le=1, description="Discount rate (0.0-1.0)")
    quantity: int = Field(default=1, ge=1, description="Quantity for calculation")


class SavingsCalculationResponse(BaseModel):
    """Savings calculation response."""

    original_price: float = Field(..., gt=0, description="Original price")
    discount_rate: float = Field(..., ge=0, le=1, description="Applied discount rate")
    quantity: int = Field(..., ge=1, description="Quantity")
    per_unit_savings: float = Field(..., ge=0, description="Savings per unit")
    total_savings: float = Field(..., ge=0, description="Total savings for all units")
    final_unit_price: float = Field(
        ..., ge=0, description="Final unit price after discount"
    )
    final_total: float = Field(..., ge=0, description="Final total price")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original_price": 99.99,
                "discount_rate": 0.20,
                "quantity": 100,
                "per_unit_savings": 20.0,
                "total_savings": 2000.0,
                "final_unit_price": 79.99,
                "final_total": 7999.0,
            }
        }
    )
