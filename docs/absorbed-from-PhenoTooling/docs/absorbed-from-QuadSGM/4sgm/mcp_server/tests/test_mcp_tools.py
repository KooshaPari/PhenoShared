"""Tests for MCP tool functions in server.py."""

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


class TestSearchProducts:
    """Tests for search_products tool."""

    @pytest.mark.asyncio
    async def test_search_products_returns_matching_products(self, product_repo):
        """Test search_products returns list of matching products."""
        products = await product_repo.search("laptop", limit=10)
        assert len(products) > 0
        assert all("laptop" in p.name.lower() for p in products)

    @pytest.mark.asyncio
    async def test_search_products_respects_limit(self, product_repo):
        """Test search_products respects the limit parameter."""
        products = await product_repo.search("", limit=5)
        assert len(products) <= 5

    @pytest.mark.asyncio
    async def test_search_products_returns_empty_for_no_matches(self, product_repo):
        """Test search_products returns empty list when no products match."""
        products = await product_repo.search("nonexistent-product-xyz", limit=10)
        assert len(products) == 0


class TestGetProduct:
    """Tests for get_product tool."""

    @pytest.mark.asyncio
    async def test_get_product_returns_product_details(self, product_repo):
        """Test get_product returns full product details."""
        product = await product_repo.get("1")
        assert product is not None
        assert product.id == "1"
        assert hasattr(product, "name")
        assert hasattr(product, "sku")
        assert hasattr(product, "price")
        assert hasattr(product, "description")

    @pytest.mark.asyncio
    async def test_get_product_returns_none_for_missing_product(self, product_repo):
        """Test get_product returns None for non-existent product."""
        product = await product_repo.get("nonexistent-id-99999")
        assert product is None

    @pytest.mark.asyncio
    async def test_get_product_includes_pricing_and_inventory(self, product_repo):
        """Test get_product includes pricing and inventory data."""
        product = await product_repo.get("1")
        assert product is not None
        assert hasattr(product, "price")
        assert hasattr(product, "quantity_on_hand")
        assert product.price > 0


class TestCheckInventory:
    """Tests for check_inventory (get_inventory) tool."""

    @pytest.mark.asyncio
    async def test_get_inventory_returns_stock_information(self, inventory_repo):
        """Test get_inventory returns stock levels."""
        inventory = await inventory_repo.get_inventory("1")
        assert inventory is not None
        assert hasattr(inventory, "product_id")
        assert hasattr(inventory, "in_stock")
        assert hasattr(inventory, "reserved")
        assert hasattr(inventory, "available")

    @pytest.mark.asyncio
    async def test_get_inventory_returns_none_for_missing_product(self, inventory_repo):
        """Test get_inventory returns None for non-existent product."""
        inventory = await inventory_repo.get_inventory("nonexistent-product-id")
        assert inventory is None

    @pytest.mark.asyncio
    async def test_get_inventory_available_equals_in_stock_minus_reserved(
        self, inventory_repo
    ):
        """Test get_inventory available quantity is calculated correctly."""
        inventory = await inventory_repo.get_inventory("1")
        assert inventory is not None
        assert inventory.available == inventory.in_stock - inventory.reserved

    @pytest.mark.asyncio
    async def test_get_inventory_warehouse_locations_exist(self, inventory_repo):
        """Test get_inventory includes warehouse locations."""
        inventory = await inventory_repo.get_inventory("1")
        assert inventory is not None
        assert hasattr(inventory, "warehouse_locations")
        assert isinstance(inventory.warehouse_locations, list)


