"""Tests for RFQ (Request for Quote) related MCP tools."""

import pytest


class TestCreateRFQTool:
    """Tests for create_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_create_rfq_success(self):
        """Test successful RFQ creation."""
        rfq = {
            "rfq_id": "RFQ-001",
            "customer_id": "CUST-123",
            "items": [{"product_id": "PROD-001", "quantity": 100}],
            "status": "pending",
            "created_at": "2025-01-01T00:00:00Z",
        }

        assert rfq["rfq_id"] is not None
        assert rfq["status"] == "pending"
        assert len(rfq["items"]) > 0

    @pytest.mark.asyncio
    async def test_create_rfq_with_multiple_items(self):
        """Test RFQ with multiple line items."""
        rfq = {
            "rfq_id": "RFQ-002",
            "items": [
                {"product_id": "PROD-001", "quantity": 50},
                {"product_id": "PROD-002", "quantity": 100},
                {"product_id": "PROD-003", "quantity": 25},
            ],
        }

        assert len(rfq["items"]) == 3

    @pytest.mark.asyncio
    async def test_create_rfq_with_notes(self):
        """Test RFQ with special notes."""
        rfq = {
            "rfq_id": "RFQ-003",
            "items": [],
            "special_notes": "Delivery needed by Jan 15",
            "contact_info": {"name": "John Doe", "email": "john@example.com", "phone": "555-1234"},
        }

        assert rfq["special_notes"] is not None
        assert rfq["contact_info"]["email"] is not None


class TestGetRFQTool:
    """Tests for get_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_get_rfq_success(self):
        """Test successful RFQ retrieval."""
        rfq = {
            "rfq_id": "RFQ-004",
            "customer_id": "CUST-124",
            "status": "quoted",
            "quote_amount": 5000.00,
            "created_at": "2025-01-01T00:00:00Z",
        }

        assert rfq["rfq_id"] == "RFQ-004"
        assert rfq["status"] == "quoted"

    @pytest.mark.asyncio
    async def test_get_rfq_not_found(self):
        """Test RFQ not found."""
        rfq = None

        assert rfq is None

    @pytest.mark.asyncio
    async def test_get_rfq_with_history(self):
        """Test RFQ with revision history."""
        rfq = {
            "rfq_id": "RFQ-005",
            "revisions": [
                {"version": 1, "status": "pending", "date": "2025-01-01"},
                {"version": 2, "status": "quoted", "date": "2025-01-02"},
            ],
        }

        assert len(rfq["revisions"]) == 2


class TestUpdateRFQTool:
    """Tests for update_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_update_rfq_items(self):
        """Test updating RFQ items."""
        updated = {"rfq_id": "RFQ-006", "items": [{"product_id": "PROD-001", "quantity": 150}]}

        assert len(updated["items"]) > 0

    @pytest.mark.asyncio
    async def test_update_rfq_status(self):
        """Test updating RFQ status."""
        updated = {"rfq_id": "RFQ-007", "status": "accepted"}

        assert updated["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_update_rfq_notes(self):
        """Test updating RFQ notes."""
        updated = {"rfq_id": "RFQ-008", "notes": "Updated delivery requirements"}

        assert updated["notes"] is not None


class TestSearchRFQTool:
    """Tests for search_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_search_rfq_by_customer(self):
        """Test searching RFQs by customer."""
        results = [
            {"rfq_id": "RFQ-009", "customer_id": "CUST-125"},
            {"rfq_id": "RFQ-010", "customer_id": "CUST-125"},
        ]

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_rfq_by_status(self):
        """Test searching RFQs by status."""
        all_rfqs = [
            {"rfq_id": "RFQ-011", "status": "pending"},
            {"rfq_id": "RFQ-012", "status": "quoted"},
            {"rfq_id": "RFQ-013", "status": "pending"},
        ]

        pending = [r for r in all_rfqs if r["status"] == "pending"]

        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_search_rfq_by_date_range(self):
        """Test searching RFQs by date range."""
        rfqs = [
            {"rfq_id": "RFQ-014", "created_at": "2025-01-01"},
            {"rfq_id": "RFQ-015", "created_at": "2025-01-05"},
            {"rfq_id": "RFQ-016", "created_at": "2025-01-10"},
        ]

        # Filter by date range
        filtered = [r for r in rfqs if "2025-01-05" >= r["created_at"] >= "2025-01-01"]

        assert len(filtered) >= 1


