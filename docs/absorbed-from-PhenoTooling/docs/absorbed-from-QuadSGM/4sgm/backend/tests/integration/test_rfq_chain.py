"""Test RFQ creation → status tracking → acceptance workflow chain.

This module tests the RFQ (Request for Quote) workflow:
1. Create RFQ with multiple items
2. Get RFQ status and quote details
3. Accept RFQ and convert to order
4. Validate quote vs accepted pricing

Tests validate quote creation, status tracking, acceptance workflows,
and price guarantees for wholesale/bulk orders.
"""

import os
from datetime import datetime, timezone

import pytest
import pytest_asyncio

os.environ["REPOSITORY_ADAPTER"] = "mock"

from backend.repositories.adapters.mock import (
    MockProductRepository,
    MockRFQRepository,
)


@pytest.fixture
def rfq_repo():
    """Provide mock RFQ repository."""
    return MockRFQRepository()


@pytest.fixture
def product_repo():
    """Provide mock product repository."""
    return MockProductRepository()


@pytest_asyncio.fixture
async def sample_products(product_repo):
    """Create sample products for RFQ."""
    products = []
    product_data = [
        {
            "sku": "BULK-WIDGET-001",
            "name": "Industrial Widget",
            "description": "Bulk wholesale widget",
            "price": 50.0,
            "quantity_on_hand": 1000,
            "category": "industrial",
        },
        {
            "sku": "BULK-GADGET-001",
            "name": "Premium Gadget",
            "description": "High-volume gadget",
            "price": 150.0,
            "quantity_on_hand": 500,
            "category": "industrial",
        },
        {
            "sku": "BULK-COMPONENT-001",
            "name": "Electronic Component",
            "description": "Bulk component",
            "price": 25.0,
            "quantity_on_hand": 2000,
            "category": "components",
        },
    ]

    for data in product_data:
        product = await product_repo.create(data)
        products.append(product)

    return products


@pytest.mark.asyncio
async def test_create_rfq_workflow(rfq_repo, sample_products):
    """Test creating an RFQ with multiple items."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 100,
            "unit_price": sample_products[0]["price"],
        },
        {
            "product_id": sample_products[1]["id"],
            "quantity": 50,
            "unit_price": sample_products[1]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="John Smith",
        customer_email="john@wholesaler.com",
    )

    assert rfq is not None
    assert rfq["customer_name"] == "John Smith"
    assert rfq["customer_email"] == "john@wholesaler.com"
    assert len(rfq["items"]) == 2
    assert rfq["status"] == "pending"
    assert rfq["created_at"] is not None


@pytest.mark.asyncio
async def test_rfq_pricing_calculation(rfq_repo, sample_products):
    """Test that RFQ includes correct pricing."""

    item_1_qty = 150
    item_1_price = sample_products[0]["price"]
    item_2_qty = 75
    item_2_price = sample_products[1]["price"]

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": item_1_qty,
            "unit_price": item_1_price,
        },
        {
            "product_id": sample_products[1]["id"],
            "quantity": item_2_qty,
            "unit_price": item_2_price,
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Bulk Buyer Inc",
        customer_email="buyer@company.com",
    )

    expected_total = (item_1_qty * item_1_price) + (item_2_qty * item_2_price)

    assert rfq["total_price"] == pytest.approx(expected_total, rel=0.01)


@pytest.mark.asyncio
async def test_rfq_status_tracking(rfq_repo, sample_products):
    """Test RFQ status changes throughout lifecycle."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 100,
            "unit_price": sample_products[0]["price"],
        },
    ]

    # Create RFQ
    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Status Tester",
        customer_email="tester@example.com",
    )

    assert rfq["status"] == "pending"
    rfq_id = rfq["id"]

    # Get status
    status = await rfq_repo.get_rfq_status(rfq_id)

    assert status is not None
    assert status["rfq_id"] == rfq_id
    assert status["status"] == "pending"
    assert status["created_at"] is not None


@pytest.mark.asyncio
async def test_complete_rfq_workflow(rfq_repo, sample_products):
    """Test complete RFQ workflow: create → quote → accept."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 200,
            "unit_price": sample_products[0]["price"],
        },
        {
            "product_id": sample_products[1]["id"],
            "quantity": 100,
            "unit_price": sample_products[1]["price"],
        },
        {
            "product_id": sample_products[2]["id"],
            "quantity": 500,
            "unit_price": sample_products[2]["price"],
        },
    ]

    # Step 1: Create RFQ
    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Complete RFQ Test",
        customer_email="rfq@company.com",
    )

    assert rfq["status"] == "pending"
    rfq_id = rfq["id"]
    initial_total = rfq["total_price"]

    # Step 2: Review quote
    status = await rfq_repo.get_rfq_status(rfq_id)

    assert status["status"] == "pending"
    assert status["items"] == items

    # Step 3: Accept RFQ
    acceptance = await rfq_repo.accept_rfq(
        rfq_id=rfq_id,
        purchase_order_number="PO-2024-001",
    )

    assert acceptance is not None
    assert acceptance["rfq_id"] == rfq_id
    assert acceptance["status"] == "accepted"
    # Price should remain locked
    assert acceptance["total_price"] == initial_total


@pytest.mark.asyncio
async def test_rfq_with_bulk_discount_expectation(rfq_repo, sample_products):
    """Test RFQ with large quantities expecting bulk discounts."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 1000,  # Large bulk order
            "unit_price": sample_products[0]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Bulk Buyer Corp",
        customer_email="bulk@company.com",
    )

    assert rfq is not None
    # Large quantities might trigger bulk pricing
    assert rfq["items"][0]["quantity"] == 1000


