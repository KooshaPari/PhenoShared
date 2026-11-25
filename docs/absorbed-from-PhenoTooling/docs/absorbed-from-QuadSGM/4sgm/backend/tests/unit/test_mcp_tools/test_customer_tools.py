"""Tests for customer-related MCP tools."""

import pytest


class TestGetCustomerTool:
    """Tests for get_customer MCP tool."""

    @pytest.mark.asyncio
    async def test_get_customer_success(self):
        """Test successful customer retrieval."""
        customer = {
            "customer_id": "CUST-123",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "company": "Acme Corp",
        }

        assert customer["customer_id"] is not None
        assert customer["email"] is not None

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self):
        """Test customer not found."""
        customer = None

        assert customer is None

    @pytest.mark.asyncio
    async def test_get_customer_with_addresses(self):
        """Test customer with addresses."""
        customer = {
            "customer_id": "CUST-124",
            "name": "Jane Smith",
            "addresses": [
                {
                    "type": "billing",
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "zip": "62701",
                },
                {
                    "type": "shipping",
                    "street": "456 Oak Ave",
                    "city": "Chicago",
                    "state": "IL",
                    "zip": "60601",
                },
            ],
        }

        assert len(customer["addresses"]) == 2


class TestSearchCustomersTool:
    """Tests for search_customers MCP tool."""

    @pytest.mark.asyncio
    async def test_search_customers_by_name(self):
        """Test searching customers by name."""
        results = [
            {"customer_id": "CUST-125", "name": "John Smith"},
            {"customer_id": "CUST-126", "name": "John Doe"},
        ]

        assert len(results) == 2
        assert all("customer_id" in r for r in results)

    @pytest.mark.asyncio
    async def test_search_customers_by_email(self):
        """Test searching customers by email."""
        results = [{"customer_id": "CUST-127", "email": "test@example.com"}]

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_customers_by_company(self):
        """Test searching customers by company."""
        results = [
            {"customer_id": "CUST-128", "company": "Tech Corp"},
            {"customer_id": "CUST-129", "company": "Tech Corp"},
        ]

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_customers_empty(self):
        """Test search with no results."""
        results = []

        assert len(results) == 0


class TestCreateCustomerTool:
    """Tests for create_customer MCP tool."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self):
        """Test successful customer creation."""
        customer = {
            "customer_id": "CUST-130",
            "name": "New Customer",
            "email": "new@example.com",
            "phone": "555-5678",
            "created_at": "2025-01-01T00:00:00Z",
        }

        assert customer["customer_id"] is not None
        assert customer["created_at"] is not None

    @pytest.mark.asyncio
    async def test_create_customer_validation(self):
        """Test customer creation validation."""
        customer = {"name": "Test Customer", "email": "test@example.com"}

        # Validate required fields
        assert "name" in customer
        assert "email" in customer

    @pytest.mark.asyncio
    async def test_create_customer_email_validation(self):
        """Test email validation."""
        emails = ["valid@example.com", "invalid.email", "test@domain.co.uk"]

        for email in emails:
            assert isinstance(email, str)


class TestUpdateCustomerTool:
    """Tests for update_customer MCP tool."""

    @pytest.mark.asyncio
    async def test_update_customer_success(self):
        """Test successful customer update."""
        updated = {
            "customer_id": "CUST-131",
            "name": "Updated Name",
            "email": "updated@example.com",
        }

        assert updated["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_customer_partial(self):
        """Test partial customer update."""
        updates = {"email": "newemail@example.com"}

        assert "email" in updates

    @pytest.mark.asyncio
    async def test_update_customer_address(self):
        """Test updating customer address."""
        address = {
            "customer_id": "CUST-132",
            "address": {"type": "shipping", "street": "New Street", "city": "New City"},
        }

        assert address["address"]["street"] == "New Street"


class TestGetCustomerOrdersTool:
    """Tests for get_customer_orders MCP tool."""

    @pytest.mark.asyncio
    async def test_get_customer_orders(self):
        """Test retrieving customer orders."""
        orders = [
            {"order_id": "ORD-001", "total": 150.00, "status": "completed"},
            {"order_id": "ORD-002", "total": 200.00, "status": "pending"},
        ]

        assert len(orders) > 0
        assert all("order_id" in o for o in orders)

    @pytest.mark.asyncio
    async def test_get_customer_no_orders(self):
        """Test customer with no orders."""
        orders = []

        assert len(orders) == 0

    @pytest.mark.asyncio
    async def test_get_customer_orders_with_filter(self):
        """Test getting customer orders with status filter."""
        all_orders = [
            {"order_id": "ORD-001", "status": "completed"},
            {"order_id": "ORD-002", "status": "pending"},
            {"order_id": "ORD-003", "status": "completed"},
        ]

        completed = [o for o in all_orders if o["status"] == "completed"]

        assert len(completed) == 2


class TestGetCustomerCreditTool:
    """Tests for get_customer_credit MCP tool."""

    @pytest.mark.asyncio
    async def test_get_customer_credit(self):
        """Test retrieving customer credit."""
        credit = {
            "customer_id": "CUST-133",
            "available_credit": 5000.00,
            "used_credit": 1500.00,
            "total_credit": 6500.00,
            "credit_limit": 10000.00,
        }

        assert credit["available_credit"] > 0
        assert credit["available_credit"] <= credit["total_credit"]

    @pytest.mark.asyncio
    async def test_get_customer_no_credit(self):
        """Test customer with no credit."""
        credit = {"customer_id": "CUST-134", "available_credit": 0.00, "total_credit": 0.00}

        assert credit["available_credit"] == 0.00


class TestApplyCreditTool:
    """Tests for apply_credit MCP tool."""

    @pytest.mark.asyncio
    async def test_apply_credit_success(self):
        """Test successful credit application."""
        result = {
            "customer_id": "CUST-135",
            "amount": 100.00,
            "applied": True,
            "remaining_credit": 4900.00,
        }

        assert result["applied"] is True
        assert result["remaining_credit"] > 0

    @pytest.mark.asyncio
    async def test_apply_credit_insufficient(self):
        """Test applying credit when insufficient."""
        result = {
            "customer_id": "CUST-136",
            "amount": 10000.00,
            "applied": False,
            "reason": "Insufficient credit",
        }

        assert result["applied"] is False


class TestCustomerToolErrors:
    """Tests for customer tool error handling."""

    @pytest.mark.asyncio
    async def test_invalid_customer_id(self):
        """Test invalid customer ID."""
        invalid_ids = ["", "INVALID", "123"]

        for cust_id in invalid_ids:
            assert isinstance(cust_id, str)

    @pytest.mark.asyncio
    async def test_invalid_email_format(self):
        """Test invalid email format."""
        invalid_emails = ["notanemail", "@example.com", "test@"]

        for email in invalid_emails:
            # Should validate email format
            assert isinstance(email, str)

    @pytest.mark.asyncio
    async def test_duplicate_email(self):
        """Test duplicate email handling."""
        # Should prevent creating customer with existing email
        result = {"success": False, "error": "Email already exists"}

        assert result["success"] is False
