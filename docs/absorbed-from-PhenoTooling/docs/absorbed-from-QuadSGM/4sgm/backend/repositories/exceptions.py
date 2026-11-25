"""Repository exceptions for 4SGM.

Custom exceptions for repository operations providing clear error
semantics and structured error handling across the application.
"""

from typing import Any, Optional


class RepositoryError(Exception):
    """Base exception for all repository errors."""

    def __init__(
        self, message: str, code: str = "REPOSITORY_ERROR", details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class NotFoundError(RepositoryError):
    """Base exception for resource not found errors."""

    def __init__(self, resource_type: str, resource_id: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"{resource_type} '{resource_id}' not found",
            code=f"{resource_type.upper()}_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class ProductNotFoundError(NotFoundError):
    """Product not found exception."""

    def __init__(self, product_id: str, message: Optional[str] = None):
        super().__init__(resource_type="Product", resource_id=product_id, message=message)


class CartError(RepositoryError):
    """Cart operation error."""

    def __init__(
        self, message: str, cart_id: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="CART_ERROR",
            details={**(details or {}), "cart_id": cart_id} if cart_id else details,
        )
        self.cart_id = cart_id


class CartNotFoundError(NotFoundError):
    """Cart not found exception."""

    def __init__(self, cart_id: str, message: Optional[str] = None):
        super().__init__(resource_type="Cart", resource_id=cart_id, message=message)


class OrderError(RepositoryError):
    """Order operation error."""

    def __init__(
        self, message: str, order_id: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="ORDER_ERROR",
            details={**(details or {}), "order_id": order_id} if order_id else details,
        )
        self.order_id = order_id


class OrderNotFoundError(NotFoundError):
    """Order not found exception."""

    def __init__(self, order_id: str, message: Optional[str] = None):
        super().__init__(resource_type="Order", resource_id=order_id, message=message)


class InventoryError(RepositoryError):
    """Inventory operation error."""

    def __init__(
        self,
        message: str,
        product_id: Optional[str] = None,
        requested_quantity: Optional[int] = None,
        available_quantity: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        error_details = details or {}
        if product_id:
            error_details["product_id"] = product_id
        if requested_quantity is not None:
            error_details["requested_quantity"] = requested_quantity
        if available_quantity is not None:
            error_details["available_quantity"] = available_quantity

        super().__init__(message=message, code="INVENTORY_ERROR", details=error_details)
        self.product_id = product_id
        self.requested_quantity = requested_quantity
        self.available_quantity = available_quantity


class InsufficientInventoryError(InventoryError):
    """Insufficient inventory exception."""

    def __init__(self, product_id: str, requested: int, available: int):
        msg = (
            f"Insufficient inventory for product '{product_id}': "
            f"requested {requested}, available {available}"
        )
        super().__init__(
            message=msg,
            product_id=product_id,
            requested_quantity=requested,
            available_quantity=available,
        )


class CustomerError(RepositoryError):
    """Customer operation error."""

    def __init__(
        self,
        message: str,
        customer_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="CUSTOMER_ERROR",
            details={**(details or {}), "customer_id": customer_id} if customer_id else details,
        )
        self.customer_id = customer_id


class CustomerNotFoundError(NotFoundError):
    """Customer not found exception."""

    def __init__(self, customer_id: str, message: Optional[str] = None):
        super().__init__(resource_type="Customer", resource_id=customer_id, message=message)


class ShippingError(RepositoryError):
    """Shipping operation error."""

    def __init__(
        self,
        message: str,
        shipment_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="SHIPPING_ERROR",
            details={**(details or {}), "shipment_id": shipment_id} if shipment_id else details,
        )
        self.shipment_id = shipment_id


class RFQError(RepositoryError):
    """RFQ operation error."""

    def __init__(
        self, message: str, rfq_id: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RFQ_ERROR",
            details={**(details or {}), "rfq_id": rfq_id} if rfq_id else details,
        )
        self.rfq_id = rfq_id


class RFQNotFoundError(NotFoundError):
    """RFQ not found exception."""

    def __init__(self, rfq_id: str, message: Optional[str] = None):
        super().__init__(resource_type="RFQ", resource_id=rfq_id, message=message)


class PricingError(RepositoryError):
    """Pricing operation error."""

    def __init__(
        self,
        message: str,
        product_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="PRICING_ERROR",
            details={**(details or {}), "product_id": product_id} if product_id else details,
        )
        self.product_id = product_id


class ValidationError(RepositoryError):
    """Input validation error."""

    def __init__(
        self, message: str, field: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={**(details or {}), "field": field} if field else details,
        )
        self.field = field


class ConnectionError(RepositoryError):
    """Database connection error."""

    def __init__(
        self, message: str = "Database connection failed", details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message=message, code="CONNECTION_ERROR", details=details)