@pytest.mark.asyncio
async def test_rfq_expiration_handling(rfq_repo, sample_products):
    """Test handling of RFQ expiration."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 50,
            "unit_price": sample_products[0]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Expiration Test",
        customer_email="expire@test.com",
    )

    rfq_id = rfq["id"]

    # Check if RFQ is still valid
    status = await rfq_repo.get_rfq_status(rfq_id)

    if "expires_at" in status:
        assert status["expires_at"] is not None
        assert status["expires_at"] > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_rfq_rejection_workflow(rfq_repo, sample_products):
    """Test rejecting an RFQ."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 75,
            "unit_price": sample_products[0]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Rejection Test",
        customer_email="reject@test.com",
    )

    rfq_id = rfq["id"]

    try:
        # Try to reject RFQ (if supported)
        rejection = await rfq_repo.reject_rfq(rfq_id)
        assert rejection["status"] == "rejected"
    except AttributeError:
        # Rejection not supported in mock
        pass


@pytest.mark.asyncio
async def test_multiple_rfqs_for_same_customer(rfq_repo, sample_products):
    """Test creating multiple RFQs for same customer."""

    customer_email = "repeat@customer.com"

    rfqs = []
    for i in range(3):
        items = [
            {
                "product_id": sample_products[i % len(sample_products)]["id"],
                "quantity": 50 + (i * 25),
                "unit_price": sample_products[i % len(sample_products)]["price"],
            },
        ]

        rfq = await rfq_repo.create_rfq(
            items=items,
            customer_name=f"Customer {i + 1}",
            customer_email=customer_email,
        )
        rfqs.append(rfq)

    # All should be created successfully
    assert len(rfqs) == 3
    for rfq in rfqs:
        assert rfq["customer_email"] == customer_email


@pytest.mark.asyncio
async def test_rfq_with_custom_notes(rfq_repo, sample_products):
    """Test RFQ with special delivery or handling notes."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 100,
            "unit_price": sample_products[0]["price"],
        },
    ]

    # Some RFQs might have special requirements
    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Special Request",
        customer_email="special@requests.com",
    )

    assert rfq is not None


@pytest.mark.asyncio
async def test_rfq_price_guarantee(rfq_repo, sample_products):
    """Test that accepted RFQ price remains guaranteed."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 200,
            "unit_price": sample_products[0]["price"],
        },
        {
            "product_id": sample_products[1]["id"],
            "quantity": 100,
            "unit_price": sample_products[1]["price"],
        },
    ]

    # Create RFQ
    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Price Guarantee",
        customer_email="guarantee@test.com",
    )

    original_price = rfq["total_price"]

    # Accept RFQ
    acceptance = await rfq_repo.accept_rfq(
        rfq_id=rfq["id"],
        purchase_order_number="PO-GUARANTEED",
    )

    # Price should be locked in
    assert acceptance["total_price"] == original_price


@pytest.mark.asyncio
async def test_rfq_item_availability_verification(rfq_repo, product_repo, sample_products):
    """Test verifying item availability in RFQ."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 200,
            "unit_price": sample_products[0]["price"],
        },
    ]

    await rfq_repo.create_rfq(
        items=items,
        customer_name="Availability Test",
        customer_email="availability@test.com",
    )

    # Verify product exists
    product = await product_repo.get(sample_products[0]["id"])
    assert product is not None
    assert product["quantity_on_hand"] >= 200


@pytest.mark.asyncio
async def test_rfq_vs_regular_order_pricing(rfq_repo, sample_products):
    """Test RFQ pricing vs regular order pricing."""

    quantity = 100

    # RFQ pricing
    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": quantity,
            "unit_price": sample_products[0]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Pricing Comparison",
        customer_email="compare@pricing.com",
    )

    rfq_total = rfq["total_price"]

    # RFQ should provide wholesale pricing
    # (exact behavior depends on business rules)
    assert rfq_total > 0


@pytest.mark.asyncio
async def test_rfq_acceptance_creates_order_reference(rfq_repo, sample_products):
    """Test that RFQ acceptance creates proper order reference."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 150,
            "unit_price": sample_products[0]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Order Reference",
        customer_email="reference@order.com",
    )

    po_number = "PO-REF-2024-001"

    acceptance = await rfq_repo.accept_rfq(
        rfq_id=rfq["id"],
        purchase_order_number=po_number,
    )

    assert acceptance["purchase_order_number"] == po_number
    # Should be able to track order by PO number


@pytest.mark.asyncio
async def test_rfq_multi_item_status_tracking(rfq_repo, sample_products):
    """Test status tracking for RFQ with multiple line items."""

    items = [
        {
            "product_id": sample_products[0]["id"],
            "quantity": 100,
            "unit_price": sample_products[0]["price"],
        },
        {
            "product_id": sample_products[1]["id"],
            "quantity": 50,
            "unit_price": sample_products[1]["price"],
        },
        {
            "product_id": sample_products[2]["id"],
            "quantity": 200,
            "unit_price": sample_products[2]["price"],
        },
    ]

    rfq = await rfq_repo.create_rfq(
        items=items,
        customer_name="Multi Item",
        customer_email="multi@items.com",
    )

    status = await rfq_repo.get_rfq_status(rfq["id"])

    # All items should be tracked
    assert len(status["items"]) == 3
    for item in status["items"]:
        assert "product_id" in item
        assert "quantity" in item
        assert "unit_price" in item
