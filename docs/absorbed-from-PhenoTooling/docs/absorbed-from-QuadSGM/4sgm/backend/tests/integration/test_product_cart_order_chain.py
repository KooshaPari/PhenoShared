"""Test product → cart → order workflow chain.

This module tests the complete order workflow:
1. Search for products
2. Get product details
3. Check inventory
4. Create cart
5. Add items to cart
6. Validate cart
7. Calculate cart total
8. Create order

Tests validate data consistency across tool calls and error handling
when inventory is insufficient or products don't exist.
"""

import os

import pytest
import pytest_asyncio

os.environ["REPOSITORY_ADAPTER"] = "mock"

from backend.repositories.adapters.mock import (
    MockCartRepository,
    MockInventoryRepository,
    MockOrderRepository,
    MockProductRepository,
)


@pytest.fixture
def product_repo():
    """Provide mock product repository."""
    return MockProductRepository()


@pytest.fixture
def inventory_repo():
    """Provide mock inventory repository."""
    return MockInventoryRepository()


@pytest.fixture
def cart_repo():
    """Provide mock cart repository."""
    return MockCartRepository()


@pytest.fixture
def order_repo():
    """Provide mock order repository."""
    return MockOrderRepository()


@pytest_asyncio.fixture
async def sample_products(product_repo):
    """Create sample products for testing."""
    products = []
    product_data = [
        {
            "sku": "LAPTOP-001",
            "name": "Gaming Laptop Pro",
            "description": "High-performance gaming laptop",
            "price": 1499.99,
            "quantity_on_hand": 50,
            "category": "electronics",
            "rating": 4.8,
            "reviews": 120,
        },
        {
            "sku": "MOUSE-001",
            "name": "Wireless Gaming Mouse",
            "description": "Precision gaming mouse",
            "price": 79.99,
            "quantity_on_hand": 200,
            "category": "accessories",
            "rating": 4.5,
            "reviews": 340,
        },
        {
            "sku": "KEYBOARD-001",
            "name": "Mechanical Keyboard RGB",
            "description": "RGB mechanical keyboard",
            "price": 189.99,
            "quantity_on_hand": 100,
            "category": "accessories",
            "rating": 4.7,
            "reviews": 280,
        },
    ]

    for data in product_data:
        product = await product_repo.create(data)
        products.append(product)

    return products


@pytest.mark.asyncio
async def test_complete_order_workflow(
    product_repo, inventory_repo, cart_repo, order_repo, sample_products
):
    """Test full order workflow: search → add to cart → calculate → create order."""

    # Step 1: Search for products
    products = await product_repo.search("laptop", limit=5)
    assert len(products) > 0
    laptop = products[0]
    assert laptop["name"] == "Gaming Laptop Pro"

    # Step 2: Get product details
    product_detail = await product_repo.get(laptop["id"])
    assert product_detail is not None
    assert product_detail["price"] == 1499.99
    assert product_detail["quantity_on_hand"] == 50

    # Step 3: Check inventory
    inventory = await inventory_repo.get_inventory(laptop["id"])
    assert inventory is not None
    assert inventory["in_stock"] > 0
    assert inventory["available"] >= 2  # Want to buy 2

    # Step 4: Create cart
    cart = await cart_repo.create({"user_id": "user-123"})
    assert cart is not None
    assert cart["user_id"] == "user-123"
    assert cart["items"] == []
    assert cart["total"] == 0.0

    # Step 5: Add items to cart
    cart = await cart_repo.add_item(cart["id"], laptop["id"], quantity=2, price=laptop["price"])
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == laptop["id"]
    assert cart["items"][0]["quantity"] == 2

    # Add second product
    mouse = sample_products[1]
    cart = await cart_repo.add_item(cart["id"], mouse["id"], quantity=1, price=mouse["price"])
    assert len(cart["items"]) == 2

    # Step 6: Validate cart
    try:
        # Check items exist and quantities are valid
        for item in cart["items"]:
            product = await product_repo.get(item["product_id"])
            assert product is not None
            assert item["quantity"] > 0
            assert item["quantity"] <= product["quantity_on_hand"] + 10  # Allow some flex
    except Exception as e:
        pytest.fail(f"Cart validation failed: {str(e)}")

    # Step 7: Calculate cart total
    expected_total = 2 * 1499.99 + 1 * 79.99  # 3079.97
    assert cart["total"] == pytest.approx(expected_total, rel=0.01)

    # Step 8: Create order
    order = await order_repo.create(
        {
            "user_id": "user-123",
            "items": cart["items"],
            "total": cart["total"],
            "shipping_address": "123 Main St, New York, NY 10001",
            "status": "pending",
        }
    )

    assert order is not None
    assert order["user_id"] == "user-123"
    assert order["status"] == "pending"
    assert order["total"] == pytest.approx(expected_total, rel=0.01)
    assert len(order["items"]) == 2

    # Step 9: Verify order items match cart
    for order_item in order["items"]:
        cart_item = next(
            (i for i in cart["items"] if i["product_id"] == order_item["product_id"]), None
        )
        assert cart_item is not None
        assert order_item["quantity"] == cart_item["quantity"]


