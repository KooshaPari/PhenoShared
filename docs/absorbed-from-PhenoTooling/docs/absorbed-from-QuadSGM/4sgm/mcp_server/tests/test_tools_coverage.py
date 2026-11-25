"""Additional coverage tests for MCP tools."""

import pytest
from datetime import datetime, timezone

from ..repositories.impl.memory import (
    InMemoryProductRepository,
    InMemoryInventoryRepository,
    InMemoryCartRepository,
    InMemoryShippingRepository,
    InMemoryRFQRepository,
)
from ..models import (
    ProductResponse,
    InventoryResponse,
    PricingResponse,
    DiscountResponse,
    OrderResponse,
)


class TestInventoryToolsCoverage:
    """Coverage tests for inventory tools."""

    @pytest.mark.asyncio
    async def test_inventory_repo_get_inventory(self):
        """Test getting inventory."""
        repo = InMemoryInventoryRepository()
        inventory = await repo.get_inventory("1")
        assert inventory is not None
        assert inventory.product_id == "1"

    @pytest.mark.asyncio
    async def test_inventory_response_creation(self):
        """Test creating InventoryResponse."""
        response = InventoryResponse(
            product_id="P1",
            in_stock=100,
            reserved=10,
            available=90,
            warehouse_locations=["WH-A"],
        )
        dumped = response.model_dump()
        assert dumped["product_id"] == "P1"
        assert dumped["in_stock"] == 100


class TestOrderToolsCoverage:
    """Coverage tests for order tools."""

    @pytest.mark.asyncio
    async def test_order_response_creation(self):
        """Test creating OrderResponse."""
        response = OrderResponse(
            order_id="ORD-001",
            cart_id="CART-001",
            user_id="user123",
            status="pending",
            created_at=datetime.now(timezone.utc),
            shipping_address="123 Main St",
            tracking_number="TRK-001",
        )
        assert response.order_id == "ORD-001"
        dumped = response.model_dump(exclude_none=True)
        assert isinstance(dumped, dict)


class TestPricingToolsCoverage:
    """Coverage tests for pricing tools."""

    @pytest.mark.asyncio
    async def test_pricing_response_creation(self):
        """Test creating PricingResponse."""
        response = PricingResponse(
            product_id="P1",
            quantity=10,
            base_price=100.0,
            discount_rate=0.1,
            unit_price=90.0,
            total=900.0,
        )
        assert response.quantity == 10
        assert response.discount_rate == 0.1

    @pytest.mark.asyncio
    async def test_discount_response_creation(self):
        """Test creating DiscountResponse."""
        response = DiscountResponse(
            product_id="P1",
            code="SAVE10",
            discount_rate=0.1,
            valid=True,
        )
        dumped = response.model_dump()
        assert dumped["valid"] is True


class TestProductToolsCoverage:
    """Coverage tests for product tools."""

    @pytest.mark.asyncio
    async def test_product_repo_get(self):
        """Test getting product."""
        repo = InMemoryProductRepository()
        product = await repo.get("1")
        assert product is not None
        assert product.id == "1"

    @pytest.mark.asyncio
    async def test_product_repo_search(self):
        """Test searching products."""
        repo = InMemoryProductRepository()
        results = await repo.search("laptop", limit=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_product_response_creation(self):
        """Test creating ProductResponse."""
        response = ProductResponse(
            id="P1",
            name="Laptop",
            sku="SKU-LAP",
            price=999.99,
            description="High-performance laptop",
        )
        dumped = response.model_dump()
        assert dumped["name"] == "Laptop"
        assert dumped["price"] == 999.99


class TestCartToolsCoverage:
    """Coverage tests for cart tools."""

    @pytest.mark.asyncio
    async def test_cart_repo_create(self):
        """Test creating cart."""
        repo = InMemoryCartRepository()
        cart = await repo.create(customer_id="user123")
        assert cart is not None
        assert cart.customer_id == "user123"

    @pytest.mark.asyncio
    async def test_cart_repo_add_item(self):
        """Test adding item to cart."""
        repo = InMemoryCartRepository()
        cart = await repo.create(customer_id="user123")
        result = await repo.add_item(cart.id, "prod1", 2, unit_price=100.0)
        assert result is not None


class TestShippingRepositoryCoverage:
    """Coverage tests for shipping repository."""

    @pytest.mark.asyncio
    async def test_shipping_repo_calculate(self):
        """Test calculating shipping."""
        repo = InMemoryShippingRepository()
        result = await repo.calculate_shipping(
            origin="NY",
            destination="LA",
            weight_lbs=10.0,
        )
        assert result is not None


class TestRFQRepositoryCoverage:
    """Coverage tests for RFQ repository."""

    @pytest.mark.asyncio
    async def test_rfq_repo_create(self):
        """Test creating RFQ."""
        repo = InMemoryRFQRepository()
        items = [{"product_id": "1", "quantity": 100}]
        rfq = await repo.create(
            customer_id="cust1",
            items=items,
        )
        assert rfq is not None


class TestExceptionsCoverage:
    """Coverage tests for exceptions."""

    def test_exception_imports(self):
        """Test that exceptions can be imported."""
        from ..exceptions import (
            InventoryError,
            OrderCreationError,
            PricingError,
        )

        assert InventoryError is not None
        assert OrderCreationError is not None
        assert PricingError is not None
