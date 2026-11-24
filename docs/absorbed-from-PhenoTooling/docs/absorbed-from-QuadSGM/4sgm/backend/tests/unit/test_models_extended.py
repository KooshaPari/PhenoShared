"""Extended tests for Pydantic models."""

import sys
from datetime import date, datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestProductModels:
    """Tests for product models."""

    def test_product_response_with_all_fields(self):
        """Test ProductResponse with all fields."""
        from mcp_server.models import ProductResponse

        response = ProductResponse(
            id="P1",
            name="Test Product",
            sku="SKU123",
            price=99.99,
            description="A test product",
        )
        assert response.id == "P1"
        assert response.name == "Test Product"
        assert response.price == 99.99

    def test_inventory_response_model(self):
        """Test InventoryResponse model."""
        from mcp_server.models import InventoryResponse

        response = InventoryResponse(
            product_id="P1",
            in_stock=100,
            reserved=10,
            available=90,
            warehouse_locations=["WH-A", "WH-B"],
        )
        assert response.in_stock == 100
        assert response.reserved == 10
        assert response.available == 90
        assert len(response.warehouse_locations) == 2

    def test_update_inventory_response_model(self):
        """Test UpdateInventoryResponse model."""
        from mcp_server.models import UpdateInventoryResponse

        response = UpdateInventoryResponse(
            product_id="P1",
            quantity_updated=10,
            new_total=110,
        )
        assert response.quantity_updated == 10
        assert response.new_total == 110


class TestCartModels:
    """Tests for cart models."""

    def test_cart_response_model(self):
        """Test CartResponse model."""
        from mcp_server.models import CartResponse

        response = CartResponse(
            cart_id="CART-001",
            user_id="user123",
            items=[],
        )
        assert response.cart_id == "CART-001"
        assert response.user_id == "user123"
        assert len(response.items) == 0

    def test_cart_item_response(self):
        """Test CartItemResponse model."""
        from mcp_server.models import CartItemResponse

        item = CartItemResponse(
            product_id="P1",
            quantity=2,
            unit_price=50.0,
            line_total=100.0,
        )
        assert item.product_id == "P1"
        assert item.quantity == 2
        assert item.unit_price == 50.0
        assert item.line_total == 100.0


class TestPricingModels:
    """Tests for pricing models."""

    def test_pricing_response_model(self):
        """Test PricingResponse model."""
        from mcp_server.models import PricingResponse

        response = PricingResponse(
            product_id="P1",
            quantity=10,
            base_price=100.0,
            discount_rate=0.1,
            unit_price=90.0,
            total=900.0,
        )
        assert response.discount_rate == 0.1
        assert response.total == 900.0

    def test_discount_response_valid(self):
        """Test DiscountResponse for valid discount."""
        from mcp_server.models import DiscountResponse

        response = DiscountResponse(
            product_id="P1",
            code="SUMMER",
            discount_rate=0.2,
            valid=True,
        )
        assert response.valid is True
        assert response.discount_rate == 0.2

    def test_discount_response_invalid(self):
        """Test DiscountResponse for invalid discount."""
        from mcp_server.models import DiscountResponse

        response = DiscountResponse(
            product_id="P1",
            code="INVALID",
            discount_rate=0.0,
            valid=False,
        )
        assert response.valid is False
        assert response.discount_rate == 0.0


class TestOrderModels:
    """Tests for order models."""

    def test_order_response_model(self):
        """Test OrderResponse model."""
        from mcp_server.models import OrderResponse

        response = OrderResponse(
            order_id="ORD-001",
            cart_id="CART-001",
            user_id="user123",
            status="pending",
            created_at=datetime.now(),
            shipping_address="123 Main St",
            tracking_number="TRK-ABC123",
        )
        assert response.order_id == "ORD-001"
        assert response.status == "pending"
        assert response.tracking_number == "TRK-ABC123"


class TestShippingModels:
    """Tests for shipping models."""

    def test_shipping_calculation_response(self):
        """Test ShippingCalculationResponse model."""
        from mcp_server.models import ShippingCalculationResponse
        from mcp_server.models.shipping import CarrierOption

        response = ShippingCalculationResponse(
            origin="NY",
            destination="LA",
            weight_lbs=10.0,
            base_cost=25.0,
            final_cost=30.0,
            estimated_days=3,
            carriers=[
                CarrierOption(carrier="FedEx", cost=30.0, estimated_days=3, service_level="Ground")
            ],
        )
        assert response.final_cost == 30.0
        assert response.base_cost == 25.0
        assert response.estimated_days == 3

    def test_tracking_response(self):
        """Test TrackingResponse model."""
        from mcp_server.models import TrackingResponse

        response = TrackingResponse(
            tracking_number="TRK-001",
            status="in_transit",
            current_location="Chicago",
            carrier="FedEx",
        )
        assert response.status == "in_transit"
        assert response.current_location == "Chicago"

    def test_delivery_estimate_response(self):
        """Test DeliveryEstimateResponse model."""
        from mcp_server.models import DeliveryEstimateResponse

        response = DeliveryEstimateResponse(
            destination="LA",
            shipping_method="express",
            estimated_days=2,
            estimated_delivery_date=date.today(),
        )
        assert response.destination == "LA"
        assert response.shipping_method == "express"


class TestCustomerModels:
    """Tests for customer models."""

    def test_customer_history_response(self):
        """Test CustomerHistoryResponse model."""
        from mcp_server.models import CustomerHistoryResponse

        response = CustomerHistoryResponse(
            user_id="user1",
            total_orders=5,
            total_spent=1000.0,
            average_order_value=200.0,
        )
        assert response.total_orders == 5
        assert response.total_spent == 1000.0
        assert response.average_order_value == 200.0

    def test_customer_preferences_response(self):
        """Test CustomerPreferencesResponse model."""
        from mcp_server.models import CustomerPreferencesResponse

        response = CustomerPreferencesResponse(
            user_id="user1",
            preferred_shipping="express",
            email_notifications=True,
            preferred_payment="credit_card",
        )
        assert response.preferred_shipping == "express"
        assert response.email_notifications is True
        assert response.preferred_payment == "credit_card"