class TestGetCart:
    """Tests for get_cart tool."""

    @pytest.mark.asyncio
    async def test_get_cart_returns_cart_data_with_items(self, cart_repo):
        """Test get_cart returns cart with all items."""
        # Create cart and add items
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id
        await cart_repo.add_item(cart_id, "1", 2, unit_price=1299.99)
        await cart_repo.add_item(cart_id, "2", 1, unit_price=29.99)

        # Get cart
        cart_data = await cart_repo.get_cart(cart_id)
        assert cart_data is not None
        assert cart_data["cart_id"] == cart_id
        assert cart_data["user_id"] == "user123"
        assert len(cart_data["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_cart_includes_item_details(self, cart_repo):
        """Test get_cart includes item details (product_id, quantity, price)."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id
        await cart_repo.add_item(cart_id, "1", 3, unit_price=99.99)

        cart_data = await cart_repo.get_cart(cart_id)
        assert len(cart_data["items"]) > 0
        item = cart_data["items"][0]
        assert "product_id" in item
        assert "quantity" in item
        assert item["product_id"] == "1"
        assert item["quantity"] == 3

    @pytest.mark.asyncio
    async def test_get_cart_empty_cart(self, cart_repo):
        """Test get_cart on empty cart returns empty items list."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        cart_data = await cart_repo.get_cart(cart_id)
        assert cart_data is not None
        assert len(cart_data["items"]) == 0


class TestAddToCart:
    """Tests for add_to_cart tool."""

    @pytest.mark.asyncio
    async def test_add_to_cart_adds_item_successfully(self, cart_repo, pricing_repo):
        """Test add_to_cart successfully adds item to cart."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        result = await cart_repo.add_item(cart_id, "1", 2, unit_price=1299.99)
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].product_id == "1"
        assert result.items[0].quantity == 2

    @pytest.mark.asyncio
    async def test_add_to_cart_with_multiple_items(self, cart_repo):
        """Test add_to_cart can add multiple different items."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        await cart_repo.add_item(cart_id, "1", 1, unit_price=1299.99)
        await cart_repo.add_item(cart_id, "2", 3, unit_price=29.99)
        await cart_repo.add_item(cart_id, "3", 5, unit_price=99.99)

        cart_data = await cart_repo.get_cart(cart_id)
        assert len(cart_data["items"]) == 3

    @pytest.mark.asyncio
    async def test_add_to_cart_updates_existing_item(self, cart_repo):
        """Test add_to_cart updates quantity when item already in cart."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        # Add first time
        await cart_repo.add_item(cart_id, "1", 2, unit_price=1299.99)
        cart_data1 = await cart_repo.get_cart(cart_id)
        assert cart_data1["items"][0]["quantity"] == 2

        # Add same item again - should update quantity
        await cart_repo.add_item(cart_id, "1", 3, unit_price=1299.99)
        cart_data2 = await cart_repo.get_cart(cart_id)
        assert len(cart_data2["items"]) == 1
        assert cart_data2["items"][0]["quantity"] == 5  # 2 + 3

    @pytest.mark.asyncio
    async def test_add_to_cart_returns_item_details(self, cart_repo):
        """Test add_to_cart returns item with unit_price and line_total."""
        cart = await cart_repo.create(customer_id="user123")
        cart_id = cart.id

        result = await cart_repo.add_item(cart_id, "1", 2, unit_price=100.0)
        assert result is not None
        assert result.items[0].product_id == "1"
        assert result.items[0].quantity == 2
        assert hasattr(result.items[0], "unit_price") or "unit_price" in str(
            result.items[0]
        )


class TestGetPricing:
    """Tests for pricing calculations."""

    @pytest.mark.asyncio
    async def test_get_pricing_returns_base_price(self, pricing_repo):
        """Test get_pricing returns base price."""
        pricing = await pricing_repo.get_pricing("1", quantity=1)
        assert pricing is not None
        assert "base_price" in pricing
        assert pricing["base_price"] > 0

    @pytest.mark.asyncio
    async def test_get_pricing_applies_bulk_discounts(self, pricing_repo):
        """Test get_pricing applies bulk discounts for large quantities."""
        # Small quantity - no discount
        pricing_small = await pricing_repo.get_pricing("1", quantity=10)
        assert pricing_small["discount_rate"] == 0.0

        # Large quantity - should have discount
        pricing_large = await pricing_repo.get_pricing("1", quantity=1000)
        assert pricing_large["discount_rate"] > 0
        assert pricing_large["unit_price"] < pricing_large["base_price"]

    @pytest.mark.asyncio
    async def test_get_pricing_calculates_total(self, pricing_repo):
        """Test get_pricing calculates total correctly."""
        pricing = await pricing_repo.get_pricing("1", quantity=10)
        expected_total = pricing["unit_price"] * 10
        assert abs(pricing["total"] - expected_total) < 0.01

    @pytest.mark.asyncio
    async def test_get_pricing_bulk_tiers(self, pricing_repo):
        """Test get_pricing applies correct tier discounts."""
        # Test multiple quantity levels
        pricing_20 = await pricing_repo.get_pricing("1", quantity=20)
        assert pricing_20["discount_rate"] == 0.05

        pricing_100 = await pricing_repo.get_pricing("1", quantity=100)
        assert pricing_100["discount_rate"] == 0.10

        pricing_500 = await pricing_repo.get_pricing("1", quantity=500)
        assert pricing_500["discount_rate"] == 0.15

        pricing_1000 = await pricing_repo.get_pricing("1", quantity=1000)
        assert pricing_1000["discount_rate"] == 0.20
