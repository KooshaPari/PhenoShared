"""Pydantic models for product-related MCP tools."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GetProductInput(BaseModel):
    """Input model for get_product tool."""

    product_id: str = Field(..., description="The unique product identifier")


class ProductResponse(BaseModel):
    """Response model for product details."""

    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., description="Product price")
    category: Optional[str] = Field(None, description="Product category")
    rating: Optional[float] = Field(None, description="Average rating")
    reviews: Optional[int] = Field(None, description="Number of reviews")
    quantity_on_hand: int = Field(default=0, description="Quantity in stock")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class SearchProductsInput(BaseModel):
    """Input model for search_products tool."""

    query: str = Field(..., description="Search query string", min_length=1)
    limit: int = Field(
        default=10, description="Maximum results to return", ge=1, le=100
    )


class SearchProductsResponse(BaseModel):
    """Response model for search results."""

    products: list[ProductResponse] = Field(
        default_factory=list, description="List of matching products"
    )
    total_results: int = Field(default=0, description="Total number of results found")
    query: str = Field(..., description="The search query used")


class GetInventoryInput(BaseModel):
    """Input model for get_inventory tool."""

    product_id: str = Field(..., description="The product identifier")


class InventoryResponse(BaseModel):
    """Response model for inventory information."""

    product_id: str = Field(..., description="Product ID")
    in_stock: int = Field(..., description="Total in stock")
    reserved: int = Field(..., description="Reserved quantity")
    available: int = Field(..., description="Available for sale")
    warehouse_locations: list[str] = Field(
        default_factory=list, description="Warehouse locations"
    )


class UpdateInventoryInput(BaseModel):
    """Input model for update_inventory tool."""

    product_id: str = Field(..., description="The product identifier")
    quantity: int = Field(..., description="Quantity change (positive or negative)")


class UpdateInventoryResponse(BaseModel):
    """Response model for inventory update."""

    product_id: str = Field(..., description="Product ID")
    quantity_updated: int = Field(..., description="Amount updated")
    new_total: int = Field(..., description="New total quantity")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Update timestamp"
    )


class GetPricingInput(BaseModel):
    """Input model for get_pricing tool."""

    product_id: str = Field(..., description="The product identifier")
    quantity: int = Field(default=1, description="Quantity for pricing", ge=1)


class PricingResponse(BaseModel):
    """Response model for pricing information."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity requested")
    base_price: float = Field(..., description="Base price per unit")
    discount_rate: float = Field(..., description="Discount rate applied (0.0-1.0)")
    unit_price: float = Field(..., description="Price per unit after discount")
    total: float = Field(..., description="Total price")


class ApplyDiscountInput(BaseModel):
    """Input model for apply_discount tool."""

    product_id: str = Field(..., description="The product identifier")
    discount_code: str = Field(..., description="Discount code to apply", min_length=1)


class DiscountResponse(BaseModel):
    """Response model for discount application."""

    product_id: str = Field(..., description="Product ID")
    code: str = Field(..., description="Discount code used")
    discount_rate: float = Field(..., description="Discount rate (0.0-1.0)")
    valid: bool = Field(..., description="Whether discount code is valid")
