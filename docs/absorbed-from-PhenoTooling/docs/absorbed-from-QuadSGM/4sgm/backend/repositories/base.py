"""Protocol definitions for repository pattern.

This module defines the interface contracts for all repositories using
Python's typing.Protocol. These protocols allow for flexible implementations
that can be swapped (Supabase, Oracle, SAP, etc.) without changing consumer code.

Protocols are structural subtypes - any class implementing these methods
satisfies the protocol without explicit inheritance.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional, Protocol, TypeVar

T = TypeVar("T")


class BaseRepository(Protocol[T]):
    """Base protocol for all repositories.

    Defines CRUD operations common to all data access patterns.
    Any adapter (Supabase, Oracle, etc.) implementing these methods
    can be used interchangeably.
    """

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Retrieve single entity by ID.

        Args:
            id: Entity identifier

        Returns:
            Entity instance or None if not found
        """
        ...

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Retrieve multiple entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entity instances
        """
        ...

    @abstractmethod
    async def list(self, **filters) -> list[T]:
        """Filter entities by arbitrary criteria.

        Args:
            **filters: Filter parameters (implementation-specific)

        Returns:
            List of matching entities
        """
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> T:
        """Create new entity.

        Args:
            data: Entity data (validated upstream)

        Returns:
            Created entity instance
        """
        ...

    @abstractmethod
    async def update(self, id: str, data: dict[str, Any]) -> Optional[T]:
        """Update existing entity.

        Args:
            id: Entity identifier
            data: Fields to update

        Returns:
            Updated entity or None if not found
        """
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID.

        Args:
            id: Entity identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if entity exists.

        Args:
            id: Entity identifier

        Returns:
            True if exists, False otherwise
        """
        ...