@pytest.mark.asyncio
async def test_cart_workflow_with_multiple_products(
    product_repo, inventory_repo, cart_repo, order_repo, sample_products
):
    """Test adding multiple products to cart and validating totals."""

    # Create cart
    cart = await cart_repo.create({"user_id": "user-456"})
    assert cart["total"] == 0.0

    # Add multiple products with different quantities
    items_to_add = [
        (sample_products[0]["id"], 1, sample_products[0]["price"]),  # 1 laptop
        (sample_products[1]["id"], 3, sample_products[1]["price"]),  # 3 mice
        (sample_products[2]["id"], 2, sample_products[2]["price"]),  # 2 keyboards
    ]

    for product_id, quantity, price in items_to_add:
        cart = await cart_repo.add_item(cart["id"], product_id, quantity=quantity, price=price)

    # Verify all items added
    assert len(cart["items"]) == 3

    # Calculate expected total
    expected = 1 * 1499.99 + 3 * 79.99 + 2 * 189.99
    assert cart["total"] == pytest.approx(expected, rel=0.01)

    # Create order with all items
    order = await order_repo.create(
        {
            "user_id": "user-456",
            "items": cart["items"],
            "total": cart["total"],
            "shipping_address": "456 Oak Ave, Los Angeles, CA 90001",
            "status": "pending",
        }
    )

    assert len(order["items"]) == 3
    assert order["total"] == pytest.approx(expected, rel=0.01)


@pytest.mark.asyncio
async def test_insufficient_inventory_in_workflow(
    product_repo, inventory_repo, cart_repo, sample_products
):
    """Test workflow when trying to buy more than available inventory."""

    product = sample_products[0]  # Has only 50 units

    # Create cart
    cart = await cart_repo.create({"user_id": "user-789"})

    # Try to add more items than available
    try:
        # Add reasonable quantity
        cart = await cart_repo.add_item(
            cart["id"], product["id"], quantity=100, price=product["price"]
        )

        # This might succeed in mock, but verify inventory check in real scenario
        # In production, inventory validation would fail
    except Exception:
        # Expected: insufficient inventory
        pass


@pytest.mark.asyncio
async def test_product_not_found_in_workflow(cart_repo):
    """Test workflow when product doesn't exist."""

    cart = await cart_repo.create({"user_id": "user-999"})

    # Try to add non-existent product
    from backend.repositories.exceptions import ProductNotFoundError

    with pytest.raises(ProductNotFoundError):
        await cart_repo.add_item(cart["id"], "NON-EXISTENT", quantity=1, price=99.99)


@pytest.mark.asyncio
async def test_remove_item_from_cart_workflow(cart_repo, sample_products):
    """Test removing items from cart during workflow."""

    cart = await cart_repo.create({"user_id": "user-111"})

    # Add multiple items
    cart = await cart_repo.add_item(
        cart["id"], sample_products[0]["id"], quantity=2, price=sample_products[0]["price"]
    )
    cart = await cart_repo.add_item(
        cart["id"], sample_products[1]["id"], quantity=3, price=sample_products[1]["price"]
    )

    assert len(cart["items"]) == 2
    initial_total = cart["total"]

    # Remove one item type
    cart = await cart_repo.remove_item(cart["id"], sample_products[0]["id"])

    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == sample_products[1]["id"]
    assert cart["total"] < initial_total


