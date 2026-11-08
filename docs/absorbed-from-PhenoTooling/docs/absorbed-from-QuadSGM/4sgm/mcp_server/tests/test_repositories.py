"""Smoke tests for in-memory repository implementations."""

import pytest
import pytest_asyncio

from ..repositories.impl.memory import (
    InMemoryProductRepository,
    InMemoryInventoryRepository,
    InMemoryCartRepository,
    InMemoryPricingRepository,
)


@pytest_asyncio.fixture
async def product_repo():
    """Create and return an in-memory product repository."""
    return InMemoryProductRepository()


@pytest_asyncio.fixture
async def inventory_repo():
    """Create and return an in-memory inventory repository."""
    return InMemoryInventoryRepository()


@pytest_asyncio.fixture
async def cart_repo():
    """Create and return an in-memory cart repository."""
    return InMemoryCartRepository()


@pytest_asyncio.fixture
async def pricing_repo():
    """Create and return an in-memory pricing repository."""
    return InMemoryPricingRepository()


class TestInMemoryProductRepository:
    """Tests for InMemoryProductRepository."""

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown_id(self, product_repo):
        """Test that get() returns None for unknown product ID."""
        result = await product_repo.get("unknown-id-12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_product_for_seeded_id(self, product_repo):
        """Test that get() returns product for seeded product IDs."""
        result = await product_repo.get("1")  # LAPTOP-PRO-15 ID
        assert result is not None
        assert result.id == "1"
        assert result.sku == "LAPTOP-PRO-15"
        assert result.name == 'Laptop Pro 15"'
        assert result.price == 1299.99

    @pytest.mark.asyncio
    async def test_get_by_sku(self, product_repo):
        """Test that get_by_sku() returns product by SKU."""
        result = await product_repo.get_by_sku("MOUSE-WIRELESS")
        assert result is not None
        assert result.sku == "MOUSE-WIRELESS"
        assert result.id == "2"

    @pytest.mark.asyncio
    async def test_search_products(self, product_repo):
        """Test that search() finds products by name."""
        results = await product_repo.search("mouse", limit=10)
        assert len(results) > 0
        assert any(p.sku == "MOUSE-WIRELESS" for p in results)


class TestInMemoryInventoryRepository:
    """Tests for InMemoryInventoryRepository."""

    @pytest.mark.asyncio
    async def test_get_inventory_returns_flat_structure(self, inventory_repo):
        """Test that get_inventory() returns _FlatInventory with correct fields."""
        result = await inventory_repo.get_inventory("1")
        assert result is not None
        assert result.product_id == "1"
        assert hasattr(result, "in_stock")
        assert hasattr(result, "reserved")
        assert hasattr(result, "available")
        assert hasattr(result, "warehouse_locations")
        assert result.in_stock == 50  # Initial value
        assert result.reserved == 0
        assert result.available == 50

    @pytest.mark.asyncio
    async def test_get_inventory_returns_none_for_unknown_product(self, inventory_repo):
        """Test that get_inventory() returns None for unknown product."""
        result = await inventory_repo.get_inventory("unknown-product-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_inventory(self, inventory_repo):
        """Test inventory update operation."""
        result = await inventory_repo.update_inventory("1", 10)
        assert result is not None
        assert result.in_stock == 60  # 50 + 10


class TestInMemoryCartRepository:
    """Tests for InMemoryCartRepository."""

    @pytest.mark.asyncio
    async def test_create_cart(self, cart_repo):
        """Test cart creation."""
        cart = await cart_repo.create(customer_id="user123")
        assert cart is not None
        assert cart.id is not None
        assert cart.customer_id == "user123"
        assert cart.items == []

    @pytest.mark.asyncio
    async def test_add_item_to_cart(self, cart_repo):
        """Test adding item to cart."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        result = await cart_repo.add_item(cart_id, "1", 2, unit_price=1299.99)
        assert result is not None
        assert result.id == cart_id
        assert len(result.items) == 1
        assert result.items[0].product_id == "1"
        assert result.items[0].quantity == 2

    @pytest.mark.asyncio
    async def test_get_items_round_trip(self, cart_repo):
        """Test create, add items, and retrieve items workflow."""
        cart = await cart_repo.create(customer_id="user456")
        cart_id = cart.id

        # Add items
        await cart_repo.add_item(cart_id, "1", 1, unit_price=1299.99)
        await cart_repo.add_item(cart_id, "2", 3, unit_price=29.99)

        # Get items
        items = await cart_repo.get_items(cart_id)
        assert len(items) == 2
        assert items[0]["product_id"] == "1"
        assert items[0]["quantity"] == 1
        assert items[1]["product_id"] == "2"
        assert items[1]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_get_cart(self, cart_repo):
        """Test retrieving cart with its items."""
        cart = await cart_repo.create(customer_id="user789")
        cart_id = cart.id

        await cart_repo.add_item(cart_id, "1", 2, unit_price=1299.99)

        cart_data = await cart_repo.get_cart(cart_id)
        assert cart_data is not None
        assert cart_data["cart_id"] == cart_id
        assert cart_data["user_id"] == "user789"
        assert len(cart_data["items"]) == 1


class TestInMemoryPricingRepository:
    """Tests for InMemoryPricingRepository."""

    @pytest.mark.asyncio
    async def test_get_pricing(self, pricing_repo):
        """Test get_pricing() returns pricing dict."""
        result = await pricing_repo.get_pricing("1", quantity=1)
        assert result is not None
        assert "base_price" in result
        assert "discount_rate" in result
        assert "unit_price" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_validate_discount_code_valid_code(self, pricing_repo):
        """Test validate_discount_code() with valid code."""
        result = await pricing_repo.validate_discount_code("SAVE10")
        assert result == 0.10

    @pytest.mark.asyncio
    async def test_validate_discount_code_invalid_code(self, pricing_repo):
        """Test validate_discount_code() with invalid code."""
        result = await pricing_repo.validate_discount_code("INVALID-CODE")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_bulk_pricing_tiers(self, pricing_repo):
        """Test bulk pricing applies correct discounts."""
        # Small quantity - no discount
        result_small = await pricing_repo.get_pricing("1", quantity=5)
        assert result_small["discount_rate"] == 0.0

        # Large quantity - 20% discount
        result_large = await pricing_repo.get_pricing("1", quantity=1000)
        assert result_large["discount_rate"] == 0.20
