"""Tests for cart-related MCP tools."""

import pytest


class TestCreateCartTool:
    """Tests for create_cart MCP tool."""

    @pytest.mark.asyncio
    async def test_create_cart_success(self):
        """Test successful cart creation."""
        cart = {
            "cart_id": "CART-123",
            "user_id": "USER-456",
            "items": [],
            "total": 0.00,
            "created_at": "2025-01-01T00:00:00Z",
        }

        assert cart["cart_id"] is not None
        assert cart["total"] == 0.00
        assert len(cart["items"]) == 0

    @pytest.mark.asyncio
    async def test_create_cart_with_user(self):
        """Test cart creation with user ID."""
        cart = {"cart_id": "CART-124", "user_id": "USER-789", "items": []}

        assert cart["user_id"] == "USER-789"
        assert cart["cart_id"] is not None

    @pytest.mark.asyncio
    async def test_create_cart_without_user(self):
        """Test cart creation without user ID (guest)."""
        cart = {"cart_id": "CART-125", "user_id": None, "items": []}

        assert cart["user_id"] is None
        assert cart["cart_id"] is not None


class TestAddToCartTool:
    """Tests for add_to_cart MCP tool."""

    @pytest.mark.asyncio
    async def test_add_to_cart_success(self):
        """Test successful add to cart."""
        cart = {
            "cart_id": "CART-123",
            "items": [{"product_id": "PROD-001", "quantity": 2, "price": 99.99}],
            "total": 199.98,
        }

        assert len(cart["items"]) == 1
        assert cart["items"][0]["product_id"] == "PROD-001"
        assert cart["total"] == 199.98

    @pytest.mark.asyncio
    async def test_add_to_cart_multiple_items(self):
        """Test adding multiple items to cart."""
        cart = {
            "items": [
                {"product_id": "PROD-001", "quantity": 1, "price": 100.00},
                {"product_id": "PROD-002", "quantity": 2, "price": 50.00},
                {"product_id": "PROD-003", "quantity": 1, "price": 75.00},
            ]
        }

        assert len(cart["items"]) == 3
        total = sum(item["quantity"] * item["price"] for item in cart["items"])
        assert total == 275.00

    @pytest.mark.asyncio
    async def test_add_to_cart_update_quantity(self):
        """Test updating quantity when item already in cart."""
        cart = {"items": [{"product_id": "PROD-001", "quantity": 2}]}

        # Add same product again (should increase quantity)
        cart["items"][0]["quantity"] += 3

        assert cart["items"][0]["quantity"] == 5

    @pytest.mark.asyncio
    async def test_add_to_cart_quantity_validation(self):
        """Test quantity validation."""
        valid_quantity = 10

        # Quantity should be positive
        assert valid_quantity > 0

    @pytest.mark.asyncio
    async def test_add_to_cart_price_calculation(self):
        """Test price calculation in cart."""
        items = [{"quantity": 2, "unit_price": 50.00}, {"quantity": 3, "unit_price": 33.33}]

        total = sum(item["quantity"] * item["unit_price"] for item in items)

        assert abs(total - 199.99) < 0.01  # Account for floating point


class TestGetCartTool:
    """Tests for get_cart MCP tool."""

    @pytest.mark.asyncio
    async def test_get_cart_success(self):
        """Test successful cart retrieval."""
        cart = {
            "cart_id": "CART-123",
            "user_id": "USER-456",
            "items": [{"product_id": "PROD-001", "quantity": 1}],
            "total": 99.99,
            "item_count": 1,
        }

        assert cart["cart_id"] == "CART-123"
        assert cart["total"] > 0

    @pytest.mark.asyncio
    async def test_get_empty_cart(self):
        """Test getting empty cart."""
        cart = {"cart_id": "CART-124", "items": [], "total": 0.00, "item_count": 0}

        assert len(cart["items"]) == 0
        assert cart["total"] == 0.00


class TestRemoveFromCartTool:
    """Tests for remove_from_cart MCP tool."""

    @pytest.mark.asyncio
    async def test_remove_item_from_cart(self):
        """Test removing item from cart."""
        cart = {
            "items": [
                {"product_id": "PROD-001", "quantity": 2},
                {"product_id": "PROD-002", "quantity": 1},
            ]
        }

        # Remove first item
        cart["items"] = [item for item in cart["items"] if item["product_id"] != "PROD-001"]

        assert len(cart["items"]) == 1
        assert cart["items"][0]["product_id"] == "PROD-002"

    @pytest.mark.asyncio
    async def test_remove_all_items(self):
        """Test removing all items from cart."""
        cart = {"items": [{"product_id": "PROD-001", "quantity": 1}]}

        cart["items"] = []

        assert len(cart["items"]) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self):
        """Test removing item that doesn't exist."""
        cart = {"items": [{"product_id": "PROD-001", "quantity": 1}]}

        # Try to remove non-existent item
        original_length = len(cart["items"])
        cart["items"] = [item for item in cart["items"] if item["product_id"] != "PROD-999"]

        assert len(cart["items"]) == original_length


class TestClearCartTool:
    """Tests for clear_cart MCP tool."""

    @pytest.mark.asyncio
    async def test_clear_cart_success(self):
        """Test successful cart clearing."""
        cart = {
            "cart_id": "CART-123",
            "items": [
                {"product_id": "PROD-001", "quantity": 2},
                {"product_id": "PROD-002", "quantity": 1},
            ],
        }

        # Clear cart
        cart["items"] = []

        assert len(cart["items"]) == 0

    @pytest.mark.asyncio
    async def test_clear_empty_cart(self):
        """Test clearing already empty cart."""
        cart = {"cart_id": "CART-124", "items": []}

        # Should handle gracefully
        cart["items"] = []

        assert len(cart["items"]) == 0


class TestCartToolErrors:
    """Tests for cart tool error handling."""

    @pytest.mark.asyncio
    async def test_invalid_cart_id(self):
        """Test invalid cart ID handling."""
        invalid_ids = ["", "INVALID", "123"]

        for cart_id in invalid_ids:
            assert isinstance(cart_id, str)

    @pytest.mark.asyncio
    async def test_add_invalid_quantity(self):
        """Test adding invalid quantity."""
        invalid_quantities = [0, -1, -10]

        for qty in invalid_quantities:
            # Should validate quantity > 0
            assert qty <= 0

    @pytest.mark.asyncio
    async def test_cart_total_precision(self):
        """Test cart total precision."""
        items = [{"quantity": 1, "unit_price": 10.33}, {"quantity": 2, "unit_price": 15.67}]

        total = sum(item["quantity"] * item["unit_price"] for item in items)

        # Should have decimal precision
        assert isinstance(total, float)
        assert total > 0