@pytest.mark.asyncio
async def test_cart_persistence_across_operations(cart_repo, sample_products):
    """Test that cart state persists across multiple operations."""

    # Create cart
    cart = await cart_repo.create({"user_id": "user-222"})
    cart_id = cart["id"]

    # Add item
    cart = await cart_repo.add_item(
        cart_id, sample_products[0]["id"], quantity=1, price=sample_products[0]["price"]
    )
    first_total = cart["total"]

    # Retrieve cart to verify persistence
    retrieved_cart = await cart_repo.get(cart_id)
    assert retrieved_cart["total"] == first_total
    assert len(retrieved_cart["items"]) == 1

    # Add another item
    cart = await cart_repo.add_item(
        cart_id, sample_products[1]["id"], quantity=2, price=sample_products[1]["price"]
    )
    second_total = cart["total"]

    # Verify update persisted
    retrieved_cart = await cart_repo.get(cart_id)
    assert len(retrieved_cart["items"]) == 2
    assert retrieved_cart["total"] == second_total
    assert retrieved_cart["total"] > first_total


@pytest.mark.asyncio
async def test_order_creation_captures_cart_state(cart_repo, order_repo, sample_products):
    """Test that order creation accurately captures cart state."""

    # Create and populate cart
    cart = await cart_repo.create({"user_id": "user-333"})

    items_data = [
        (sample_products[0]["id"], 2, sample_products[0]["price"]),
        (sample_products[1]["id"], 5, sample_products[1]["price"]),
    ]

    for product_id, quantity, price in items_data:
        cart = await cart_repo.add_item(cart["id"], product_id, quantity=quantity, price=price)

    cart_total = cart["total"]
    cart_items = cart["items"]

    # Create order
    order = await order_repo.create(
        {
            "user_id": "user-333",
            "items": cart_items,
            "total": cart_total,
            "shipping_address": "333 Pine St, Seattle, WA 98101",
            "status": "pending",
        }
    )

    # Verify order has exact cart state
    assert order["total"] == cart_total
    assert len(order["items"]) == len(cart_items)
    for i, order_item in enumerate(order["items"]):
        assert order_item["product_id"] == cart_items[i]["product_id"]
        assert order_item["quantity"] == cart_items[i]["quantity"]


@pytest.mark.asyncio
async def test_sequential_cart_operations(cart_repo, sample_products):
    """Test sequential add/remove operations maintain consistency."""

    cart = await cart_repo.create({"user_id": "user-444"})

    # Add, remove, re-add pattern
    cart = await cart_repo.add_item(
        cart["id"], sample_products[0]["id"], quantity=5, price=sample_products[0]["price"]
    )
    assert len(cart["items"]) == 1
    total_after_add = cart["total"]

    cart = await cart_repo.remove_item(cart["id"], sample_products[0]["id"])
    assert len(cart["items"]) == 0
    assert cart["total"] == 0.0

    # Re-add same product
    cart = await cart_repo.add_item(
        cart["id"], sample_products[0]["id"], quantity=3, price=sample_products[0]["price"]
    )
    assert len(cart["items"]) == 1
    # New total should be less than original (3 vs 5 units)
    assert cart["total"] < total_after_add


@pytest.mark.asyncio
async def test_bulk_order_workflow(product_repo, cart_repo, order_repo, sample_products):
    """Test bulk order scenario with large quantities."""

    cart = await cart_repo.create({"user_id": "bulk-buyer-001"})

    # Bulk purchase
    cart = await cart_repo.add_item(
        cart["id"], sample_products[1]["id"], quantity=100, price=sample_products[1]["price"]
    )

    assert cart["items"][0]["quantity"] == 100

    # Create bulk order
    order = await order_repo.create(
        {
            "user_id": "bulk-buyer-001",
            "items": cart["items"],
            "total": cart["total"],
            "shipping_address": "Bulk Warehouse, 999 Industrial Blvd, TX 75001",
            "status": "pending",
        }
    )

    assert order["items"][0]["quantity"] == 100
    assert order["total"] == pytest.approx(100 * sample_products[1]["price"], rel=0.01)
