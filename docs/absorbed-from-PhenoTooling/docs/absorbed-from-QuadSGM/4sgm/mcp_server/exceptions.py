"""Custom exceptions for 4SGM MCP Server."""


class MCPException(Exception):
    """Base exception for MCP server operations."""

    def __init__(self, message: str, code: str = "MCP_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ShippingException(MCPException):
    """Shipping-related errors."""

    def __init__(
        self, message: str, code: str = "SHIPPING_ERROR", status_code: int = 400
    ):
        super().__init__(message, code, status_code)


class PricingException(MCPException):
    """Pricing-related errors."""

    def __init__(
        self, message: str, code: str = "PRICING_ERROR", status_code: int = 400
    ):
        super().__init__(message, code, status_code)


class RFQException(MCPException):
    """RFQ-related errors."""

    def __init__(self, message: str, code: str = "RFQ_ERROR", status_code: int = 400):
        super().__init__(message, code, status_code)


class CustomerException(MCPException):
    """Customer-related errors."""

    def __init__(
        self, message: str, code: str = "CUSTOMER_ERROR", status_code: int = 400
    ):
        super().__init__(message, code, status_code)


class ValidationException(MCPException):
    """Validation errors."""

    def __init__(self, message: str, field: str = "", code: str = "VALIDATION_ERROR"):
        super().__init__(f"{message} (field: {field})" if field else message, code, 422)


class NotFoundError(MCPException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str = ""):
        msg = f"{resource} not found"
        if identifier:
            msg += f": {identifier}"
        super().__init__(msg, "NOT_FOUND", 404)


class ProductNotFoundError(NotFoundError):
    """Product not found."""

    def __init__(self, product_id: str = ""):
        super().__init__("Product", product_id)


class ProductSearchError(MCPException):
    """Product search error."""

    def __init__(self, message: str = "Product search failed"):
        super().__init__(message, "PRODUCT_SEARCH_ERROR", 400)


class InventoryError(MCPException):
    """Inventory-related error."""

    def __init__(
        self, message: str, code: str = "INVENTORY_ERROR", status_code: int = 400
    ):
        super().__init__(message, code, status_code)


class InventoryNotFoundError(NotFoundError):
    """Inventory not found."""

    def __init__(self, identifier: str = ""):
        super().__init__("Inventory", identifier)


class InsufficientInventoryError(InventoryError):
    """Insufficient inventory."""

    def __init__(self, product_id: str = "", requested: int = 0, available: int = 0):
        msg = f"Insufficient inventory for product {product_id}: requested {requested}, available {available}"
        super().__init__(msg, "INSUFFICIENT_INVENTORY", 400)


class PricingError(MCPException):
    """Pricing-related error."""

    def __init__(self, message: str = "Pricing error"):
        super().__init__(message, "PRICING_ERROR", 400)


class InvalidDiscountCodeError(PricingError):
    """Invalid discount code."""

    def __init__(self, code: str = ""):
        msg = f"Invalid discount code: {code}" if code else "Invalid discount code"
        super().__init__(msg)


class CartError(MCPException):
    """Cart-related error."""

    def __init__(self, message: str, code: str = "CART_ERROR", status_code: int = 400):
        super().__init__(message, code, status_code)


class CartNotFoundError(NotFoundError):
    """Cart not found."""

    def __init__(self, cart_id: str = ""):
        super().__init__("Cart", cart_id)


class CartValidationError(CartError):
    """Cart validation error."""

    def __init__(self, message: str = "Cart validation failed"):
        super().__init__(message, "CART_VALIDATION_ERROR", 422)


class OrderError(MCPException):
    """Order-related error."""

    def __init__(self, message: str, code: str = "ORDER_ERROR", status_code: int = 400):
        super().__init__(message, code, status_code)


class OrderCreationError(OrderError):
    """Order creation error."""

    def __init__(self, message: str = "Failed to create order"):
        super().__init__(message, "ORDER_CREATION_ERROR", 400)


class InvalidOrderDataError(OrderError):
    """Invalid order data error."""

    def __init__(self, message: str = "Invalid order data"):
        super().__init__(message, "INVALID_ORDER_DATA", 422)


class UnauthorizedError(MCPException):
    """Authorization error."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED", 401)


class InternalServerError(MCPException):
    """Internal server error."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, "INTERNAL_ERROR", 500)
