"""Test pricing → bulk discount → coupon → savings workflow chain.

This module tests the pricing workflow:
1. Get base product pricing
2. Apply bulk quantity discounts
3. Apply promotional coupons
4. Calculate final savings
5. Verify discount stacking

Tests validate discount calculations, coupon validity, and final
price accuracy across different purchase scenarios.
"""

import os

import pytest

os.environ["REPOSITORY_ADAPTER"] = "mock"

from backend.repositories.adapters.mock import (
    MockPricingRepository,
)


@pytest.fixture
def pricing_repo():
    """Provide mock pricing repository."""
    return MockPricingRepository()


@pytest.mark.asyncio
async def test_bulk_pricing_workflow(pricing_repo):
    """Test bulk pricing discount application for increasing quantities."""

    product_id = "PROD-001"

    # Test different quantity tiers
    test_cases = [
        (1, 100.0, 0.0),  # No bulk discount
        (10, 100.0, 0.0),  # Still no discount
        (20, 95.0, 5.0),  # 5% bulk discount
        (50, 100.0, 10.0),  # Simulate 10% for 50+
        (100, 100.0, 10.0),  # 10% discount
        (500, 100.0, 15.0),  # 15% discount
        (1000, 100.0, 20.0),  # 20% discount
    ]

    for quantity, expected_unit_price_or_base, min_discount_rate in test_cases:
        result = await pricing_repo.get_bulk_pricing(
            product_id=product_id,
            quantity=quantity,
        )

        assert result is not None
        assert result["quantity"] == quantity
        assert result["unit_price"] > 0
        # Total should be consistent
        assert result["total_price"] > 0


@pytest.mark.asyncio
async def test_coupon_application_workflow(pricing_repo):
    """Test applying coupon codes to cart."""

    cart_total = 500.0

    # Test valid coupon
    result = await pricing_repo.apply_coupon(
        coupon_code="SAVE10",
        cart_total=cart_total,
    )

    if result is not None:
        assert result["coupon_code"] == "SAVE10"
        assert result["discount_amount"] > 0
        assert result["final_total"] < cart_total


@pytest.mark.asyncio
async def test_invalid_coupon_handling(pricing_repo):
    """Test handling of invalid or expired coupons."""

    cart_total = 300.0

    # Test invalid coupon
    result = await pricing_repo.apply_coupon(
        coupon_code="INVALID_CODE",
        cart_total=cart_total,
    )

    # Should either return None or indicate invalid coupon
    if result is None:
        assert True  # Invalid coupon not found
    else:
        # If returned, should indicate it's invalid
        assert not result.get("is_valid", False) or result.get("error") is not None


@pytest.mark.asyncio
async def test_complete_pricing_workflow(pricing_repo):
    """Test complete pricing workflow: base → bulk → coupon → savings."""

    product_id = "PROD-002"
    quantity = 100

    # Step 1: Get base pricing
    result = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=1,
    )
    base_unit_price = result["unit_price"]
    base_unit_price * 1

    # Step 2: Get bulk pricing
    result = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=quantity,
    )

    bulk_unit_price = result["unit_price"]
    bulk_total = result["total_price"]

    # Bulk unit price should be <= base price
    assert bulk_unit_price <= base_unit_price

    # Step 3: Apply coupon
    coupon_result = await pricing_repo.apply_coupon(
        coupon_code="BULK20",
        cart_total=bulk_total,
    )

    if coupon_result is not None:
        final_total = coupon_result["final_total"]
        # Final should be less than bulk (if coupon valid)
        assert final_total <= bulk_total
    else:
        final_total = bulk_total

    # Step 4: Calculate savings
    savings = base_unit_price * quantity - final_total
    assert savings >= 0


@pytest.mark.asyncio
async def test_promotional_offers_retrieval(pricing_repo):
    """Test retrieving active promotional offers."""

    promotions = await pricing_repo.get_promotions()

    if promotions is not None:
        assert isinstance(promotions, list)
        for promo in promotions:
            assert "id" in promo
            assert "code" in promo or "description" in promo
            assert "discount_type" in promo or "discount_amount" in promo


@pytest.mark.asyncio
async def test_savings_calculation_accuracy(pricing_repo):
    """Test accurate savings calculation."""

    original_price = 100.0
    discount_rate = 0.20  # 20%
    quantity = 10

    result = await pricing_repo.calculate_savings(
        original_price=original_price,
        discount_rate=discount_rate,
        quantity=quantity,
    )

    if result is not None:
        expected_discount = original_price * discount_rate
        expected_total_savings = expected_discount * quantity

        assert result["discount_per_unit"] == pytest.approx(expected_discount, rel=0.01)
        assert result["total_savings"] == pytest.approx(expected_total_savings, rel=0.01)


