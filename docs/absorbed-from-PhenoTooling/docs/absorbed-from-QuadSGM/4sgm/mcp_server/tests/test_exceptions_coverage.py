"""Tests for exception handling and edge cases."""

import pytest

from ..exceptions import (
    MCPException,
    ShippingException,
    PricingException,
    RFQException,
    CustomerException,
    ValidationException,
    NotFoundError,
    ProductNotFoundError,
    ProductSearchError,
    InventoryError,
    InventoryNotFoundError,
    InsufficientInventoryError,
    PricingError,
    InvalidDiscountCodeError,
    CartError,
    CartNotFoundError,
    CartValidationError,
    OrderError,
    OrderCreationError,
    InvalidOrderDataError,
    UnauthorizedError,
    InternalServerError,
)


class TestExceptionHierarchy:
    """Test exception hierarchy and structure."""

    def test_mcp_exception_base(self):
        """Test MCPException base exception."""
        error = MCPException("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_shipping_exception(self):
        """Test ShippingException."""
        error = ShippingException("Shipping error")
        assert isinstance(error, MCPException)

    def test_pricing_exception(self):
        """Test PricingException."""
        error = PricingException("Pricing error")
        assert isinstance(error, MCPException)

    def test_rfq_exception(self):
        """Test RFQException."""
        error = RFQException("RFQ error")
        assert isinstance(error, MCPException)

    def test_customer_exception(self):
        """Test CustomerException."""
        error = CustomerException("Customer error")
        assert isinstance(error, MCPException)

    def test_validation_exception(self):
        """Test ValidationException."""
        error = ValidationException("Validation error")
        assert isinstance(error, MCPException)

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Not found")
        assert isinstance(error, MCPException)

    def test_product_not_found_error(self):
        """Test ProductNotFoundError."""
        error = ProductNotFoundError("prod-123")
        assert "prod-123" in str(error)
        assert isinstance(error, NotFoundError)

    def test_product_search_error(self):
        """Test ProductSearchError."""
        error = ProductSearchError("Search failed")
        assert isinstance(error, MCPException)

    def test_inventory_error(self):
        """Test InventoryError."""
        error = InventoryError("Inventory error")
        assert isinstance(error, MCPException)

    def test_inventory_not_found_error(self):
        """Test InventoryNotFoundError."""
        error = InventoryNotFoundError("prod-123")
        assert "prod-123" in str(error)
        assert isinstance(error, NotFoundError)

    def test_insufficient_inventory_error(self):
        """Test InsufficientInventoryError."""
        error = InsufficientInventoryError("Not enough stock")
        assert isinstance(error, InventoryError)

    def test_pricing_error(self):
        """Test PricingError."""
        error = PricingError("Pricing error")
        assert isinstance(error, MCPException)

    def test_invalid_discount_code_error(self):
        """Test InvalidDiscountCodeError."""
        error = InvalidDiscountCodeError("Invalid code")
        assert isinstance(error, PricingError)

    def test_cart_error(self):
        """Test CartError."""
        error = CartError("Cart error")
        assert isinstance(error, MCPException)

    def test_cart_not_found_error(self):
        """Test CartNotFoundError."""
        error = CartNotFoundError("cart-123")
        assert "cart-123" in str(error)
        assert isinstance(error, NotFoundError)

    def test_cart_validation_error(self):
        """Test CartValidationError."""
        error = CartValidationError("Invalid cart")
        assert isinstance(error, CartError)

    def test_order_error(self):
        """Test OrderError."""
        error = OrderError("Order error")
        assert isinstance(error, MCPException)

    def test_order_creation_error(self):
        """Test OrderCreationError."""
        error = OrderCreationError("Cannot create order")
        assert isinstance(error, OrderError)

    def test_invalid_order_data_error(self):
        """Test InvalidOrderDataError."""
        error = InvalidOrderDataError("Invalid data")
        assert isinstance(error, OrderError)

    def test_unauthorized_error(self):
        """Test UnauthorizedError."""
        error = UnauthorizedError("Not authorized")
        assert isinstance(error, MCPException)

    def test_internal_server_error(self):
        """Test InternalServerError."""
        error = InternalServerError("Server error")
        assert isinstance(error, MCPException)


class TestExceptionMessages:
    """Test exception message formatting."""

    def test_product_not_found_message(self):
        """Test ProductNotFoundError message."""
        error = ProductNotFoundError("test-product-id")
        msg = str(error)
        assert "test-product-id" in msg

    def test_cart_not_found_message(self):
        """Test CartNotFoundError message."""
        error = CartNotFoundError("test-cart-id")
        msg = str(error)
        assert "test-cart-id" in msg

    def test_inventory_not_found_message(self):
        """Test InventoryNotFoundError message."""
        error = InventoryNotFoundError("test-product-id")
        msg = str(error)
        assert "test-product-id" in msg


class TestExceptionRaising:
    """Test raising and catching exceptions."""

    def test_catch_product_error(self):
        """Test catching ProductNotFoundError."""
        with pytest.raises(ProductNotFoundError):
            raise ProductNotFoundError("test-id")

    def test_catch_cart_error(self):
        """Test catching CartError."""
        with pytest.raises(CartError):
            raise CartError("test")

    def test_catch_order_error(self):
        """Test catching OrderError."""
        with pytest.raises(OrderError):
            raise OrderError("test")

    def test_catch_inventory_error(self):
        """Test catching InventoryError."""
        with pytest.raises(InventoryError):
            raise InventoryError("test")

    def test_catch_shipping_error(self):
        """Test catching ShippingException."""
        with pytest.raises(ShippingException):
            raise ShippingException("test")

    def test_catch_pricing_error(self):
        """Test catching PricingException."""
        with pytest.raises(PricingException):
            raise PricingException("test")

    def test_catch_mcp_exception_catches_all(self):
        """Test catching MCPException catches all subclasses."""
        with pytest.raises(MCPException):
            raise ProductNotFoundError("test-id")

        with pytest.raises(MCPException):
            raise CartError("test")

        with pytest.raises(MCPException):
            raise OrderError("test")
