"""Pydantic models for order-related MCP tools."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CartItem(BaseModel):
    """Model representing a cart item."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity", ge=1)
    price: float = Field(..., description="Price per unit", ge=0)


class CreateOrderInput(BaseModel):
    """Input model for create_order tool."""

    cart_id: str = Field(..., description="Cart ID", min_length=1)
    user_id: str = Field(..., description="User ID", min_length=1)
    shipping_address: str = Field(..., description="Shipping address", min_length=10)
    items: Optional[list[CartItem]] = Field(None, description="Items in order")
    subtotal: Optional[float] = Field(None, description="Order subtotal")
    tax: Optional[float] = Field(None, description="Tax amount")
    shipping_cost: Optional[float] = Field(None, description="Shipping cost")
    total: Optional[float] = Field(None, description="Order total")


class OrderResponse(BaseModel):
    """Response model for order information."""

    order_id: str = Field(..., description="Order ID")
    cart_id: str = Field(..., description="Cart ID")
    user_id: str = Field(..., description="User ID")
    status: str = Field(..., description="Order status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    shipping_address: str = Field(..., description="Shipping address")
    tracking_number: str = Field(..., description="Tracking number for shipment")
    items: Optional[list[CartItem]] = Field(None, description="Order items")
    subtotal: Optional[float] = Field(None, description="Subtotal")
    tax: Optional[float] = Field(None, description="Tax")
    shipping_cost: Optional[float] = Field(None, description="Shipping cost")
    total: Optional[float] = Field(None, description="Total")
