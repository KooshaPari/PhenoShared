"""RFQ (Request for Quote) Pydantic models for 4SGM MCP Server."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timedelta
from typing import Optional, List


class RFQItem(BaseModel):
    """Item in an RFQ."""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Requested quantity")
    specifications: Optional[str] = Field(
        None, description="Product specifications/notes"
    )


class CreateRFQInput(BaseModel):
    """Create RFQ request."""

    items: List[RFQItem] = Field(
        ..., min_length=1, description="List of items to quote"
    )
    customer_name: str = Field(..., min_length=1, description="Customer name")
    customer_email: str = Field(..., description="Customer email address")
    delivery_date: Optional[datetime] = Field(
        None, description="Requested delivery date"
    )
    special_requirements: Optional[str] = Field(
        None, max_length=1000, description="Special requirements"
    )

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "product_id": "PROD-123",
                        "quantity": 1000,
                        "specifications": "Custom packaging required",
                    }
                ],
                "customer_name": "John Smith",
                "customer_email": "john@example.com",
                "delivery_date": "2025-03-01T00:00:00",
                "special_requirements": "Rush order",
            }
        }
    )


class CreateRFQResponse(BaseModel):
    """Create RFQ response."""

    rfq_id: str = Field(..., description="RFQ ID")
    customer_name: str
    customer_email: str
    items: List[RFQItem]
    total_quantity: int = Field(..., ge=1, description="Total quantity requested")
    status: str = Field(default="pending", description="RFQ status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=30)
    )
    reference_number: str = Field(..., description="Customer reference number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rfq_id": "RFQ-ABC123XYZ",
                "customer_name": "John Smith",
                "customer_email": "john@example.com",
                "items": [
                    {
                        "product_id": "PROD-123",
                        "quantity": 1000,
                        "specifications": "Custom packaging",
                    }
                ],
                "total_quantity": 1000,
                "status": "pending",
                "created_at": "2025-01-10T10:00:00",
                "valid_until": "2025-02-09T10:00:00",
                "reference_number": "REF-2025-001",
            }
        }
    )


class GetRFQStatusInput(BaseModel):
    """Get RFQ status request."""

    rfq_id: str = Field(..., description="RFQ ID")


class GetRFQStatusResponse(BaseModel):
    """Get RFQ status response."""

    rfq_id: str
    status: str = Field(
        ..., description="RFQ status (pending, quoted, accepted, rejected)"
    )
    created_at: datetime
    quote_amount: Optional[float] = Field(
        None, ge=0, description="Quoted amount in USD"
    )
    quote_date: Optional[datetime] = Field(
        None, description="Date when quote was provided"
    )
    quoted_by: Optional[str] = Field(
        None, description="Sales representative who provided quote"
    )
    valid_until: Optional[datetime] = Field(None, description="Quote validity date")
    notes: Optional[str] = Field(None, description="Additional notes")
    delivery_estimate: Optional[str] = Field(
        None, description="Estimated delivery timeline"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rfq_id": "RFQ-ABC123XYZ",
                "status": "quoted",
                "created_at": "2025-01-10T10:00:00",
                "quote_amount": 5000.0,
                "quote_date": "2025-01-11T14:30:00",
                "quoted_by": "Sales Team",
                "valid_until": "2025-02-09T10:00:00",
                "notes": "Bulk discount applied",
                "delivery_estimate": "4 weeks",
            }
        }
    )


class AcceptRFQInput(BaseModel):
    """Accept RFQ request."""

    rfq_id: str = Field(..., description="RFQ ID to accept")
    purchase_order_number: Optional[str] = Field(None, description="Customer PO number")
    special_instructions: Optional[str] = Field(
        None, max_length=500, description="Special delivery/handling instructions"
    )


class AcceptRFQResponse(BaseModel):
    """Accept RFQ response."""

    rfq_id: str
    order_id: str = Field(..., description="Generated order ID from RFQ")
    status: str = Field(default="accepted", description="Status after acceptance")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    purchase_order_number: Optional[str] = Field(None, description="Customer PO number")
    order_total: float = Field(..., ge=0, description="Order total amount in USD")
    next_steps: str = Field(..., description="Instructions for next steps")
    account_manager: Optional[str] = Field(None, description="Assigned account manager")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rfq_id": "RFQ-ABC123XYZ",
                "order_id": "ORD-ORD123456",
                "status": "accepted",
                "created_at": "2025-01-11T15:00:00",
                "purchase_order_number": "PO-2025-001",
                "order_total": 5000.0,
                "next_steps": "Invoice will be sent within 24 hours",
                "account_manager": "Jane Doe",
            }
        }
    )
