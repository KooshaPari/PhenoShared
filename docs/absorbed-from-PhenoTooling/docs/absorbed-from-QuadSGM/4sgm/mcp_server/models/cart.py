"""Pydantic models for cart-related MCP tools."""

from pydantic import BaseModel, Field
from datetime import datetime


class CreateCartInput(BaseModel):
    """Input model for create_cart tool."""

    user_id: str = Field(..., description="The user identifier", min_length=1)


class CartResponse(BaseModel):
    """Response model for cart information."""

    cart_id: str = Field(..., description="Cart ID")
    user_id: str = Field(..., description="User ID")
    items: list[dict] = Field(default_factory=list, description="Items in cart")
    total: float = Field(default=0.0, description="Cart total")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


class CartItemResponse(BaseModel):
    """Response model for cart item."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity ordered", ge=1)
    unit_price: float = Field(..., description="Price per unit")
    line_total: float = Field(..., description="Total for this line item")


class AddToCartInput(BaseModel):
    """Input model for add_to_cart tool."""

    cart_id: str = Field(..., description="Cart ID", min_length=1)
    product_id: str = Field(..., description="Product to add", min_length=1)
    quantity: int = Field(..., description="Quantity to add", ge=1)


class AddToCartResponse(BaseModel):
    """Response model for add to cart."""

    cart_id: str = Field(..., description="Cart ID")
    product_id: str = Field(..., description="Product ID added")
    quantity: int = Field(..., description="Quantity added")
    unit_price: float = Field(..., description="Unit price")
    line_total: float = Field(..., description="Line item total")
    status: str = Field(..., description="Operation status")


class RemoveFromCartInput(BaseModel):
    """Input model for remove_from_cart tool."""

    cart_id: str = Field(..., description="Cart ID", min_length=1)
    product_id: str = Field(..., description="Product to remove", min_length=1)


class RemoveFromCartResponse(BaseModel):
    """Response model for remove from cart."""

    cart_id: str = Field(..., description="Cart ID")
    product_id: str = Field(..., description="Product ID removed")
    status: str = Field(..., description="Operation status")


class CartItem(BaseModel):
    """Model representing a cart item."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity", ge=1)
    price: float = Field(..., description="Price per unit", ge=0)


class CalculateCartTotalInput(BaseModel):
    """Input model for calculate_cart_total tool."""

    cart_id: str = Field(..., description="Cart ID", min_length=1)
    items: list[CartItem] = Field(..., description="Items in cart")


class CartTotalResponse(BaseModel):
    """Response model for cart total calculation."""

    cart_id: str = Field(..., description="Cart ID")
    subtotal: float = Field(..., description="Subtotal before tax/shipping")
    tax: float = Field(..., description="Tax amount")
    shipping: float = Field(..., description="Shipping cost")
    total: float = Field(..., description="Final total")


class ValidateCartInput(BaseModel):
    """Input model for validate_cart tool."""

    cart_id: str = Field(..., description="Cart ID", min_length=1)
    items: list[CartItem] = Field(..., description="Items to validate")


class CartValidationResponse(BaseModel):
    """Response model for cart validation."""

    cart_id: str = Field(..., description="Cart ID")
    valid: bool = Field(..., description="Whether cart is valid")
    item_count: int = Field(..., description="Number of items")
    errors: list[str] = Field(
        default_factory=list, description="Validation errors if any"
    )
