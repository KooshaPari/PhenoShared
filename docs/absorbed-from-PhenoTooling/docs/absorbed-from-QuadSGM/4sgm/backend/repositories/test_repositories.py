"""Test examples for repositories using mock adapter.

Demonstrates how to write unit tests for services and routes using
the mock repository adapter without requiring a database.

Run with: pytest test_repositories.py -v
"""

import os

import pytest
import pytest_asyncio

# Set to use mock adapter for all tests
os.environ["REPOSITORY_ADAPTER"] = "mock"

from .adapters.mock import (
    MockCartRepository,
    MockCustomerRepository,
    MockOrderRepository,
    MockProductRepository,
)


# Fixtures
@pytest.fixture
def product_repo():
    """Provide mock product repository."""
    return MockProductRepository()


@pytest.fixture
def cart_repo():
    """Provide mock cart repository."""
    return MockCartRepository()


@pytest.fixture
def order_repo():
    """Provide mock order repository."""
    return MockOrderRepository()


@pytest.fixture
def customer_repo():
    """Provide mock customer repository."""
    return MockCustomerRepository()


@pytest_asyncio.fixture
async def sample_product(product_repo):
    """Create sample product for testing."""
    return await product_repo.create(
        {
            "sku": "TEST-001",
            "name": "Test Product",
            "description": "A test product",
            "price": 99.99,
            "quantity_on_hand": 10,
            "category": "test",
        }
    )


@pytest_asyncio.fixture
async def sample_products(product_repo):
    """Create multiple sample products for testing."""
    products = []
    for i in range(1, 4):
        product = await product_repo.create(
            {
                "sku": f"PROD-{i:03d}",
                "name": f"Test Product {i}",
                "description": f"A test product {i}",
                "price": 50.00 * i,
                "quantity_on_hand": 100,
                "category": "test",
            }
        )
        # Register in global registry for cart tests that use hardcoded IDs
        from .adapters.mock import _product_registry

        _product_registry[f"prod-{i}"] = {
            "id": f"prod-{i}",
            "sku": f"PROD-{i:03d}",
            "name": f"Test Product {i}",
            "price": 50.00 * i,
        }
        products.append(product)
    return products


@pytest_asyncio.fixture
async def sample_customer(customer_repo):
    """Create sample customer for testing."""
    return await customer_repo.create(
        {"email": "test@example.com", "name": "Test Customer", "status": "active"}
    )


# Product Repository Tests
@pytest.mark.asyncio
async def test_product_create(product_repo):
    """Test creating a product."""
    product = await product_repo.create(
        {"sku": "SHOE-001", "name": "Running Shoes", "price": 129.99, "quantity_on_hand": 50}
    )

    assert product["id"] is not None
    assert product["sku"] == "SHOE-001"
    assert product["name"] == "Running Shoes"
    assert product["price"] == 129.99


@pytest.mark.asyncio
async def test_product_get(product_repo, sample_product):
    """Test getting a product by ID."""
    product = await product_repo.get(sample_product["id"])

    assert product is not None
    assert product["id"] == sample_product["id"]
    assert product["name"] == "Test Product"


@pytest.mark.asyncio
async def test_product_get_not_found(product_repo):
    """Test getting a non-existent product."""
    product = await product_repo.get("nonexistent")
    assert product is None


@pytest.mark.asyncio
async def test_product_get_by_sku(product_repo, sample_product):
    """Test getting a product by SKU."""
    product = await product_repo.get_by_sku("TEST-001")

    assert product is not None
    assert product["sku"] == "TEST-001"


@pytest.mark.asyncio
async def test_product_list_by_category(product_repo):
    """Test listing products by category."""
    # Create products in different categories
    await product_repo.create(
        {"sku": "SHOE-001", "name": "Shoes", "price": 99.99, "category": "footwear"}
    )
    await product_repo.create(
        {"sku": "SOCK-001", "name": "Socks", "price": 9.99, "category": "footwear"}
    )
    await product_repo.create(
        {"sku": "HAT-001", "name": "Hat", "price": 29.99, "category": "headwear"}
    )

    footwear = await product_repo.list_by_category("footwear")
    assert len(footwear) == 2
    assert all(p["category"] == "footwear" for p in footwear)


@pytest.mark.asyncio
async def test_product_search(product_repo):
    """Test searching products."""
    await product_repo.create(
        {
            "sku": "RED-SHOE",
            "name": "Red Running Shoes",
            "description": "Fast and comfortable",
            "price": 129.99,
        }
    )
    await product_repo.create(
        {
            "sku": "BLUE-SHOE",
            "name": "Blue Casual Shoes",
            "description": "Comfortable casual wear",
            "price": 79.99,
        }
    )

    results = await product_repo.search("running")
    assert len(results) == 1
    assert results[0]["name"] == "Red Running Shoes"


