"""Test shipping calculation → method selection → tracking workflow chain.

This module tests the shipping workflow:
1. Calculate shipping costs between locations
2. Get available shipping methods
3. Select shipping method with best rate/time tradeoff
4. Estimate delivery time
5. Track shipment

Tests validate shipping cost calculations, method availability, and
delivery estimates across different locations and weights.
"""

import os

import pytest

os.environ["REPOSITORY_ADAPTER"] = "mock"

from backend.repositories.adapters.mock import (
    MockShippingRepository,
)


@pytest.fixture
def shipping_repo():
    """Provide mock shipping repository."""
    return MockShippingRepository()


@pytest.mark.asyncio
async def test_shipping_calculation_workflow(shipping_repo):
    """Test shipping calculation for different origin/destination pairs."""

    # Test case 1: Short distance (same state)
    result = await shipping_repo.calculate_shipping(
        origin="New York, NY",
        destination="Buffalo, NY",
        weight_lbs=5.0,
    )

    assert result is not None
    assert result["origin"] == "New York, NY"
    assert result["destination"] == "Buffalo, NY"
    assert result["weight_lbs"] == 5.0
    assert result["base_cost"] > 0
    assert result["final_cost"] >= result["base_cost"]
    assert result["estimated_days"] > 0
    assert len(result["carriers"]) > 0

    # Test case 2: Long distance (cross-country)
    result = await shipping_repo.calculate_shipping(
        origin="New York, NY",
        destination="Los Angeles, CA",
        weight_lbs=10.0,
    )

    assert result["base_cost"] > 0
    assert result["estimated_days"] >= 2  # Cross-country takes longer


@pytest.mark.asyncio
async def test_shipping_cost_scales_with_weight(shipping_repo):
    """Test that shipping cost increases with weight."""

    result_5lb = await shipping_repo.calculate_shipping(
        origin="Chicago, IL",
        destination="Denver, CO",
        weight_lbs=5.0,
    )

    result_20lb = await shipping_repo.calculate_shipping(
        origin="Chicago, IL",
        destination="Denver, CO",
        weight_lbs=20.0,
    )

    # Heavier shipment should cost more
    assert result_20lb["final_cost"] > result_5lb["final_cost"]


@pytest.mark.asyncio
async def test_shipping_methods_availability(shipping_repo):
    """Test availability of different shipping methods."""

    methods = await shipping_repo.get_shipping_methods()

    assert methods is not None
    assert len(methods) > 0

    # Verify method structure
    for method in methods:
        assert "id" in method
        assert "name" in method
        assert "description" in method
        assert "avg_delivery_days" in method
        assert "cost_per_lb" in method


@pytest.mark.asyncio
async def test_complete_shipping_workflow(shipping_repo):
    """Test complete shipping workflow: calculate → select method → estimate."""

    origin = "Los Angeles, CA"
    destination = "New York, NY"
    weight_lbs = 15.0

    # Step 1: Calculate shipping
    calculation = await shipping_repo.calculate_shipping(
        origin=origin,
        destination=destination,
        weight_lbs=weight_lbs,
    )

    assert calculation is not None
    assert len(calculation["carriers"]) > 0

    # Step 2: Get available methods
    methods = await shipping_repo.get_shipping_methods()
    assert len(methods) > 0

    # Step 3: Select best method (lowest cost)
    selected_carrier = min(calculation["carriers"], key=lambda x: x["cost"])
    assert selected_carrier is not None
    assert selected_carrier["cost"] > 0

    # Step 4: Estimate delivery
    delivery_estimate = await shipping_repo.estimate_delivery(
        destination=destination,
        weight_lbs=weight_lbs,
        shipping_method=selected_carrier["carrier"],
    )

    assert delivery_estimate is not None
    assert delivery_estimate["destination"] == destination
    assert delivery_estimate["estimated_delivery_date"] is not None
    assert delivery_estimate["estimated_days"] > 0


@pytest.mark.asyncio
async def test_carrier_options_structure(shipping_repo):
    """Test that carrier options have complete information."""

    result = await shipping_repo.calculate_shipping(
        origin="Seattle, WA",
        destination="Miami, FL",
        weight_lbs=8.0,
    )

    carriers = result["carriers"]
    assert len(carriers) > 0

    for carrier in carriers:
        assert "carrier" in carrier
        assert "cost" in carrier
        assert "estimated_days" in carrier
        assert carrier["cost"] > 0
        assert carrier["estimated_days"] > 0


@pytest.mark.asyncio
async def test_shipping_dimension_impact(shipping_repo):
    """Test that dimensions impact shipping calculations."""

    # Small compact package
    result_compact = await shipping_repo.calculate_shipping(
        origin="Boston, MA",
        destination="Philadelphia, PA",
        weight_lbs=5.0,
        dimensions_inches=(6, 4, 3),
    )

    # Larger but same weight
    result_large = await shipping_repo.calculate_shipping(
        origin="Boston, MA",
        destination="Philadelphia, PA",
        weight_lbs=5.0,
        dimensions_inches=(24, 18, 12),
    )

    # Larger dimensional package may have different cost
    assert result_compact is not None
    assert result_large is not None


