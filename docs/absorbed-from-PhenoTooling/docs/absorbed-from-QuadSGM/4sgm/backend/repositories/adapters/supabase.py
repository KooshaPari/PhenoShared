"""Supabase adapter implementations for repositories.

This module provides concrete implementations of all repository protocols
using Supabase PostgreSQL as the backend. These can be swapped with other
adapters (Oracle, SAP, etc.) without changing consumer code.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SupabaseProductRepository:
    """Supabase implementation of ProductRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client.

        Args:
            client: Supabase client instance
        """
        self.client = client
        self.table_name = "products"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve product by ID."""
        try:
            response = (
                self.client.table(self.table_name).select("*").eq("id", id).single().execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting product {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all products with pagination."""
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter products by arbitrary criteria."""
        try:
            query = self.client.table(self.table_name).select("*")

            # Apply filters
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing products with filters: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new product."""
        try:
            product_data = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.table_name).insert(product_data).execute()
            return response.data[0] if response.data else product_data
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update existing product."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = self.client.table(self.table_name).update(update_data).eq("id", id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating product {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete product by ID."""
        try:
            response = self.client.table(self.table_name).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting product {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if product exists."""
        product = await self.get(id)
        return product is not None

    async def get_by_sku(self, sku: str) -> Optional[dict]:
        """Get product by SKU."""
        try:
            response = (
                self.client.table(self.table_name).select("*").eq("sku", sku).single().execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting product by SKU {sku}: {e}")
            return None

    async def list_by_category(self, category: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List products in category."""
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("category", category)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing products by category: {e}")
            return []

    async def search(self, query: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """Full-text search products by name or description."""
        try:
            # Simple ILIKE search - can be enhanced with pgvector for semantic search
            response = (
                self.client.table(self.table_name)
                .select("*")
                .or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []

    async def update_inventory(self, product_id: str, quantity_change: int) -> Optional[dict]:
        """Update product inventory."""
        try:
            # Get current product
            product = await self.get(product_id)
            if not product:
                return None

            new_quantity = product.get("quantity_on_hand", 0) + quantity_change

            # Update quantity
            response = (
                self.client.table(self.table_name)
                .update(
                    {
                        "quantity_on_hand": max(0, new_quantity),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", product_id)
                .execute()
            )

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            return None

    async def get_low_stock(self, threshold: int = 10) -> list[dict]:
        """Get products below stock threshold."""
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .lt("quantity_on_hand", threshold)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return []


class SupabaseCartRepository:
    """Supabase implementation of CartRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client."""
        self.client = client
        self.carts_table = "carts"
        self.items_table = "cart_items"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve cart by ID."""
        try:
            response = (
                self.client.table(self.carts_table)
                .select("*, cart_items(*)")
                .eq("id", id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting cart {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all carts with pagination."""
        try:
            response = (
                self.client.table(self.carts_table)
                .select("*, cart_items(*)")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all carts: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter carts by criteria."""
        try:
            query = self.client.table(self.carts_table).select("*, cart_items(*)")
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing carts: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new cart."""
        try:
            cart_data = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.carts_table).insert(cart_data).execute()
            return response.data[0] if response.data else cart_data
        except Exception as e:
            logger.error(f"Error creating cart: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update cart."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = (
                self.client.table(self.carts_table).update(update_data).eq("id", id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating cart {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete cart by ID."""
        try:
            response = self.client.table(self.carts_table).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting cart {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if cart exists."""
        cart = await self.get(id)
        return cart is not None

    async def get_by_customer(self, customer_id: str) -> Optional[dict]:
        """Get active cart for customer."""
        try:
            response = (
                self.client.table(self.carts_table)
                .select("*, cart_items(*)")
                .eq("customer_id", customer_id)
                .eq("status", "active")
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting cart for customer {customer_id}: {e}")
            return None

    async def add_item(self, cart_id: str, product_id: str, quantity: int, price: float) -> dict:
        """Add item to cart."""
        try:
            item_data = {
                "id": str(uuid.uuid4()),
                "cart_id": cart_id,
                "product_id": product_id,
                "quantity": quantity,
                "price": price,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.client.table(self.items_table).insert(item_data).execute()

            # Update cart timestamp
            await self.update(cart_id, {})

            # Return updated cart
            return await self.get(cart_id) or {"id": cart_id}
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}")
            raise

    async def remove_item(self, cart_id: str, item_id: str) -> dict:
        """Remove item from cart."""
        try:
            self.client.table(self.items_table).delete().eq("id", item_id).execute()

            # Update cart timestamp
            await self.update(cart_id, {})

            return await self.get(cart_id) or {"id": cart_id}
        except Exception as e:
            logger.error(f"Error removing item from cart: {e}")
            raise

    async def update_item(self, cart_id: str, item_id: str, quantity: int) -> dict:
        """Update item quantity in cart."""
        try:
            self.client.table(self.items_table).update({"quantity": quantity}).eq(
                "id", item_id
            ).execute()

            # Update cart timestamp
            await self.update(cart_id, {})

            return await self.get(cart_id) or {"id": cart_id}
        except Exception as e:
            logger.error(f"Error updating cart item: {e}")
            raise

    async def clear(self, cart_id: str) -> dict:
        """Clear all items from cart."""
        try:
            self.client.table(self.items_table).delete().eq("cart_id", cart_id).execute()

            await self.update(cart_id, {"item_count": 0})
            return await self.get(cart_id) or {"id": cart_id}
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            raise

    async def calculate_total(self, cart_id: str) -> dict:
        """Calculate cart totals."""
        try:
            cart = await self.get(cart_id)
            if not cart:
                return {}

            items = cart.get("cart_items", [])
            subtotal = sum(item.get("quantity", 0) * item.get("price", 0) for item in items)

            # Simple tax calculation (can be enhanced)
            tax_rate = 0.08
            tax = subtotal * tax_rate

            # Placeholder shipping (can be integrated with ShippingRepository)
            shipping = 10.0 if subtotal > 0 else 0

            total = subtotal + tax + shipping

            return {**cart, "subtotal": subtotal, "tax": tax, "shipping": shipping, "total": total}
        except Exception as e:
            logger.error(f"Error calculating cart total: {e}")
            raise


class SupabaseOrderRepository:
    """Supabase implementation of OrderRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client."""
        self.client = client
        self.orders_table = "orders"
        self.items_table = "order_items"
        self.shipments_table = "shipments"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve order by ID."""
        try:
            response = (
                self.client.table(self.orders_table)
                .select("*, order_items(*), shipments(*)")
                .eq("id", id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting order {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all orders with pagination."""
        try:
            response = (
                self.client.table(self.orders_table)
                .select("*, order_items(*), shipments(*)")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter orders by criteria."""
        try:
            query = self.client.table(self.orders_table).select("*, order_items(*), shipments(*)")
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing orders: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new order."""
        try:
            order_data = {
                "id": str(uuid.uuid4()),
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.orders_table).insert(order_data).execute()
            return response.data[0] if response.data else order_data
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update order."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = (
                self.client.table(self.orders_table).update(update_data).eq("id", id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating order {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete order by ID."""
        try:
            response = self.client.table(self.orders_table).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting order {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if order exists."""
        order = await self.get(id)
        return order is not None

    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders for customer."""
        try:
            response = (
                self.client.table(self.orders_table)
                .select("*, order_items(*), shipments(*)")
                .eq("customer_id", customer_id)
                .order("created_at", desc=True)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting orders for customer: {e}")
            return []

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders by status."""
        try:
            response = (
                self.client.table(self.orders_table)
                .select("*, order_items(*), shipments(*)")
                .eq("status", status)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting orders by status: {e}")
            return []

    async def get_line_items(self, order_id: str) -> list[dict]:
        """Get line items for order."""
        try:
            response = (
                self.client.table(self.items_table).select("*").eq("order_id", order_id).execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting order items: {e}")
            return []

    async def update_status(self, order_id: str, status: str, notes: str = "") -> Optional[dict]:
        """Update order status."""
        try:
            response = (
                self.client.table(self.orders_table)
                .update(
                    {
                        "status": status,
                        "status_notes": notes,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", order_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return None

    async def add_shipment(self, order_id: str, tracking_number: str, carrier: str) -> dict:
        """Add shipment tracking to order."""
        try:
            shipment_data = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "tracking_number": tracking_number,
                "carrier": carrier,
                "status": "in_transit",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.client.table(self.shipments_table).insert(shipment_data).execute()

            await self.update_status(order_id, "shipped")
            return await self.get(order_id) or {"id": order_id}
        except Exception as e:
            logger.error(f"Error adding shipment: {e}")
            raise

    async def get_pending_fulfillment(self) -> list[dict]:
        """Get orders awaiting fulfillment."""
        try:
            response = (
                self.client.table(self.orders_table)
                .select("*, order_items(*)")
                .eq("status", "pending")
                .order("created_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting pending fulfillment: {e}")
            return []


class SupabaseCustomerRepository:
    """Supabase implementation of CustomerRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client."""
        self.client = client
        self.customers_table = "customers"
        self.addresses_table = "customer_addresses"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve customer by ID."""
        try:
            response = (
                self.client.table(self.customers_table)
                .select("*, customer_addresses(*)")
                .eq("id", id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting customer {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all customers with pagination."""
        try:
            response = (
                self.client.table(self.customers_table)
                .select("*, customer_addresses(*)")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all customers: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter customers by criteria."""
        try:
            query = self.client.table(self.customers_table).select("*, customer_addresses(*)")
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing customers: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new customer."""
        try:
            customer_data = {
                "id": str(uuid.uuid4()),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.customers_table).insert(customer_data).execute()
            return response.data[0] if response.data else customer_data
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update customer."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = (
                self.client.table(self.customers_table).update(update_data).eq("id", id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating customer {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete customer by ID."""
        try:
            response = self.client.table(self.customers_table).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting customer {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if customer exists."""
        customer = await self.get(id)
        return customer is not None

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get customer by email."""
        try:
            response = (
                self.client.table(self.customers_table)
                .select("*, customer_addresses(*)")
                .eq("email", email)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting customer by email: {e}")
            return None

    async def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List customers by status."""
        try:
            response = (
                self.client.table(self.customers_table)
                .select("*, customer_addresses(*)")
                .eq("status", status)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing customers by status: {e}")
            return []

    async def update_profile(self, customer_id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update customer profile."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = (
                self.client.table(self.customers_table)
                .update(update_data)
                .eq("id", customer_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating customer profile: {e}")
            return None

    async def add_address(self, customer_id: str, address_data: dict[str, Any]) -> dict:
        """Add address to customer."""
        try:
            address = {
                "id": str(uuid.uuid4()),
                "customer_id": customer_id,
                "is_default": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **address_data,
            }
            response = self.client.table(self.addresses_table).insert(address).execute()
            return response.data[0] if response.data else address
        except Exception as e:
            logger.error(f"Error adding address: {e}")
            raise

    async def get_addresses(self, customer_id: str) -> list[dict]:
        """Get all addresses for customer."""
        try:
            response = (
                self.client.table(self.addresses_table)
                .select("*")
                .eq("customer_id", customer_id)
                .order("is_default", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting customer addresses: {e}")
            return []

    async def set_default_address(self, customer_id: str, address_id: str) -> dict:
        """Set default address for customer."""
        try:
            # Clear existing defaults
            self.client.table(self.addresses_table).update({"is_default": False}).eq(
                "customer_id", customer_id
            ).execute()

            # Set new default
            self.client.table(self.addresses_table).update({"is_default": True}).eq(
                "id", address_id
            ).execute()

            return await self.get(customer_id) or {"id": customer_id}
        except Exception as e:
            logger.error(f"Error setting default address: {e}")
            raise


class SupabaseShippingRepository:
    """Supabase implementation of ShippingRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client."""
        self.client = client
        self.methods_table = "shipping_methods"
        self.rates_table = "shipping_rates"
        self.tracking_table = "shipment_tracking"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve shipping method by ID."""
        try:
            response = (
                self.client.table(self.methods_table).select("*").eq("id", id).single().execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting shipping method {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all shipping methods."""
        try:
            response = (
                self.client.table(self.methods_table)
                .select("*")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting shipping methods: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter shipping methods by criteria."""
        try:
            query = self.client.table(self.methods_table).select("*")
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing shipping methods: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new shipping method."""
        try:
            method_data = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.methods_table).insert(method_data).execute()
            return response.data[0] if response.data else method_data
        except Exception as e:
            logger.error(f"Error creating shipping method: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update shipping method."""
        try:
            response = self.client.table(self.methods_table).update(data).eq("id", id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating shipping method {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete shipping method by ID."""
        try:
            response = self.client.table(self.methods_table).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting shipping method {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if shipping method exists."""
        method = await self.get(id)
        return method is not None

    async def get_rates(self, origin: str, destination: str, weight: float) -> list[dict]:
        """Get shipping rates for route and weight."""
        try:
            response = (
                self.client.table(self.rates_table)
                .select("*")
                .eq("origin", origin)
                .eq("destination", destination)
                .lte("max_weight", weight)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting shipping rates: {e}")
            return []

    async def get_by_carrier(self, carrier: str) -> list[dict]:
        """Get shipping methods for carrier."""
        try:
            response = (
                self.client.table(self.methods_table).select("*").eq("carrier", carrier).execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting methods by carrier: {e}")
            return []

    async def track(self, tracking_number: str, carrier: str) -> Optional[dict]:
        """Get shipment tracking status."""
        try:
            response = (
                self.client.table(self.tracking_table)
                .select("*")
                .eq("tracking_number", tracking_number)
                .eq("carrier", carrier)
                .order("updated_at", desc=True)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting tracking info: {e}")
            return None

    async def create_shipment(self, order_id: str, carrier: str, service: str) -> dict:
        """Create shipment and generate label."""
        try:
            shipment_data = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "carrier": carrier,
                "service": service,
                "status": "label_generated",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            response = self.client.table(self.tracking_table).insert(shipment_data).execute()
            return response.data[0] if response.data else shipment_data
        except Exception as e:
            logger.error(f"Error creating shipment: {e}")
            raise

    async def estimate_delivery(
        self, carrier: str, destination: str, service: str
    ) -> Optional[datetime]:
        """Estimate delivery date."""
        try:
            # Simple estimation based on service level (can be enhanced)
            # In production, this would integrate with carrier APIs
            response = (
                self.client.table(self.rates_table)
                .select("estimated_days")
                .eq("carrier", carrier)
                .eq("service", service)
                .single()
                .execute()
            )

            if response.data and "estimated_days" in response.data:
                days = response.data["estimated_days"]
                return datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + days)
            return None
        except Exception as e:
            logger.error(f"Error estimating delivery: {e}")
            return None


class SupabaseRFQRepository:
    """Supabase implementation of RFQRepository protocol."""

    def __init__(self, client):
        """Initialize with Supabase client."""
        self.client = client
        self.rfqs_table = "rfqs"
        self.items_table = "rfq_items"
        self.quotes_table = "rfq_quotes"

    async def get(self, id: str) -> Optional[dict]:
        """Retrieve RFQ by ID."""
        try:
            response = (
                self.client.table(self.rfqs_table)
                .select("*, rfq_items(*), rfq_quotes(*)")
                .eq("id", id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting RFQ {id}: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Retrieve all RFQs with pagination."""
        try:
            response = (
                self.client.table(self.rfqs_table)
                .select("*, rfq_items(*), rfq_quotes(*)")
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all RFQs: {e}")
            return []

    async def list(self, **filters) -> list[dict]:
        """Filter RFQs by criteria."""
        try:
            query = self.client.table(self.rfqs_table).select("*, rfq_items(*), rfq_quotes(*)")
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error listing RFQs: {e}")
            return []

    async def create(self, data: dict[str, Any]) -> dict:
        """Create new RFQ."""
        try:
            rfq_data = {
                "id": str(uuid.uuid4()),
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            response = self.client.table(self.rfqs_table).insert(rfq_data).execute()
            return response.data[0] if response.data else rfq_data
        except Exception as e:
            logger.error(f"Error creating RFQ: {e}")
            raise

    async def update(self, id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update RFQ."""
        try:
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat(), **data}
            response = self.client.table(self.rfqs_table).update(update_data).eq("id", id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating RFQ {id}: {e}")
            return None

    async def delete(self, id: str) -> bool:
        """Delete RFQ by ID."""
        try:
            response = self.client.table(self.rfqs_table).delete().eq("id", id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting RFQ {id}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if RFQ exists."""
        rfq = await self.get(id)
        return rfq is not None

    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs for customer."""
        try:
            response = (
                self.client.table(self.rfqs_table)
                .select("*, rfq_items(*), rfq_quotes(*)")
                .eq("customer_id", customer_id)
                .order("created_at", desc=True)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting RFQs for customer: {e}")
            return []

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs by status."""
        try:
            response = (
                self.client.table(self.rfqs_table)
                .select("*, rfq_items(*), rfq_quotes(*)")
                .eq("status", status)
                .range(skip, skip + limit - 1)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting RFQs by status: {e}")
            return []

    async def get_items(self, rfq_id: str) -> list[dict]:
        """Get line items for RFQ."""
        try:
            response = (
                self.client.table(self.items_table).select("*").eq("rfq_id", rfq_id).execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting RFQ items: {e}")
            return []

    async def add_quote(self, rfq_id: str, quote_data: dict[str, Any]) -> dict:
        """Add quote response to RFQ."""
        try:
            quote = {
                "id": str(uuid.uuid4()),
                "rfq_id": rfq_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **quote_data,
            }
            self.client.table(self.quotes_table).insert(quote).execute()
            await self.update(rfq_id, {"status": "quoted"})
            return await self.get(rfq_id) or {"id": rfq_id}
        except Exception as e:
            logger.error(f"Error adding quote: {e}")
            raise

    async def get_quote(self, rfq_id: str) -> Optional[dict]:
        """Get active quote for RFQ."""
        try:
            response = (
                self.client.table(self.quotes_table)
                .select("*")
                .eq("rfq_id", rfq_id)
                .eq("status", "active")
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None

    async def accept_quote(self, rfq_id: str) -> dict:
        """Accept quote and convert to order."""
        try:
            await self.update(rfq_id, {"status": "accepted"})
            # In production, create order from RFQ here
            return await self.get(rfq_id) or {"id": rfq_id}
        except Exception as e:
            logger.error(f"Error accepting quote: {e}")
            raise

    async def get_pending_quotes(self) -> list[dict]:
        """Get RFQs awaiting quote responses."""
        try:
            response = (
                self.client.table(self.rfqs_table)
                .select("*, rfq_items(*)")
                .eq("status", "open")
                .order("created_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting pending RFQs: {e}")
            return []
