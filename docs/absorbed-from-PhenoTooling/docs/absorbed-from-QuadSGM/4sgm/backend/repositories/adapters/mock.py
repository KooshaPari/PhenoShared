"""Mock adapter implementations for testing.

Provides in-memory implementations of all repository protocols without
external dependencies. Useful for unit testing and development without
a running database.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from ..exceptions import (
    CartNotFoundError,
    InsufficientInventoryError,
    ProductNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Shared registries for cross-repository validation
_product_registry: dict[str, dict] = {}
_inventory_registry: dict[str, dict] = {}


class MockProductRepository:
    """In-memory implementation of ProductRepository protocol."""

    def __init__(self):
        """Initialize with empty product store."""
        self.products = {}
        # Clear shared registry on new instance for test isolation
        _product_registry.clear()

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve product by ID."""
        return self.products.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all products with pagination."""
        items = list(self.products.values())
        return items[skip : skip + limit]

    async def list(self, **filters) -> list[dict]:
        """Filter products by criteria."""
        results = []
        for product in self.products.values():
            match = True
            for key, value in filters.items():
                if product.get(key) != value:
                    match = False
                    break
            if match:
                results.append(product)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new product."""
        product = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.products[product["id"]] = product
        # Register in shared registry for cross-repo validation
        _product_registry[product["id"]] = product
        return product

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update existing product."""
        if id not in self.products:
            return None
        self.products[id].update({"updated_at": datetime.now(timezone.utc).isoformat(), **data})
        return self.products[id]

    async def delete(self, id: str) -> bool:
        """Delete product by ID."""
        if id in self.products:
            del self.products[id]
            _product_registry.pop(id, None)
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if product exists."""
        return id in self.products

    async def get_by_sku(self, sku: str) -> Optional[dict]:
        """Get product by SKU."""
        for product in self.products.values():
            if product.get("sku") == sku:
                return product
        return None

    async def list_by_category(self, category: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List products in category."""
        items = [p for p in self.products.values() if p.get("category") == category]
        return items[skip : skip + limit]

    async def search(self, query: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """Full-text search products."""
        query_lower = query.lower()
        results = [
            p
            for p in self.products.values()
            if query_lower in p.get("name", "").lower()
            or query_lower in p.get("description", "").lower()
        ]
        return results[skip : skip + limit]

    async def update_inventory(self, product_id: str, quantity_change: int) -> Optional[dict]:
        """Update product inventory."""
        if product_id not in self.products:
            return None

        product = self.products[product_id]
        current = product.get("quantity_on_hand", 0)
        product["quantity_on_hand"] = max(0, current + quantity_change)
        product["updated_at"] = datetime.now(timezone.utc).isoformat()
        return product

    async def get_low_stock(self, threshold: int = 10) -> list[dict]:
        """Get products below stock threshold."""
        return [p for p in self.products.values() if p.get("quantity_on_hand", 0) < threshold]


class MockCartRepository:
    """In-memory implementation of CartRepository protocol."""

    def __init__(self):
        """Initialize with empty cart and item stores."""
        self.carts = {}
        self.items = {}

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve cart by ID."""
        if id not in self.carts:
            return None

        cart = self.carts[id].copy()
        items_list = [self.items[iid] for iid in cart.get("item_ids", []) if iid in self.items]
        cart["cart_items"] = items_list
        cart["items"] = items_list  # Alias for compatibility

        # Calculate total from items
        total = sum(item.get("quantity", 0) * item.get("price", 0) for item in items_list)
        cart["total"] = total

        return cart

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all carts with pagination."""
        carts_list = list(self.carts.values())[skip : skip + limit]
        return [await self.get(c["id"]) or c for c in carts_list]

    async def list(self, **filters) -> list[dict]:
        """Filter carts by criteria."""
        results = []
        for cart_id in self.carts:
            cart = await self.get(cart_id)
            if cart:
                match = all(cart.get(k) == v for k, v in filters.items())
                if match:
                    results.append(cart)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new cart."""
        cart = {
            "id": str(uuid.uuid4()),
            "item_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.carts[cart["id"]] = cart
        return await self.get(cart["id"]) or cart

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update cart."""
        if id not in self.carts:
            return None
        self.carts[id].update({"updated_at": datetime.now(timezone.utc).isoformat(), **data})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete cart by ID."""
        if id in self.carts:
            # Clean up items
            for item_id in self.carts[id].get("item_ids", []):
                self.items.pop(item_id, None)
            del self.carts[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if cart exists."""
        return id in self.carts

    async def get_by_customer(self, customer_id: str) -> Optional[dict]:
        """Get active cart for customer."""
        for cart_id, cart in self.carts.items():
            if cart.get("customer_id") == customer_id and cart.get("status") == "active":
                return await self.get(cart_id)
        return None

    async def add_item(self, cart_id: str, product_id: str, quantity: int, price: float) -> dict:
        """Add item to cart."""
        if cart_id not in self.carts:
            raise CartNotFoundError(cart_id)

        # Validate product exists
        if product_id not in _product_registry:
            raise ProductNotFoundError(product_id)

        # Validate quantity
        if quantity <= 0:
            raise ValidationError(f"Quantity must be positive, got {quantity}", field="quantity")

        # Validate price
        if price < 0:
            raise ValidationError(f"Price cannot be negative, got {price}", field="price")

        item_id = str(uuid.uuid4())
        self.items[item_id] = {
            "id": item_id,
            "cart_id": cart_id,
            "product_id": product_id,
            "quantity": quantity,
            "price": price,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.carts[cart_id]["item_ids"].append(item_id)
        await self.update(cart_id, {})
        return await self.get(cart_id) or {"id": cart_id}

    async def remove_item(self, cart_id: str, item_id: str) -> dict:
        """Remove item from cart (by item_id or product_id)."""
        if cart_id not in self.carts:
            raise ValueError(f"Cart {cart_id} not found")

        # Check if item_id is actually a product_id and find the item_id
        if item_id not in self.items:
            # Try to find by product_id
            for iid, item in self.items.items():
                if item.get("product_id") == item_id and item.get("cart_id") == cart_id:
                    item_id = iid
                    break

        if item_id in self.items and self.items[item_id].get("cart_id") == cart_id:
            del self.items[item_id]
            if item_id in self.carts[cart_id]["item_ids"]:
                self.carts[cart_id]["item_ids"].remove(item_id)
            await self.update(cart_id, {})

        return await self.get(cart_id) or {"id": cart_id}

    async def update_item(self, cart_id: str, item_id: str, quantity: int) -> dict:
        """Update item quantity in cart."""
        if item_id in self.items:
            self.items[item_id]["quantity"] = quantity
            await self.update(cart_id, {})

        return await self.get(cart_id) or {"id": cart_id}

    async def clear(self, cart_id: str) -> dict:
        """Clear all items from cart."""
        if cart_id not in self.carts:
            raise ValueError(f"Cart {cart_id} not found")

        for item_id in self.carts[cart_id].get("item_ids", []):
            self.items.pop(item_id, None)

        self.carts[cart_id]["item_ids"] = []
        await self.update(cart_id, {"item_count": 0})
        return await self.get(cart_id) or {"id": cart_id}

    async def calculate_total(self, cart_id: str) -> dict:
        """Calculate cart totals."""
        cart = await self.get(cart_id)
        if not cart:
            return {}

        items = cart.get("cart_items", [])
        subtotal = sum(item.get("quantity", 0) * item.get("price", 0) for item in items)

        tax = subtotal * 0.08
        shipping = 10.0 if subtotal > 0 else 0

        return {
            **cart,
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": subtotal + tax + shipping,
        }


class MockOrderRepository:
    """In-memory implementation of OrderRepository protocol."""

    def __init__(self):
        """Initialize with empty order and item stores."""
        self.orders = {}
        self.items = {}
        self.shipments = {}

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve order by ID."""
        if id not in self.orders:
            return None

        order = self.orders[id].copy()
        order["order_items"] = [
            self.items[iid] for iid in order.get("item_ids", []) if iid in self.items
        ]
        order["shipments"] = [
            self.shipments[sid] for sid in order.get("shipment_ids", []) if sid in self.shipments
        ]
        return order

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all orders with pagination."""
        orders_list = list(self.orders.values())[skip : skip + limit]
        return [await self.get(o["id"]) or o for o in orders_list]

    async def list(self, **filters) -> list[dict]:
        """Filter orders by criteria."""
        results = []
        for order_id in self.orders:
            order = await self.get(order_id)
            if order:
                match = all(order.get(k) == v for k, v in filters.items())
                if match:
                    results.append(order)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new order."""
        order = {
            "id": str(uuid.uuid4()),
            "status": "pending",
            "item_ids": [],
            "shipment_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.orders[order["id"]] = order
        return await self.get(order["id"]) or order

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update order."""
        if id not in self.orders:
            return None
        self.orders[id].update({"updated_at": datetime.now(timezone.utc).isoformat(), **data})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete order by ID."""
        if id in self.orders:
            for item_id in self.orders[id].get("item_ids", []):
                self.items.pop(item_id, None)
            for shipment_id in self.orders[id].get("shipment_ids", []):
                self.shipments.pop(shipment_id, None)
            del self.orders[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if order exists."""
        return id in self.orders

    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders for customer."""
        orders = [
            await self.get(oid) or self.orders[oid]
            for oid in self.orders
            if self.orders[oid].get("customer_id") == customer_id
        ]
        return sorted(orders, key=lambda o: o.get("created_at", ""), reverse=True)[
            skip : skip + limit
        ]

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders by status."""
        orders = [
            await self.get(oid) or self.orders[oid]
            for oid in self.orders
            if self.orders[oid].get("status") == status
        ]
        return orders[skip : skip + limit]

    async def get_line_items(self, order_id: str) -> list[dict]:
        """Get line items for order."""
        if order_id not in self.orders:
            return []
        return [
            self.items[iid]
            for iid in self.orders[order_id].get("item_ids", [])
            if iid in self.items
        ]

    async def update_status(self, order_id: str, status: str, notes: str = "") -> Optional[dict]:
        """Update order status."""
        if order_id not in self.orders:
            return None
        return await self.update(order_id, {"status": status, "status_notes": notes})

    async def add_shipment(self, order_id: str, tracking_number: str, carrier: str) -> dict:
        """Add shipment tracking to order."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")

        shipment_id = str(uuid.uuid4())
        self.shipments[shipment_id] = {
            "id": shipment_id,
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "status": "in_transit",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.orders[order_id]["shipment_ids"].append(shipment_id)
        await self.update_status(order_id, "shipped")
        return await self.get(order_id) or {"id": order_id}

    async def get_pending_fulfillment(self) -> list[dict]:
        """Get orders awaiting fulfillment."""
        pending = [
            await self.get(oid) or self.orders[oid]
            for oid in self.orders
            if self.orders[oid].get("status") == "pending"
        ]
        return sorted(pending, key=lambda o: o.get("created_at", ""))


class MockCustomerRepository:
    """In-memory implementation of CustomerRepository protocol."""

    def __init__(self):
        """Initialize with empty customer and address stores."""
        self.customers = {}
        self.addresses = {}

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve customer by ID."""
        if id not in self.customers:
            return None

        customer = self.customers[id].copy()
        customer["customer_addresses"] = [
            self.addresses[aid] for aid in customer.get("address_ids", []) if aid in self.addresses
        ]
        return customer

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all customers with pagination."""
        customers_list = list(self.customers.values())[skip : skip + limit]
        return [await self.get(c["id"]) or c for c in customers_list]

    async def list(self, **filters) -> list[dict]:
        """Filter customers by criteria."""
        results = []
        for customer_id in self.customers:
            customer = await self.get(customer_id)
            if customer:
                match = all(customer.get(k) == v for k, v in filters.items())
                if match:
                    results.append(customer)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new customer."""
        customer = {
            "id": str(uuid.uuid4()),
            "status": "active",
            "address_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.customers[customer["id"]] = customer
        return await self.get(customer["id"]) or customer

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update customer."""
        if id not in self.customers:
            return None
        self.customers[id].update({"updated_at": datetime.now(timezone.utc).isoformat(), **data})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete customer by ID."""
        if id in self.customers:
            for address_id in self.customers[id].get("address_ids", []):
                self.addresses.pop(address_id, None)
            del self.customers[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if customer exists."""
        return id in self.customers

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get customer by email."""
        for customer_id, customer in self.customers.items():
            if customer.get("email") == email:
                return await self.get(customer_id)
        return None

    async def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List customers by status."""
        customers = [
            await self.get(cid) or self.customers[cid]
            for cid in self.customers
            if self.customers[cid].get("status") == status
        ]
        return customers[skip : skip + limit]

    async def update_profile(self, customer_id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update customer profile."""
        return await self.update(customer_id, data)

    async def add_address(self, customer_id: str, address_data: dict[str, Any]) -> dict:
        """Add address to customer."""
        if customer_id not in self.customers:
            raise ValueError(f"Customer {customer_id} not found")

        address_id = str(uuid.uuid4())
        address = {
            "id": address_id,
            "customer_id": customer_id,
            "is_default": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **address_data,
        }
        self.addresses[address_id] = address
        self.customers[customer_id]["address_ids"].append(address_id)
        return address

    async def get_addresses(self, customer_id: str) -> list[dict]:
        """Get all addresses for customer."""
        if customer_id not in self.customers:
            return []

        addresses = [
            self.addresses[aid]
            for aid in self.customers[customer_id].get("address_ids", [])
            if aid in self.addresses
        ]
        return sorted(addresses, key=lambda a: a.get("is_default", False), reverse=True)

    async def set_default_address(self, customer_id: str, address_id: str) -> dict:
        """Set default address for customer."""
        if customer_id not in self.customers:
            raise ValueError(f"Customer {customer_id} not found")

        # Clear existing defaults
        for aid in self.customers[customer_id].get("address_ids", []):
            if aid in self.addresses:
                self.addresses[aid]["is_default"] = False

        # Set new default
        if address_id in self.addresses:
            self.addresses[address_id]["is_default"] = True

        return await self.get(customer_id) or {"id": customer_id}


class MockShippingRepository:
    """In-memory implementation of ShippingRepository protocol."""

    def __init__(self):
        """Initialize with empty shipping stores."""
        self.methods = {}
        self.rates = {}
        self.tracking = {}

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve shipping method by ID."""
        return self.methods.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all shipping methods."""
        items = list(self.methods.values())
        return items[skip : skip + limit]

    async def list(self, **filters) -> list[dict]:
        """Filter shipping methods by criteria."""
        results = []
        for method in self.methods.values():
            match = all(method.get(k) == v for k, v in filters.items())
            if match:
                results.append(method)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new shipping method."""
        method = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.methods[method["id"]] = method
        return method

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update shipping method."""
        if id not in self.methods:
            return None
        self.methods[id].update(data)
        return self.methods[id]

    async def delete(self, id: str) -> bool:
        """Delete shipping method by ID."""
        if id in self.methods:
            del self.methods[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if shipping method exists."""
        return id in self.methods

    async def get_rates(self, origin: str, destination: str, weight: float) -> list[dict]:
        """Get shipping rates for route and weight."""
        return [
            r
            for r in self.rates.values()
            if r.get("origin") == origin
            and r.get("destination") == destination
            and r.get("max_weight", float("inf")) >= weight
        ]

    async def get_by_carrier(self, carrier: str) -> list[dict]:
        """Get shipping methods for carrier."""
        return [m for m in self.methods.values() if m.get("carrier") == carrier]

    async def track(self, tracking_number: str, carrier: str) -> Optional[dict]:
        """Get shipment tracking status."""
        for tracking in sorted(
            self.tracking.values(), key=lambda t: t.get("updated_at", ""), reverse=True
        ):
            if (
                tracking.get("tracking_number") == tracking_number
                and tracking.get("carrier") == carrier
            ):
                return tracking
        return None

    async def create_shipment(self, order_id: str, carrier: str, service: str) -> dict:
        """Create shipment and generate label."""
        shipment = {
            "id": str(uuid.uuid4()),
            "order_id": order_id,
            "carrier": carrier,
            "service": service,
            "status": "label_generated",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tracking[shipment["id"]] = shipment
        return shipment

    async def estimate_delivery(
        self,
        carrier: str = None,
        destination: str = None,
        service: str = None,
        weight_lbs: float = None,
        shipping_method: str = None,
        **kwargs,
    ) -> dict:
        """Estimate delivery date."""
        # Use shipping_method if provided (can be carrier name)
        method = shipping_method or service or carrier or "ground"
        method_lower = method.lower()

        # Mock estimate: days based on method/carrier type
        days_map = {
            "ground": 3,
            "express": 2,
            "overnight": 1,
            "ups": 3,
            "fedex": 2,
            "usps": 4,
        }
        days = days_map.get(method_lower, 2)
        estimated_date = datetime.now(timezone.utc) + timedelta(days=days)

        return {
            "carrier": carrier or shipping_method or "UPS",
            "service": service or "Ground",
            "destination": destination,
            "estimated_days": days,
            "estimated_delivery": estimated_date.isoformat(),
            "estimated_delivery_date": estimated_date.isoformat(),
            "estimated_date": estimated_date,
        }

    async def calculate_shipping(
        self,
        origin: str,
        destination: str,
        weight_lbs: float,
        dimensions: dict = None,
        dimensions_inches: tuple = None,
    ) -> dict:
        """Calculate shipping cost and options."""
        # Base rate calculation based on weight and distance simulation
        base_cost = 5.0 + (weight_lbs * 0.5)

        # Handle dimensions (can be dict or tuple)
        if dimensions_inches is not None:
            if isinstance(dimensions_inches, tuple):
                # Tuple format: (length, width, height)
                volume = dimensions_inches[0] * dimensions_inches[1] * dimensions_inches[2]
            else:
                # Dict format
                volume = (
                    dimensions_inches.get("length", 1)
                    * dimensions_inches.get("width", 1)
                    * dimensions_inches.get("height", 1)
                )
            dim_factor = 1.0 + (volume / 1000)
            base_cost *= dim_factor
        elif dimensions is not None:
            volume = (
                dimensions.get("length", 1)
                * dimensions.get("width", 1)
                * dimensions.get("height", 1)
            )
            dim_factor = 1.0 + (volume / 1000)
            base_cost *= dim_factor

        # Simulate distance factor based on origin/destination
        same_state = origin.split(",")[-1].strip() == destination.split(",")[-1].strip()
        distance_multiplier = 1.0 if same_state else 2.0

        base_cost = round(base_cost * distance_multiplier, 2)
        final_cost = base_cost  # Could add taxes/fees here

        carriers = [
            {
                "carrier": "UPS",
                "service": "Ground",
                "cost": base_cost,
                "estimated_days": 5 if not same_state else 3,
                "delivery_date": (
                    datetime.now(timezone.utc) + timedelta(days=5 if not same_state else 3)
                ).isoformat(),
            },
            {
                "carrier": "FedEx",
                "service": "Express",
                "cost": round(base_cost * 1.5, 2),
                "estimated_days": 2,
                "delivery_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            },
            {
                "carrier": "FedEx",
                "service": "Overnight",
                "cost": round(base_cost * 3.0, 2),
                "estimated_days": 1,
                "delivery_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            },
        ]

        return {
            "origin": origin,
            "destination": destination,
            "weight_lbs": weight_lbs,
            "base_cost": base_cost,
            "final_cost": final_cost,
            "estimated_days": 5 if not same_state else 3,  # Default ground shipping
            "carriers": carriers,
            "options": carriers,  # Alias for compatibility
        }

    async def get_carriers(self) -> list[dict]:
        """Get available carriers."""
        return [
            {"id": "ups", "name": "UPS", "services": ["Ground", "2-Day", "Next Day"]},
            {"id": "fedex", "name": "FedEx", "services": ["Ground", "Express", "Overnight"]},
            {"id": "usps", "name": "USPS", "services": ["Priority", "Express"]},
        ]

    async def get_shipping_methods(self, destination: str = None) -> list[dict]:
        """Get available shipping methods."""
        return [
            {
                "id": "ground",
                "name": "Ground Shipping",
                "estimated_days": "3-5",
                "description": "Standard ground delivery within 3-5 business days",
                "avg_delivery_days": 4,
                "cost_per_lb": 0.50,
            },
            {
                "id": "express",
                "name": "Express Shipping",
                "estimated_days": "1-2",
                "description": "Expedited delivery within 1-2 business days",
                "avg_delivery_days": 2,
                "cost_per_lb": 1.50,
            },
            {
                "id": "overnight",
                "name": "Overnight Shipping",
                "estimated_days": "1",
                "description": "Next day delivery for urgent orders",
                "avg_delivery_days": 1,
                "cost_per_lb": 3.00,
            },
        ]

    async def track_shipment(self, tracking_number: str) -> dict:
        """Track a shipment by tracking number."""
        # Simulate tracking info
        return {
            "tracking_number": tracking_number,
            "status": "in_transit",
            "carrier": "UPS",
            "current_location": "Distribution Center",
            "estimated_delivery": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "events": [
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "location": "Distribution Center",
                    "status": "In Transit",
                },
                {
                    "date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    "location": "Origin Facility",
                    "status": "Shipped",
                },
            ],
        }

    async def validate_address(self, address: dict) -> dict:
        """Validate shipping address."""
        # Simple validation - check required fields
        required = ["street", "city", "state", "zip"]
        missing = [f for f in required if not address.get(f)]

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "normalized_address": address if not missing else None,
        }


class MockRFQRepository:
    """In-memory implementation of RFQRepository protocol."""

    def __init__(self):
        """Initialize with empty RFQ stores."""
        self.rfqs = {}
        self.items = {}
        self.quotes = {}

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve RFQ by ID."""
        if id not in self.rfqs:
            return None

        rfq = self.rfqs[id].copy()
        items_list = [self.items[iid] for iid in rfq.get("item_ids", []) if iid in self.items]
        rfq["rfq_items"] = items_list
        rfq["items"] = items_list  # Alias for compatibility
        rfq["rfq_quotes"] = [
            self.quotes[qid] for qid in rfq.get("quote_ids", []) if qid in self.quotes
        ]
        # Add total_price alias if not present
        if "total" in rfq and "total_price" not in rfq:
            rfq["total_price"] = rfq["total"]
        return rfq

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all RFQs with pagination."""
        rfqs_list = list(self.rfqs.values())[skip : skip + limit]
        return [await self.get(r["id"]) or r for r in rfqs_list]

    async def list(self, **filters) -> list[dict]:
        """Filter RFQs by criteria."""
        results = []
        for rfq_id in self.rfqs:
            rfq = await self.get(rfq_id)
            if rfq:
                match = all(rfq.get(k) == v for k, v in filters.items())
                if match:
                    results.append(rfq)
        return results

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new RFQ."""
        rfq = {
            "id": str(uuid.uuid4()),
            "status": "open",
            "item_ids": [],
            "quote_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.rfqs[rfq["id"]] = rfq
        return await self.get(rfq["id"]) or rfq

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update RFQ."""
        if id not in self.rfqs:
            return None
        self.rfqs[id].update({"updated_at": datetime.now(timezone.utc).isoformat(), **data})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete RFQ by ID."""
        if id in self.rfqs:
            for item_id in self.rfqs[id].get("item_ids", []):
                self.items.pop(item_id, None)
            for quote_id in self.rfqs[id].get("quote_ids", []):
                self.quotes.pop(quote_id, None)
            del self.rfqs[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        """Check if RFQ exists."""
        return id in self.rfqs

    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs for customer."""
        rfqs = [
            await self.get(rid) or self.rfqs[rid]
            for rid in self.rfqs
            if self.rfqs[rid].get("customer_id") == customer_id
        ]
        return sorted(rfqs, key=lambda r: r.get("created_at", ""), reverse=True)[
            skip : skip + limit
        ]

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs by status."""
        rfqs = [
            await self.get(rid) or self.rfqs[rid]
            for rid in self.rfqs
            if self.rfqs[rid].get("status") == status
        ]
        return rfqs[skip : skip + limit]

    async def get_items(self, rfq_id: str) -> list[dict]:
        """Get line items for RFQ."""
        if rfq_id not in self.rfqs:
            return []
        return [
            self.items[iid] for iid in self.rfqs[rfq_id].get("item_ids", []) if iid in self.items
        ]

    async def add_quote(self, rfq_id: str, quote_data: dict[str, Any]) -> dict:
        """Add quote response to RFQ."""
        if rfq_id not in self.rfqs:
            raise ValueError(f"RFQ {rfq_id} not found")

        quote_id = str(uuid.uuid4())
        quote = {
            "id": quote_id,
            "rfq_id": rfq_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **quote_data,
        }
        self.quotes[quote_id] = quote
        self.rfqs[rfq_id]["quote_ids"].append(quote_id)
        await self.update(rfq_id, {"status": "quoted"})
        return await self.get(rfq_id) or {"id": rfq_id}

    async def get_quote(self, rfq_id: str) -> Optional[dict]:
        """Get active quote for RFQ."""
        if rfq_id not in self.rfqs:
            return None

        quote_ids = self.rfqs[rfq_id].get("quote_ids", [])
        for quote_id in quote_ids:
            if quote_id in self.quotes and self.quotes[quote_id].get("status") == "active":
                return self.quotes[quote_id]
        return None

    async def accept_quote(self, rfq_id: str) -> dict:
        """Accept quote and convert to order."""
        if rfq_id not in self.rfqs:
            raise ValueError(f"RFQ {rfq_id} not found")

        await self.update(rfq_id, {"status": "accepted"})
        return await self.get(rfq_id) or {"id": rfq_id}

    async def get_pending_quotes(self) -> list[dict]:
        """Get RFQs awaiting quote responses."""
        pending = [
            await self.get(rid) or self.rfqs[rid]
            for rid in self.rfqs
            if self.rfqs[rid].get("status") == "open"
        ]
        return sorted(pending, key=lambda r: r.get("created_at", ""))

    async def create_rfq(
        self, items: list[dict], customer_name: str, customer_email: str, **kwargs
    ) -> dict:
        """Create RFQ with items."""
        rfq_id = str(uuid.uuid4())

        # Create the RFQ
        rfq = {
            "id": rfq_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "status": "pending",
            "item_ids": [],
            "quote_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

        # Calculate totals and add items
        total = 0
        item_count = 0
        for item_data in items:
            item_id = str(uuid.uuid4())
            quantity = item_data.get("quantity", 1)
            unit_price = item_data.get("unit_price", 0)
            line_total = quantity * unit_price

            item = {
                "id": item_id,
                "rfq_id": rfq_id,
                "product_id": item_data.get("product_id"),
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.items[item_id] = item
            rfq["item_ids"].append(item_id)
            total += line_total
            item_count += quantity

        rfq["total"] = total
        rfq["total_price"] = total  # Alias
        rfq["item_count"] = item_count
        self.rfqs[rfq_id] = rfq

        return await self.get(rfq_id) or rfq

    async def update_rfq_status(self, rfq_id: str, status: str, notes: str = "") -> Optional[dict]:
        """Update RFQ status."""
        if rfq_id not in self.rfqs:
            return None
        return await self.update(rfq_id, {"status": status, "status_notes": notes})

    async def get_rfq_status(self, rfq_id: str) -> Optional[dict]:
        """Get RFQ status details."""
        rfq = await self.get(rfq_id)
        if not rfq:
            return None

        # Return simplified item structure matching input format
        simplified_items = []
        for item in rfq.get("items", []):
            simplified_items.append(
                {
                    "product_id": item.get("product_id"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                }
            )

        return {
            "rfq_id": rfq_id,
            "status": rfq.get("status", "unknown"),
            "created_at": rfq.get("created_at"),
            "updated_at": rfq.get("updated_at"),
            "items": simplified_items,
            "item_count": len(simplified_items),
            "total_price": rfq.get("total", 0),
        }

    async def accept_rfq(self, rfq_id: str, **kwargs) -> Optional[dict]:
        """Accept an RFQ and create order reference."""
        if rfq_id not in self.rfqs:
            return None

        order_id = str(uuid.uuid4())
        purchase_order_number = kwargs.get("purchase_order_number", f"PO-{order_id[:8]}")

        await self.update(
            rfq_id,
            {
                "status": "accepted",
                "order_id": order_id,
                "purchase_order_number": purchase_order_number,
                **kwargs,
            },
        )

        rfq = await self.get(rfq_id)
        return {
            "rfq_id": rfq_id,
            "order_id": order_id,
            "purchase_order_number": purchase_order_number,
            "status": "accepted",
            "total_price": rfq.get("total_price", rfq.get("total", 0)),
            "rfq": rfq,
        }

    async def reject_rfq(self, rfq_id: str, reason: str = "") -> Optional[dict]:
        """Reject an RFQ."""
        return await self.update_rfq_status(rfq_id, "rejected", reason)


class MockInventoryRepository:
    """In-memory implementation of InventoryRepository protocol."""

    def __init__(self):
        """Initialize with empty inventory store."""
        self.inventory = {}

    async def get_inventory(self, product_id: str) -> Optional[dict]:
        """Get inventory for product."""
        if product_id in self.inventory:
            return self.inventory[product_id]

        # Check shared product registry for quantity_on_hand
        product = _product_registry.get(product_id)
        if product:
            qty = product.get("quantity_on_hand", 0)
            return {"product_id": product_id, "in_stock": qty, "available": qty, "reserved": 0}

        return {"product_id": product_id, "in_stock": 0, "available": 0, "reserved": 0}

    async def update_inventory(self, product_id: str, available: int, reserved: int = 0) -> dict:
        """Update inventory levels."""
        inv = {
            "product_id": product_id,
            "in_stock": available + reserved,
            "available": available,
            "reserved": reserved,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.inventory[product_id] = inv
        return inv

    async def reserve(self, product_id: str, quantity: int) -> dict:
        """Reserve inventory."""
        inv = await self.get_inventory(product_id)
        if inv.get("available", 0) < quantity:
            raise InsufficientInventoryError(product_id, quantity, inv.get("available", 0))

        inv["available"] = inv.get("available", 0) - quantity
        inv["reserved"] = inv.get("reserved", 0) + quantity
        inv["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.inventory[product_id] = inv
        return inv

    async def release(self, product_id: str, quantity: int) -> dict:
        """Release reserved inventory."""
        inv = self.inventory.get(
            product_id, {"product_id": product_id, "available": 0, "reserved": 0}
        )
        inv["reserved"] = max(0, inv.get("reserved", 0) - quantity)
        inv["available"] = inv.get("available", 0) + quantity
        inv["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.inventory[product_id] = inv
        return inv


class MockPricingRepository:
    """In-memory implementation of PricingRepository protocol."""

    def __init__(self):
        """Initialize with pricing data."""
        self.pricing = {}
        self.coupons = {
            "SAVE10": {"code": "SAVE10", "discount_percent": 10, "valid": True},
            "SAVE5": {"code": "SAVE5", "discount_percent": 5, "valid": True},
            "BULK20": {"code": "BULK20", "discount_percent": 20, "valid": True},
            "BULK_EXTRA": {"code": "BULK_EXTRA", "discount_percent": 5, "valid": True},
            "VIP_DISCOUNT": {"code": "VIP_DISCOUNT", "discount_percent": 15, "valid": True},
            "EXPIRED2024": {"code": "EXPIRED2024", "discount_percent": 0, "valid": False},
            "INVALID_CODE": {"code": "INVALID_CODE", "valid": False},
        }

    async def get_bulk_pricing(self, product_id: str, quantity: int) -> dict:
        """Get bulk pricing for product."""
        # Default pricing with quantity-based discount tiers
        base_price = 100.0

        discount_rate = 0.0
        if quantity >= 1000:
            discount_rate = 0.20
        elif quantity >= 500:
            discount_rate = 0.15
        elif quantity >= 100:
            discount_rate = 0.10
        elif quantity >= 50:
            discount_rate = 0.05
        elif quantity >= 20:
            discount_rate = 0.05

        unit_price = base_price * (1 - discount_rate)

        return {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "base_unit_price": base_price,
            "discount_rate": discount_rate,
            "total_price": unit_price * quantity,
        }

    async def apply_coupon(self, coupon_code: str, cart_total: float) -> Optional[dict]:
        """Apply coupon to cart."""
        coupon = self.coupons.get(coupon_code)

        if not coupon or not coupon.get("valid"):
            return None

        discount_percent = coupon.get("discount_percent", 0)
        discount_amount = cart_total * (discount_percent / 100)

        return {
            "coupon_code": coupon_code,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "final_total": cart_total - discount_amount,
            "is_valid": True,
        }

    async def get_promotions(self) -> list[dict]:
        """Get active promotions."""
        return [
            {
                "id": "promo-1",
                "code": "SAVE10",
                "description": "Save 10% on orders",
                "discount_type": "percent",
                "discount_amount": 10,
            },
            {
                "id": "promo-2",
                "code": "BULK20",
                "description": "20% off bulk orders (1000+)",
                "discount_type": "percent",
                "discount_amount": 20,
            },
        ]

    async def calculate_savings(
        self, original_price: float, discount_rate: float, quantity: int
    ) -> dict:
        """Calculate savings for discount."""
        # Clamp discount rate to max 100% (1.0)
        effective_rate = min(discount_rate, 1.0)
        discount_per_unit = original_price * effective_rate
        total_savings = discount_per_unit * quantity
        final_price = original_price - discount_per_unit

        # Ensure savings don't exceed original price
        max_savings = original_price * quantity
        total_savings = min(total_savings, max_savings)

        return {
            "original_price": original_price,
            "discount_rate": discount_rate,
            "discount_per_unit": max(0, discount_per_unit),
            "quantity": quantity,
            "total_savings": max(0, total_savings),
            "final_price_per_unit": max(0, final_price),
            "total_final_price": max(0, final_price * quantity),
        }