@pytest.mark.asyncio
async def test_product_update(product_repo, sample_product):
    """Test updating a product."""
    updated = await product_repo.update(
        sample_product["id"], {"price": 89.99, "quantity_on_hand": 5}
    )

    assert updated["price"] == 89.99
    assert updated["quantity_on_hand"] == 5
    assert updated["name"] == "Test Product"  # Unchanged


@pytest.mark.asyncio
async def test_product_delete(product_repo, sample_product):
    """Test deleting a product."""
    deleted = await product_repo.delete(sample_product["id"])
    assert deleted is True

    product = await product_repo.get(sample_product["id"])
    assert product is None


@pytest.mark.asyncio
async def test_product_update_inventory(product_repo, sample_product):
    """Test updating inventory."""
    # Decrease inventory
    updated = await product_repo.update_inventory(sample_product["id"], -3)
    assert updated["quantity_on_hand"] == 7

    # Increase inventory
    updated = await product_repo.update_inventory(sample_product["id"], 5)
    assert updated["quantity_on_hand"] == 12

    # Don't go below 0
    updated = await product_repo.update_inventory(sample_product["id"], -20)
    assert updated["quantity_on_hand"] == 0


@pytest.mark.asyncio
async def test_product_get_low_stock(product_repo):
    """Test getting low stock products."""
    await product_repo.create(
        {"sku": "LOW-001", "name": "Low Stock", "price": 99.99, "quantity_on_hand": 3}
    )
    await product_repo.create(
        {"sku": "HIGH-001", "name": "High Stock", "price": 99.99, "quantity_on_hand": 100}
    )

    low_stock = await product_repo.get_low_stock(threshold=10)
    assert len(low_stock) == 1
    assert low_stock[0]["sku"] == "LOW-001"


# Cart Repository Tests
@pytest.mark.asyncio
async def test_cart_create(cart_repo, sample_customer):
    """Test creating a cart."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"], "status": "active"})

    assert cart["id"] is not None
    assert cart["customer_id"] == sample_customer["id"]
    assert cart["status"] == "active"


@pytest.mark.asyncio
async def test_cart_add_item(cart_repo, sample_customer, sample_products):
    """Test adding item to cart."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"]})

    cart = await cart_repo.add_item(cart["id"], product_id="prod-1", quantity=2, price=99.99)

    assert len(cart["cart_items"]) == 1
    assert cart["cart_items"][0]["product_id"] == "prod-1"
    assert cart["cart_items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_cart_get_by_customer(cart_repo, sample_customer):
    """Test getting customer's active cart."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"], "status": "active"})

    retrieved = await cart_repo.get_by_customer(sample_customer["id"])
    assert retrieved is not None
    assert retrieved["id"] == cart["id"]


@pytest.mark.asyncio
async def test_cart_calculate_total(cart_repo, sample_customer, sample_products):
    """Test calculating cart totals."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"]})

    # Add items
    await cart_repo.add_item(cart["id"], "prod-1", 2, 50.00)
    await cart_repo.add_item(cart["id"], "prod-2", 1, 30.00)

    # Calculate totals
    totals = await cart_repo.calculate_total(cart["id"])

    assert totals["subtotal"] == 130.00  # (2 * 50) + (1 * 30)
    assert totals["tax"] == 130.00 * 0.08
    assert totals["shipping"] == 10.00
    assert totals["total"] == 130.00 + (130.00 * 0.08) + 10.00


@pytest.mark.asyncio
async def test_cart_remove_item(cart_repo, sample_customer, sample_products):
    """Test removing item from cart."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"]})
    cart = await cart_repo.add_item(cart["id"], "prod-1", 1, 99.99)

    item_id = cart["cart_items"][0]["id"]
    cart = await cart_repo.remove_item(cart["id"], item_id)

    assert len(cart["cart_items"]) == 0


@pytest.mark.asyncio
async def test_cart_clear(cart_repo, sample_customer, sample_products):
    """Test clearing cart."""
    cart = await cart_repo.create({"customer_id": sample_customer["id"]})
    await cart_repo.add_item(cart["id"], "prod-1", 2, 99.99)
    await cart_repo.add_item(cart["id"], "prod-2", 1, 49.99)

    cart = await cart_repo.clear(cart["id"])

    assert len(cart["cart_items"]) == 0


# Order Repository Tests
@pytest.mark.asyncio
async def test_order_create(order_repo, sample_customer):
    """Test creating an order."""
    order = await order_repo.create({"customer_id": sample_customer["id"], "total": 299.99})

    assert order["id"] is not None
    assert order["customer_id"] == sample_customer["id"]
    assert order["status"] == "pending"


@pytest.mark.asyncio
async def test_order_get_by_customer(order_repo, sample_customer):
    """Test getting customer's orders."""
    await order_repo.create({"customer_id": sample_customer["id"], "total": 100.00})
    await order_repo.create({"customer_id": sample_customer["id"], "total": 200.00})

    orders = await order_repo.get_by_customer(sample_customer["id"])

    assert len(orders) == 2
    assert all(o["customer_id"] == sample_customer["id"] for o in orders)