class ProductRepository(BaseRepository[dict]):
    """Product repository protocol.

    Handles product catalog operations including search, filtering by category,
    and inventory tracking.
    """

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[dict]:
        """Get product by SKU (unique identifier).

        Args:
            sku: Product SKU

        Returns:
            Product data or None if not found
        """
        ...

    @abstractmethod
    async def list_by_category(self, category: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List products in a category.

        Args:
            category: Product category
            skip: Pagination offset
            limit: Max records

        Returns:
            List of products
        """
        ...

    @abstractmethod
    async def search(self, query: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """Full-text search products.

        Args:
            query: Search query
            skip: Pagination offset
            limit: Max records

        Returns:
            List of matching products
        """
        ...

    @abstractmethod
    async def update_inventory(self, product_id: str, quantity_change: int) -> Optional[dict]:
        """Update product inventory.

        Args:
            product_id: Product ID
            quantity_change: Quantity to add/subtract

        Returns:
            Updated product or None if not found
        """
        ...

    @abstractmethod
    async def get_low_stock(self, threshold: int = 10) -> list[dict]:
        """Get products below stock threshold.

        Args:
            threshold: Minimum stock level

        Returns:
            List of low-stock products
        """
        ...


class CartRepository(BaseRepository[dict]):
    """Cart repository protocol.

    Manages shopping carts and line items.
    """

    @abstractmethod
    async def get_by_customer(self, customer_id: str) -> Optional[dict]:
        """Get active cart for customer.

        Args:
            customer_id: Customer ID

        Returns:
            Cart data or None
        """
        ...

    @abstractmethod
    async def add_item(self, cart_id: str, product_id: str, quantity: int, price: float) -> dict:
        """Add item to cart.

        Args:
            cart_id: Cart ID
            product_id: Product ID
            quantity: Item quantity
            price: Unit price at time of add

        Returns:
            Updated cart
        """
        ...

    @abstractmethod
    async def remove_item(self, cart_id: str, item_id: str) -> dict:
        """Remove item from cart.

        Args:
            cart_id: Cart ID
            item_id: Line item ID

        Returns:
            Updated cart
        """
        ...

    @abstractmethod
    async def update_item(self, cart_id: str, item_id: str, quantity: int) -> dict:
        """Update item quantity in cart.

        Args:
            cart_id: Cart ID
            item_id: Line item ID
            quantity: New quantity

        Returns:
            Updated cart
        """
        ...

    @abstractmethod
    async def clear(self, cart_id: str) -> dict:
        """Clear all items from cart.

        Args:
            cart_id: Cart ID

        Returns:
            Cleared cart
        """
        ...

    @abstractmethod
    async def calculate_total(self, cart_id: str) -> dict:
        """Calculate cart totals (subtotal, tax, shipping, total).

        Args:
            cart_id: Cart ID

        Returns:
            Cart with calculated totals
        """
        ...


class OrderRepository(BaseRepository[dict]):
    """Order repository protocol.

    Manages customer orders through their lifecycle.
    """

    @abstractmethod
    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders for customer.

        Args:
            customer_id: Customer ID
            skip: Pagination offset
            limit: Max records

        Returns:
            List of orders
        """
        ...

    @abstractmethod
    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get orders by status.

        Args:
            status: Order status (pending, shipped, delivered, etc.)
            skip: Pagination offset
            limit: Max records

        Returns:
            List of matching orders
        """
        ...

    @abstractmethod
    async def get_line_items(self, order_id: str) -> list[dict]:
        """Get line items for order.

        Args:
            order_id: Order ID

        Returns:
            List of line items
        """
        ...

    @abstractmethod
    async def update_status(self, order_id: str, status: str, notes: str = "") -> Optional[dict]:
        """Update order status.

        Args:
            order_id: Order ID
            status: New status
            notes: Status change notes

        Returns:
            Updated order or None
        """
        ...

    @abstractmethod
    async def add_shipment(self, order_id: str, tracking_number: str, carrier: str) -> dict:
        """Add shipment tracking to order.

        Args:
            order_id: Order ID
            tracking_number: Carrier tracking number
            carrier: Shipping carrier name

        Returns:
            Updated order with shipment
        """
        ...

    @abstractmethod
    async def get_pending_fulfillment(self) -> list[dict]:
        """Get orders awaiting fulfillment.

        Returns:
            List of pending orders
        """
        ...


class CustomerRepository(BaseRepository[dict]):
    """Customer repository protocol.

    Manages customer accounts and profiles.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get customer by email.

        Args:
            email: Customer email

        Returns:
            Customer data or None
        """
        ...

    @abstractmethod
    async def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """List customers by status (active, inactive, etc.).

        Args:
            status: Customer status
            skip: Pagination offset
            limit: Max records

        Returns:
            List of customers
        """
        ...

    @abstractmethod
    async def update_profile(self, customer_id: str, data: dict[str, Any]) -> Optional[dict]:
        """Update customer profile.

        Args:
            customer_id: Customer ID
            data: Fields to update

        Returns:
            Updated customer or None
        """
        ...

    @abstractmethod
    async def add_address(self, customer_id: str, address_data: dict[str, Any]) -> dict:
        """Add address to customer.

        Args:
            customer_id: Customer ID
            address_data: Address details

        Returns:
            Created address
        """
        ...

    @abstractmethod
    async def get_addresses(self, customer_id: str) -> list[dict]:
        """Get all addresses for customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of addresses
        """
        ...

    @abstractmethod
    async def set_default_address(self, customer_id: str, address_id: str) -> dict:
        """Set default address for customer.

        Args:
            customer_id: Customer ID
            address_id: Address ID

        Returns:
            Updated customer
        """
        ...


class ShippingRepository(BaseRepository[dict]):
    """Shipping repository protocol.

    Handles shipping methods, rates, and tracking.
    """

    @abstractmethod
    async def get_rates(self, origin: str, destination: str, weight: float) -> list[dict]:
        """Get shipping rates for route and weight.

        Args:
            origin: Origin postal code/location
            destination: Destination postal code/location
            weight: Package weight in lbs

        Returns:
            List of shipping options with rates
        """
        ...

    @abstractmethod
    async def get_by_carrier(self, carrier: str) -> list[dict]:
        """Get configured shipping methods for carrier.

        Args:
            carrier: Carrier name (USPS, FedEx, UPS, etc.)

        Returns:
            List of shipping methods
        """
        ...

    @abstractmethod
    async def track(self, tracking_number: str, carrier: str) -> Optional[dict]:
        """Get shipment tracking status.

        Args:
            tracking_number: Carrier tracking number
            carrier: Shipping carrier

        Returns:
            Tracking data or None
        """
        ...

    @abstractmethod
    async def create_shipment(self, order_id: str, carrier: str, service: str) -> dict:
        """Create shipment and generate label.

        Args:
            order_id: Order ID
            carrier: Shipping carrier
            service: Service level

        Returns:
            Shipment with tracking and label
        """
        ...

    @abstractmethod
    async def estimate_delivery(
        self, carrier: str, destination: str, service: str
    ) -> Optional[datetime]:
        """Estimate delivery date.

        Args:
            carrier: Shipping carrier
            destination: Destination location
            service: Service level

        Returns:
            Estimated delivery date or None
        """
        ...


class RFQRepository(BaseRepository[dict]):
    """Request for Quote repository protocol.

    Manages RFQ creation, responses, and quotes.
    """

    @abstractmethod
    async def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs for customer.

        Args:
            customer_id: Customer ID
            skip: Pagination offset
            limit: Max records

        Returns:
            List of RFQs
        """
        ...

    @abstractmethod
    async def get_by_status(self, status: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get RFQs by status.

        Args:
            status: RFQ status (open, quoted, accepted, rejected, etc.)
            skip: Pagination offset
            limit: Max records

        Returns:
            List of matching RFQs
        """
        ...

    @abstractmethod
    async def get_items(self, rfq_id: str) -> list[dict]:
        """Get line items for RFQ.

        Args:
            rfq_id: RFQ ID

        Returns:
            List of requested items
        """
        ...

    @abstractmethod
    async def add_quote(self, rfq_id: str, quote_data: dict[str, Any]) -> dict:
        """Add quote response to RFQ.

        Args:
            rfq_id: RFQ ID
            quote_data: Quote details (items, pricing, expiry, etc.)

        Returns:
            Updated RFQ with quote
        """
        ...

    @abstractmethod
    async def get_quote(self, rfq_id: str) -> Optional[dict]:
        """Get active quote for RFQ.

        Args:
            rfq_id: RFQ ID

        Returns:
            Quote data or None
        """
        ...

    @abstractmethod
    async def accept_quote(self, rfq_id: str) -> dict:
        """Accept quote and convert to order.

        Args:
            rfq_id: RFQ ID

        Returns:
            Created order from accepted quote
        """
        ...

    @abstractmethod
    async def get_pending_quotes(self) -> list[dict]:
        """Get RFQs awaiting quote responses.

        Returns:
            List of pending RFQs
        """
        ...