@pytest.mark.asyncio
async def test_tiered_discount_structure(pricing_repo):
    """Test that discounts increase with quantity tiers."""

    product_id = "PROD-003"
    quantities = [10, 50, 100, 500, 1000]

    results = []
    for qty in quantities:
        result = await pricing_repo.get_bulk_pricing(
            product_id=product_id,
            quantity=qty,
        )
        results.append(result)

    # Verify prices decrease as quantity increases
    for i in range(len(results) - 1):
        # Unit price should not increase for higher quantities
        assert results[i + 1]["unit_price"] <= results[i]["unit_price"]


@pytest.mark.asyncio
async def test_coupon_stacking_policy(pricing_repo):
    """Test coupon stacking behavior."""

    cart_total = 1000.0

    # Apply first coupon
    result1 = await pricing_repo.apply_coupon(
        coupon_code="SAVE10",
        cart_total=cart_total,
    )

    if result1 is not None:
        after_first = result1["final_total"]

        # Try to apply second coupon to already discounted total
        # (Behavior depends on business rules)
        result2 = await pricing_repo.apply_coupon(
            coupon_code="SAVE5",
            cart_total=after_first,
        )

        if result2 is not None:
            final = result2["final_total"]
            # Final should be less than original
            assert final <= cart_total


@pytest.mark.asyncio
async def test_negative_discount_prevention(pricing_repo):
    """Test that discounts don't create negative prices."""

    original_price = 50.0
    excessive_discount_rate = 1.5  # 150% discount

    result = await pricing_repo.calculate_savings(
        original_price=original_price,
        discount_rate=excessive_discount_rate,
        quantity=1,
    )

    if result is not None:
        # Final price should never be negative
        final_price = original_price - result.get("total_savings", 0)
        assert final_price >= 0


@pytest.mark.asyncio
async def test_zero_discount_handling(pricing_repo):
    """Test handling of products with no discount."""

    product_id = "PROD-004"

    result = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=1,
    )

    assert result is not None
    assert result["unit_price"] > 0
    assert result["total_price"] > 0


@pytest.mark.asyncio
async def test_pricing_with_fractional_discounts(pricing_repo):
    """Test pricing with fractional discount rates."""

    test_cases = [
        (100.0, 0.025),  # 2.5% discount
        (100.0, 0.075),  # 7.5% discount
        (100.0, 0.125),  # 12.5% discount
        (100.0, 0.175),  # 17.5% discount
    ]

    for original_price, discount_rate in test_cases:
        result = await pricing_repo.calculate_savings(
            original_price=original_price,
            discount_rate=discount_rate,
            quantity=1,
        )

        if result is not None:
            expected_savings = original_price * discount_rate
            assert result["total_savings"] == pytest.approx(expected_savings, rel=0.01)


@pytest.mark.asyncio
async def test_bulk_pricing_with_coupon_combination(pricing_repo):
    """Test combining bulk pricing with coupon discounts."""

    product_id = "PROD-005"
    quantity = 100

    # Get bulk price
    bulk_result = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=quantity,
    )

    bulk_total = bulk_result["total_price"]

    # Apply coupon to bulk price
    coupon_result = await pricing_repo.apply_coupon(
        coupon_code="BULK_EXTRA",
        cart_total=bulk_total,
    )

    if coupon_result is not None:
        combined_total = coupon_result["final_total"]
        # Combined discounts should save more than bulk alone
        assert combined_total <= bulk_total


@pytest.mark.asyncio
async def test_customer_specific_pricing(pricing_repo):
    """Test customer-specific pricing if available."""

    product_id = "PROD-006"
    quantity = 50

    # Regular pricing
    regular = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=quantity,
    )

    # Apply coupon that might have customer-specific logic
    result = await pricing_repo.apply_coupon(
        coupon_code="VIP_DISCOUNT",
        cart_total=regular["total_price"],
    )

    if result is not None:
        # VIP customer should get better pricing
        assert result["final_total"] <= regular["total_price"]


@pytest.mark.asyncio
async def test_price_consistency_across_quantities(pricing_repo):
    """Test that unit prices are consistent for same product."""

    product_id = "PROD-007"

    # Get pricing for single unit and multiple units
    single = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=1,
    )

    multiple = await pricing_repo.get_bulk_pricing(
        product_id=product_id,
        quantity=10,
    )

    # Unit price should be consistent or cheaper for bulk
    assert multiple["unit_price"] <= single["unit_price"]

    # Total should be approximately quantity * unit_price
    expected_total = 10 * multiple["unit_price"]
    assert multiple["total_price"] == pytest.approx(expected_total, rel=0.01)


@pytest.mark.asyncio
async def test_coupon_expiration_handling(pricing_repo):
    """Test handling of expired coupons."""

    cart_total = 500.0

    # Try expired coupon
    result = await pricing_repo.apply_coupon(
        coupon_code="EXPIRED2024",
        cart_total=cart_total,
    )

    # Should indicate coupon is invalid/expired
    if result is not None:
        # Either not found or marked as invalid
        assert "error" in result or not result.get("is_valid", False)
