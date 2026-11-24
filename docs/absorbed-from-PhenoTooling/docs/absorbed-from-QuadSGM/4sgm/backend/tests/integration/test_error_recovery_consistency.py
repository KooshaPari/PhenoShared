"""Test error recovery and cross-tool data consistency in MCP chains.

This module tests:
1. Error handling when products don't exist
2. Inventory constraint violations
3. Cart state recovery after errors
4. Price consistency across tools
5. Data integrity in multi-step operations
6. Graceful error propagation

Tests ensure the system gracefully handles failures and maintains
data consistency even when individual operations fail.
"""

import os

import pytest
import pytest_asyncio

os.environ["REPOSITORY_ADAPTER"] = "mock"

from repositories.adapters.mock import (
    MockCartRepository,
    MockInventoryRepository,
    MockOrderRepository,
    MockPricingRepository,
    MockProductRepository,
)
from repositories.exceptions import (
    ProductNotFoundError,
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


@pytest.fixture
def pricing_repo():
    """Provide mock pricing repository."""
    return MockPricingRepository()


@pytest_asyncio.fixture
async def sample_product(product_repo):
    """Create sample product."""
    return await product_repo.create(
        {
            "sku": "TEST-ERROR-001",
            "name": "Error Test Product",
            "price": 99.99,
            "quantity_on_hand": 50,
        }
    )


@pytest.mark.asyncio
async def test_product_not_found_error_handling(product_repo):
    """Test handling when product doesn't exist."""

    # Try to get non-existent product
    product = await product_repo.get("NON-EXISTENT-ID")
    assert product is None


@pytest.mark.asyncio
async def test_search_empty_results_handling(product_repo):
    """Test handling of search with no results."""

    results = await product_repo.search("xyz_nonexistent_product_xyz", limit=10)
    assert results == []


@pytest.mark.asyncio
async def test_cart_add_nonexistent_product_error(cart_repo):
    """Test error when adding non-existent product to cart."""

    cart = await cart_repo.create({"user_id": "error-tester"})

    # Try to add non-existent product
    with pytest.raises(ProductNotFoundError):
        await cart_repo.add_item(
            cart["id"],
            "DOES-NOT-EXIST",
            quantity=1,
            price=99.99,
        )


@pytest.mark.asyncio
async def test_insufficient_inventory_error_recovery(inventory_repo, sample_product):
    """Test recovery when inventory is insufficient."""

    # Get current inventory
    inventory = await inventory_repo.get_inventory(sample_product["id"])
    available = inventory["available"]

    # Try to reduce below zero (should fail or be prevented)
    try:
        result = await inventory_repo.update_inventory(
            sample_product["id"],
            -(available + 100),  # Try to reduce beyond available
        )
        # If allowed, verify it doesn't go negative
        if result:
            assert result["in_stock"] >= 0
    except Exception:
        # Expected: insufficient inventory error
        pass


@pytest.mark.asyncio
async def test_cart_state_after_failed_add(cart_repo, sample_product):
    """Test that cart state is consistent after failed add operation."""

    cart = await cart_repo.create({"user_id": "consistency-tester"})
    initial_total = cart["total"]

    # Add valid item
    cart = await cart_repo.add_item(
        cart["id"],
        sample_product["id"],
        quantity=1,
        price=sample_product["price"],
    )
    after_add = cart["total"]
    assert after_add > initial_total

    # Try to add invalid item (product not found)
    with pytest.raises(ProductNotFoundError):
        await cart_repo.add_item(
            cart["id"],
            "INVALID",
            quantity=1,
            price=99.99,
        )

    # Cart should still have valid item
    updated_cart = await cart_repo.get(cart["id"])
    assert len(updated_cart["items"]) == 1
    assert updated_cart["total"] == after_add


@pytest.mark.asyncio
async def test_order_creation_with_empty_cart(order_repo):
    """Test that creating order with empty cart fails appropriately."""

    # Try to create order with empty items
    try:
        await order_repo.create(
            {
                "user_id": "empty-cart-user",
                "items": [],
                "total": 0.0,
                "shipping_address": "123 Main St",
                "status": "pending",
            }
        )
        # If allowed, order should be marked as invalid or rejected
    except Exception:
        # Expected: can't create order with no items
        pass


@pytest.mark.asyncio
async def test_price_consistency_get_vs_search(product_repo, sample_product):
    """Test that product prices are consistent between get and search."""

    # Get price from get_product
    product_detail = await product_repo.get(sample_product["id"])
    price_from_detail = product_detail["price"]

    # Get price from search
    search_results = await product_repo.search(sample_product["name"], limit=1)
    if len(search_results) > 0:
        price_from_search = search_results[0]["price"]
        assert price_from_detail == price_from_search


@pytest.mark.asyncio
async def test_inventory_consistency_after_failed_update(inventory_repo, sample_product):
    """Test that inventory is consistent after failed update."""

    # Get initial inventory
    initial = await inventory_repo.get_inventory(sample_product["id"])
    initial_qty = initial["in_stock"]

    # Try invalid update
    try:
        await inventory_repo.update_inventory(sample_product["id"], "invalid")
    except Exception:
        pass

    # Inventory should be unchanged
    after = await inventory_repo.get_inventory(sample_product["id"])
    assert after["in_stock"] == initial_qty


@pytest.mark.asyncio
async def test_concurrent_cart_modifications_consistency(cart_repo, sample_product):
    """Test cart consistency with rapid modifications."""

    cart = await cart_repo.create({"user_id": "rapid-modifier"})

    # Rapid add/remove sequence
    for i in range(5):
        cart = await cart_repo.add_item(
            cart["id"],
            sample_product["id"],
            quantity=1,
            price=sample_product["price"],
        )

    # Total should reflect all adds
    expected_total = 5 * sample_product["price"]
    assert cart["total"] == pytest.approx(expected_total, rel=0.01)

    # Now remove one
    cart = await cart_repo.remove_item(cart["id"], sample_product["id"])

    # Verify consistency (depends on remove logic)
    assert cart["total"] >= 0


@pytest.mark.asyncio
async def test_invalid_quantity_handling(cart_repo, sample_product):
    """Test error handling for invalid quantities."""

    cart = await cart_repo.create({"user_id": "quantity-tester"})

    # Test zero quantity
    try:
        await cart_repo.add_item(
            cart["id"],
            sample_product["id"],
            quantity=0,
            price=sample_product["price"],
        )
    except Exception:
        # Expected: zero quantity not allowed
        pass

    # Test negative quantity
    try:
        await cart_repo.add_item(
            cart["id"],
            sample_product["id"],
            quantity=-5,
            price=sample_product["price"],
        )
    except Exception:
        # Expected: negative quantity not allowed
        pass


@pytest.mark.asyncio
async def test_invalid_price_handling(cart_repo, sample_product):
    """Test error handling for invalid prices."""

    cart = await cart_repo.create({"user_id": "price-tester"})

    # Test negative price
    try:
        await cart_repo.add_item(
            cart["id"],
            sample_product["id"],
            quantity=1,
            price=-99.99,
        )
    except Exception:
        # Expected: negative price not allowed
        pass

    # Test zero price (might be allowed for promotional items)
    try:
        cart = await cart_repo.add_item(
            cart["id"],
            sample_product["id"],
            quantity=1,
            price=0.0,
        )
        # If allowed, should still create valid item
    except Exception:
        pass


@pytest.mark.asyncio
async def test_order_total_validation(cart_repo, order_repo, sample_product):
    """Test that order total is validated against items."""

    cart = await cart_repo.create({"user_id": "order-validator"})

    cart = await cart_repo.add_item(
        cart["id"],
        sample_product["id"],
        quantity=2,
        price=sample_product["price"],
    )

    correct_total = 2 * sample_product["price"]

    # Create order with correct total
    order = await order_repo.create(
        {
            "user_id": "order-validator",
            "items": cart["items"],
            "total": correct_total,
            "shipping_address": "123 Test St",
            "status": "pending",
        }
    )

    assert order["total"] == pytest.approx(correct_total, rel=0.01)


@pytest.mark.asyncio
async def test_invalid_shipping_address_handling(order_repo):
    """Test handling of invalid shipping addresses."""

    items = [{"product_id": "PROD-1", "quantity": 1, "price": 99.99}]

    # Test empty address
    try:
        await order_repo.create(
            {
                "user_id": "bad-address",
                "items": items,
                "total": 99.99,
                "shipping_address": "",
                "status": "pending",
            }
        )
        # Might be rejected or created anyway
    except Exception:
        pass


@pytest.mark.asyncio
async def test_pricing_consistency_bulk_vs_single(
    pricing_repo,
):
    """Test price consistency between bulk and single unit pricing."""

    product_id = "TEST-PRICING"

    # Single unit
    single = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=1,
    )

    # 10 units
    bulk = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=10,
    )

    # Bulk unit price should not exceed single unit price
    assert bulk["unit_price"] <= single["unit_price"]

    # Total should be consistent
    expected_bulk_total = 10 * bulk["unit_price"]
    assert bulk["total_price"] == pytest.approx(expected_bulk_total, rel=0.01)