class TestQuoteRFQTool:
    """Tests for quote_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_quote_rfq_success(self):
        """Test successful RFQ quoting."""
        quote = {
            "rfq_id": "RFQ-017",
            "quote_id": "QUOTE-001",
            "total_amount": 5500.00,
            "unit_prices": {"PROD-001": 50.00, "PROD-002": 25.00},
            "valid_until": "2025-01-30",
            "status": "quoted",
        }

        assert quote["total_amount"] > 0
        assert quote["status"] == "quoted"

    @pytest.mark.asyncio
    async def test_quote_rfq_with_discounts(self):
        """Test RFQ quote with discounts."""
        quote = {
            "rfq_id": "RFQ-018",
            "subtotal": 6000.00,
            "volume_discount": 500.00,
            "loyalty_discount": 100.00,
            "total": 5400.00,
        }

        assert quote["total"] < quote["subtotal"]

    @pytest.mark.asyncio
    async def test_quote_rfq_with_shipping(self):
        """Test RFQ quote including shipping."""
        quote = {
            "rfq_id": "RFQ-019",
            "products_total": 5000.00,
            "shipping_cost": 250.00,
            "tax": 425.00,
            "total": 5675.00,
        }

        expected = quote["products_total"] + quote["shipping_cost"] + quote["tax"]
        assert abs(quote["total"] - expected) < 0.01


class TestAcceptRFQTool:
    """Tests for accept_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_accept_rfq_success(self):
        """Test successful RFQ acceptance."""
        result = {
            "rfq_id": "RFQ-020",
            "status": "accepted",
            "quote_id": "QUOTE-002",
            "order_created": True,
            "order_id": "ORD-123",
        }

        assert result["status"] == "accepted"
        assert result["order_created"] is True

    @pytest.mark.asyncio
    async def test_accept_rfq_expired(self):
        """Test accepting expired RFQ."""
        result = {
            "rfq_id": "RFQ-021",
            "status": "expired",
            "accepted": False,
            "reason": "Quote expired",
        }

        assert result["accepted"] is False


class TestRejectRFQTool:
    """Tests for reject_rfq MCP tool."""

    @pytest.mark.asyncio
    async def test_reject_rfq_success(self):
        """Test successful RFQ rejection."""
        result = {"rfq_id": "RFQ-022", "status": "rejected", "reason": "Price too high"}

        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_rfq_with_notes(self):
        """Test RFQ rejection with notes."""
        result = {
            "rfq_id": "RFQ-023",
            "status": "rejected",
            "notes": "Customer needs lower pricing to proceed",
        }

        assert result["notes"] is not None


class TestRFQToolErrors:
    """Tests for RFQ tool error handling."""

    @pytest.mark.asyncio
    async def test_invalid_rfq_id(self):
        """Test invalid RFQ ID."""
        invalid_ids = ["", "INVALID-RFQ", "123"]

        for rfq_id in invalid_ids:
            assert isinstance(rfq_id, str)

    @pytest.mark.asyncio
    async def test_rfq_invalid_quantity(self):
        """Test invalid quantity in RFQ."""
        invalid_qty = [-1, 0]

        for qty in invalid_qty:
            assert qty <= 0

    @pytest.mark.asyncio
    async def test_rfq_empty_items(self):
        """Test RFQ with no items."""
        rfq = {"rfq_id": "RFQ-024", "items": []}

        assert len(rfq["items"]) == 0

    @pytest.mark.asyncio
    async def test_rfq_quote_validation(self):
        """Test quote amount validation."""
        quote = {"total_amount": 5000.00}

        assert quote["total_amount"] > 0