@pytest.mark.asyncio
async def test_order_get_by_status(order_repo, sample_customer):
    """Test getting orders by status."""
    pending = await order_repo.create({"customer_id": sample_customer["id"]})
    await order_repo.create({"customer_id": sample_customer["id"], "status": "shipped"})

    pending_orders = await order_repo.get_by_status("pending")
    assert len(pending_orders) >= 1
    assert any(o["id"] == pending["id"] for o in pending_orders)


@pytest.mark.asyncio
async def test_order_add_shipment(order_repo, sample_customer):
    """Test adding shipment to order."""
    order = await order_repo.create({"customer_id": sample_customer["id"]})

    order = await order_repo.add_shipment(order["id"], "1Z999999999", "FedEx")

    assert order["status"] == "shipped"
    assert len(order["shipments"]) == 1
    assert order["shipments"][0]["carrier"] == "FedEx"


@pytest.mark.asyncio
async def test_order_update_status(order_repo, sample_customer):
    """Test updating order status."""
    order = await order_repo.create({"customer_id": sample_customer["id"]})

    updated = await order_repo.update_status(order["id"], "processing", "Preparing for shipment")

    assert updated["status"] == "processing"
    assert updated["status_notes"] == "Preparing for shipment"


# Customer Repository Tests
@pytest.mark.asyncio
async def test_customer_create(customer_repo):
    """Test creating a customer."""
    customer = await customer_repo.create({"email": "john@example.com", "name": "John Doe"})

    assert customer["id"] is not None
    assert customer["email"] == "john@example.com"
    assert customer["status"] == "active"


@pytest.mark.asyncio
async def test_customer_get_by_email(customer_repo):
    """Test getting customer by email."""
    created = await customer_repo.create({"email": "jane@example.com", "name": "Jane Doe"})

    customer = await customer_repo.get_by_email("jane@example.com")

    assert customer is not None
    assert customer["id"] == created["id"]


@pytest.mark.asyncio
async def test_customer_add_address(customer_repo, sample_customer):
    """Test adding address to customer."""
    address = await customer_repo.add_address(
        sample_customer["id"],
        {"street": "123 Main St", "city": "Portland", "state": "OR", "zip": "97201"},
    )

    assert address["id"] is not None
    assert address["customer_id"] == sample_customer["id"]
    assert address["city"] == "Portland"


@pytest.mark.asyncio
async def test_customer_get_addresses(customer_repo, sample_customer):
    """Test getting customer's addresses."""
    await customer_repo.add_address(
        sample_customer["id"], {"street": "123 Main St", "city": "Portland"}
    )
    await customer_repo.add_address(
        sample_customer["id"], {"street": "456 Oak Ave", "city": "Seattle"}
    )

    addresses = await customer_repo.get_addresses(sample_customer["id"])

    assert len(addresses) == 2


@pytest.mark.asyncio
async def test_customer_set_default_address(customer_repo, sample_customer):
    """Test setting default address."""
    await customer_repo.add_address(
        sample_customer["id"], {"street": "123 Main St", "city": "Portland"}
    )
    addr2 = await customer_repo.add_address(
        sample_customer["id"], {"street": "456 Oak Ave", "city": "Seattle"}
    )

    await customer_repo.set_default_address(sample_customer["id"], addr2["id"])

    addresses = await customer_repo.get_addresses(sample_customer["id"])
    # First address in list should be the default
    assert addresses[0]["is_default"] is True
    assert addresses[0]["id"] == addr2["id"]


# Integration tests
@pytest.mark.asyncio
async def test_shopping_flow(product_repo, cart_repo, customer_repo, order_repo):
    """Test complete shopping flow: browse, add to cart, checkout."""
    # Create customer
    customer = await customer_repo.create({"email": "shopper@example.com", "name": "Test Shopper"})

    # Create products
    product1 = await product_repo.create(
        {"sku": "PROD-001", "name": "Product 1", "price": 99.99, "quantity_on_hand": 10}
    )
    product2 = await product_repo.create(
        {"sku": "PROD-002", "name": "Product 2", "price": 49.99, "quantity_on_hand": 5}
    )

    # Create cart and add items
    cart = await cart_repo.create({"customer_id": customer["id"]})
    cart = await cart_repo.add_item(cart["id"], product1["id"], 2, product1["price"])
    cart = await cart_repo.add_item(cart["id"], product2["id"], 1, product2["price"])

    # Calculate totals
    cart_total = await cart_repo.calculate_total(cart["id"])
    assert cart_total["subtotal"] == (2 * 99.99) + (1 * 49.99)

    # Create order
    order = await order_repo.create({"customer_id": customer["id"], "total": cart_total["total"]})

    assert order["status"] == "pending"
    assert order["total"] == cart_total["total"]