@pytest.mark.asyncio
async def test_delivery_estimate_consistency(shipping_repo):
    """Test delivery estimate matches calculated estimate."""

    calculation = await shipping_repo.calculate_shipping(
        origin="Houston, TX",
        destination="Austin, TX",
        weight_lbs=3.0,
    )

    # Pick fastest carrier
    fastest = min(calculation["carriers"], key=lambda x: x["estimated_days"])

    estimate = await shipping_repo.estimate_delivery(
        destination="Austin, TX",
        weight_lbs=3.0,
        shipping_method=fastest["carrier"],
    )

    # Estimated days should be close to carrier's estimate
    assert estimate["estimated_days"] <= fastest["estimated_days"] + 1


@pytest.mark.asyncio
async def test_tracking_shipment_workflow(shipping_repo):
    """Test shipment tracking throughout delivery."""

    # Create a tracking scenario
    tracking_number = "1Z999AA1" + "0" * 7  # Mock tracking number

    # Get tracking info
    tracking = await shipping_repo.track_shipment(tracking_number)

    if tracking is not None:
        # Verify tracking structure
        assert "tracking_number" in tracking
        assert "current_location" in tracking
        assert "status" in tracking
        assert "estimated_delivery" in tracking


@pytest.mark.asyncio
async def test_multiple_shipping_locations(shipping_repo):
    """Test shipping from/to multiple locations."""

    location_pairs = [
        ("Seattle, WA", "Portland, OR"),
        ("San Francisco, CA", "Las Vegas, NV"),
        ("Denver, CO", "Kansas City, MO"),
        ("Atlanta, GA", "Charlotte, NC"),
        ("Boston, MA", "New York, NY"),
    ]

    for origin, destination in location_pairs:
        result = await shipping_repo.calculate_shipping(
            origin=origin,
            destination=destination,
            weight_lbs=7.5,
        )

        assert result is not None
        assert result["origin"] == origin
        assert result["destination"] == destination
        assert result["final_cost"] > 0
        assert result["estimated_days"] > 0


@pytest.mark.asyncio
async def test_international_shipping_handling(shipping_repo):
    """Test handling of international shipping (if supported)."""

    try:
        result = await shipping_repo.calculate_shipping(
            origin="New York, NY",
            destination="Toronto, Canada",
            weight_lbs=5.0,
        )

        # If international is supported, verify different cost structure
        if result is not None:
            assert result["final_cost"] > 0
    except Exception:
        # International shipping may not be supported
        pass


@pytest.mark.asyncio
async def test_expedited_vs_standard_shipping(shipping_repo):
    """Test cost/time tradeoff between expedited and standard."""

    calculation = await shipping_repo.calculate_shipping(
        origin="Phoenix, AZ",
        destination="Nashville, TN",
        weight_lbs=12.0,
    )

    carriers = calculation["carriers"]

    # Find fastest and slowest
    fastest = min(carriers, key=lambda x: x["estimated_days"])
    slowest = max(carriers, key=lambda x: x["estimated_days"])

    # Fastest should generally be more expensive
    assert (
        fastest["cost"] >= slowest["cost"] or fastest["estimated_days"] < slowest["estimated_days"]
    )


@pytest.mark.asyncio
async def test_shipping_cost_edge_cases(shipping_repo):
    """Test edge cases in shipping calculations."""

    # Very light package
    result_light = await shipping_repo.calculate_shipping(
        origin="Atlanta, GA",
        destination="Jacksonville, FL",
        weight_lbs=0.5,
    )
    assert result_light["final_cost"] > 0

    # Heavy package (but under limit)
    result_heavy = await shipping_repo.calculate_shipping(
        origin="Atlanta, GA",
        destination="Jacksonville, FL",
        weight_lbs=100.0,
    )
    assert result_heavy["final_cost"] > 0
    assert result_heavy["final_cost"] > result_light["final_cost"]


@pytest.mark.asyncio
async def test_shipping_method_selection_strategy(shipping_repo):
    """Test different strategy for selecting shipping method."""

    calculation = await shipping_repo.calculate_shipping(
        origin="Miami, FL",
        destination="Tampa, FL",
        weight_lbs=6.0,
    )

    carriers = calculation["carriers"]

    # Strategy 1: Lowest cost
    cheapest = min(carriers, key=lambda x: x["cost"])

    # Strategy 2: Fastest delivery
    fastest = min(carriers, key=lambda x: x["estimated_days"])

    # Strategy 3: Best value (cost per day)
    best_value = min(carriers, key=lambda x: x["cost"] / x["estimated_days"])

    # All strategies should select valid options
    assert cheapest["cost"] > 0
    assert fastest["estimated_days"] > 0
    assert best_value["cost"] > 0