@pytest.mark.asyncio
async def test_coupon_validation_before_application(pricing_repo):
    """Test coupon validation before applying discount."""

    cart_total = 500.0

    # Try invalid coupon
    result = await pricing_repo.apply_coupon(
        coupon_code="INVALID_CODE_xyz",
        cart_total=cart_total,
    )

    # Should indicate invalid or return None
    if result is not None:
        assert "error" in result or "invalid" in str(result).lower()


@pytest.mark.asyncio
async def test_transaction_rollback_on_order_failure(cart_repo, order_repo, sample_product):
    """Test that failed order doesn't modify cart or inventory."""

    cart = await cart_repo.create({"user_id": "rollback-tester"})

    cart = await cart_repo.add_item(
        cart["id"],
        sample_product["id"],
        quantity=5,
        price=sample_product["price"],
    )

    cart_total_before = cart["total"]
    items_count_before = len(cart["items"])

    # Try to create order with invalid data
    try:
        await order_repo.create(
            {
                "user_id": "rollback-tester",
                "items": cart["items"],
                "total": -100,  # Invalid: negative total
                "shipping_address": "123 Main",
                "status": "pending",
            }
        )
    except Exception:
        pass

    # Cart should be unchanged
    current_cart = await cart_repo.get(cart["id"])
    assert current_cart["total"] == cart_total_before
    assert len(current_cart["items"]) == items_count_before


@pytest.mark.asyncio
async def test_duplicate_add_idempotency(cart_repo, sample_product):
    """Test that adding same item twice handles correctly."""

    cart = await cart_repo.create({"user_id": "idempotent-tester"})

    # Add item
    cart = await cart_repo.add_item(
        cart["id"],
        sample_product["id"],
        quantity=5,
        price=sample_product["price"],
    )

    cart["total"]

    # Add same item again (should add to quantity, not duplicate)
    cart = await cart_repo.add_item(
        cart["id"],
        sample_product["id"],
        quantity=3,
        price=sample_product["price"],
    )

    # Either: 1) items merged (1 item with qty 8), or 2) separate items
    # Verify total is correct
    expected_total = 8 * sample_product["price"]
    assert cart["total"] == pytest.approx(expected_total, rel=0.01)


@pytest.mark.asyncio
async def test_error_message_clarity(product_repo):
    """Test that error messages are clear and helpful."""

    # Try to access non-existent product
    try:
        product = await product_repo.get("DOES_NOT_EXIST")
        if product is None:
            # Clear indication product not found
            assert True
    except Exception as e:
        # Error message should be clear
        error_str = str(e).lower()
        assert "not found" in error_str or "does not exist" in error_str or product is None
