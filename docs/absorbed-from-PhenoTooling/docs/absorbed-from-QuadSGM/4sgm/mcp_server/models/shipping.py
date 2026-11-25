"""Shipping Pydantic models for 4SGM MCP Server."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date
from typing import Optional, List


class CarrierOption(BaseModel):
    """Shipping carrier option."""

    carrier: str = Field(..., description="Carrier name (e.g., 'FedEx', 'UPS')")
    cost: float = Field(..., ge=0, description="Shipping cost in USD")
    estimated_days: int = Field(..., ge=1, description="Estimated delivery days")
    service_level: Optional[str] = Field(
        None, description="Service level (e.g., 'Standard', 'Express')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "carrier": "FedEx",
                "cost": 45.99,
                "estimated_days": 3,
                "service_level": "Ground",
            }
        }
    )


class ShippingCalculationInput(BaseModel):
    """Shipping calculation request."""

    origin: str = Field(
        ..., min_length=2, description="Origin location (city, state, or ZIP)"
    )
    destination: str = Field(
        ..., min_length=2, description="Destination location (city, state, or ZIP)"
    )
    weight_lbs: float = Field(..., gt=0, description="Package weight in pounds")
    dimensions_inches: Optional[tuple[float, float, float]] = Field(
        None, description="Package dimensions (length, width, height) in inches"
    )

    @field_validator("weight_lbs")
    @classmethod
    def validate_weight(cls, v):
        if v > 150:
            raise ValueError("Weight cannot exceed 150 lbs")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": "New York, NY",
                "destination": "Los Angeles, CA",
                "weight_lbs": 25.5,
                "dimensions_inches": (12, 10, 8),
            }
        }
    )


class ShippingCalculationResponse(BaseModel):
    """Shipping calculation response."""

    origin: str
    destination: str
    weight_lbs: float
    base_cost: float = Field(..., ge=0, description="Base shipping cost")
    final_cost: float = Field(..., ge=0, description="Final cost after surcharges")
    estimated_days: int = Field(..., ge=1, description="Estimated delivery days")
    carriers: List[CarrierOption] = Field(..., description="Available carrier options")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": "New York, NY",
                "destination": "Los Angeles, CA",
                "weight_lbs": 25.5,
                "base_cost": 50.0,
                "final_cost": 75.0,
                "estimated_days": 5,
                "carriers": [
                    {
                        "carrier": "FedEx",
                        "cost": 75.0,
                        "estimated_days": 5,
                        "service_level": "Ground",
                    }
                ],
                "created_at": "2025-01-10T10:00:00",
            }
        }
    )


class ShippingMethodInput(BaseModel):
    """Get available shipping methods request."""

    include_international: bool = Field(
        default=False, description="Include international methods"
    )
    include_disabled: bool = Field(
        default=False, description="Include disabled methods"
    )


class ShippingMethodResponse(BaseModel):
    """Available shipping method."""

    id: str = Field(..., description="Method ID (e.g., 'standard', 'express')")
    name: str = Field(..., description="Display name")
    estimated_days: int = Field(..., ge=1, description="Estimated delivery days")
    base_cost: float = Field(..., ge=0, description="Base cost in USD")
    description: Optional[str] = Field(None, description="Method description")
    is_available: bool = Field(default=True, description="Whether method is available")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "standard",
                "name": "Standard Shipping",
                "estimated_days": 5,
                "base_cost": 50.0,
                "description": "5-7 business days delivery",
                "is_available": True,
            }
        }
    )


class TrackingEvent(BaseModel):
    """Tracking event in shipment history."""

    timestamp: datetime
    status: str = Field(
        ..., description="Event status (e.g., 'picked_up', 'in_transit')"
    )
    location: str = Field(..., description="Event location")
    description: Optional[str] = Field(None, description="Event details")


class TrackingInput(BaseModel):
    """Shipment tracking request."""

    tracking_number: str = Field(..., min_length=5, description="Tracking number")


class TrackingResponse(BaseModel):
    """Shipment tracking response."""

    tracking_number: str
    status: str = Field(
        ..., description="Current status (e.g., 'in_transit', 'delivered')"
    )
    current_location: str = Field(..., description="Current location")
    estimated_delivery: Optional[datetime] = Field(
        None, description="Estimated delivery date"
    )
    carrier: str = Field(..., description="Shipping carrier")
    events: List[TrackingEvent] = Field(
        default_factory=list, description="Tracking events"
    )
    is_delivered: bool = Field(
        default=False, description="Whether shipment is delivered"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tracking_number": "TRK-ABC12345",
                "status": "in_transit",
                "current_location": "Chicago, IL Distribution Center",
                "estimated_delivery": "2025-01-12T18:00:00",
                "carrier": "FedEx",
                "events": [
                    {
                        "timestamp": "2025-01-10T10:00:00",
                        "status": "picked_up",
                        "location": "New York, NY",
                        "description": "Package picked up",
                    }
                ],
                "is_delivered": False,
            }
        }
    )


class DeliveryEstimateInput(BaseModel):
    """Delivery estimate request."""

    destination: str = Field(..., min_length=2, description="Destination location")
    shipping_method: str = Field(
        ..., description="Shipping method ID (e.g., 'standard', 'express')"
    )
    quantity: Optional[int] = Field(1, ge=1, description="Number of packages")


class DeliveryEstimateResponse(BaseModel):
    """Delivery estimate response."""

    destination: str
    shipping_method: str
    estimated_days: int = Field(..., ge=1, description="Estimated delivery days")
    estimated_delivery_date: date = Field(..., description="Estimated delivery date")
    guarantee: Optional[str] = Field(
        None, description="Delivery guarantee (e.g., 'Money back')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "destination": "Los Angeles, CA",
                "shipping_method": "express",
                "estimated_days": 2,
                "estimated_delivery_date": "2025-01-12",
                "guarantee": "Money back if not delivered on time",
            }
        }
    )
