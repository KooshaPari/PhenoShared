"""Example implementations using the repository pattern.

This module demonstrates how to use repositories in real application code.
All examples use dependency injection via FastAPI's Depends().
"""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Pydantic models for request/response
class ProductRequest(BaseModel):
    """Product creation/update request."""

    sku: str
    name: str
    description: Optional[str] = None
    price: float
    quantity_on_hand: int = 0
    category: Optional[str] = None


class ProductResponse(BaseModel):
    """Product response."""

    id: str
    sku: str
    name: str
    description: Optional[str]
    price: float
    quantity_on_hand: int
    category: Optional[str]


class AddToCartRequest(BaseModel):
    """Add to cart request."""

    product_id: str
    quantity: int


class OrderResponse(BaseModel):
    """Order response."""

    id: str
    customer_id: str
    status: str
    total: float


# Service layer examples
class ProductService:
    """Service for product operations using repository."""

    def __init__(self, repo):
        """Initialize with product repository.

        Args:
            repo: ProductRepository instance (injected)
        """
        self.repo = repo

    async def get_product(self, product_id: str) -> Optional[dict]:
        """Get product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product data or None if not found
        """
        product = await self.repo.get(product_id)
        return product

    async def create_product(self, data: ProductRequest) -> dict:
        """Create new product.

        Args:
            data: Product data

        Returns:
            Created product
        """
        product = await self.repo.create(data.dict())
        logger.info(f"Created product: {product['id']}")
        return product

    async def search_products(self, query: str) -> list[dict]:
        """Search products by name or description.

        Args:
            query: Search query

        Returns:
            List of matching products
        """
        products = await self.repo.search(query)
        return products

    async def get_category(self, category: str) -> list[dict]:
        """Get products in category.

        Args:
            category: Product category

        Returns:
            List of products
        """
        products = await self.repo.list_by_category(category)
        return products

    async def reorder_low_stock(self, threshold: int = 10) -> list[dict]:
        """Get products below stock threshold for reordering.

        Args:
            threshold: Minimum stock level

        Returns:
            List of low stock products
        """
        products = await self.repo.get_low_stock(threshold)
        logger.warning(f"Low stock products: {len(products)}")
        return products


class CartService:
    """Service for cart operations using repository."""

    def __init__(self, cart_repo, product_repo):
        """Initialize with repositories.

        Args:
            cart_repo: CartRepository instance
            product_repo: ProductRepository instance
        """
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    async def get_or_create_cart(self, customer_id: str) -> dict:
        """Get or create customer's cart.

        Args:
            customer_id: Customer ID

        Returns:
            Cart data
        """
        cart = await self.cart_repo.get_by_customer(customer_id)
        if cart:
            return cart

        # Create new cart
        cart = await self.cart_repo.create({"customer_id": customer_id})
        logger.info(f"Created cart for customer: {customer_id}")
        return cart

    async def add_to_cart(self, customer_id: str, product_id: str, quantity: int) -> dict:
        """Add product to customer's cart.

        Args:
            customer_id: Customer ID
            product_id: Product ID
            quantity: Item quantity

        Returns:
            Updated cart
        """
        # Get product to verify existence and get price
        product = await self.product_repo.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Check stock
        if product.get("quantity_on_hand", 0) < quantity:
            raise ValueError("Insufficient stock")

        # Get or create cart
        cart = await self.get_or_create_cart(customer_id)

        # Add item
        cart = await self.cart_repo.add_item(cart["id"], product_id, quantity, product["price"])

        logger.info(f"Added {quantity} of {product_id} to cart {cart['id']}")
        return cart

    async def get_cart_summary(self, customer_id: str) -> dict:
        """Get cart with calculated totals.

        Args:
            customer_id: Customer ID

        Returns:
            Cart with totals
        """
        cart = await self.cart_repo.get_by_customer(customer_id)
        if not cart:
            return {"items": [], "total": 0}

        totals = await self.cart_repo.calculate_total(cart["id"])
        return totals

    async def checkout(self, customer_id: str) -> str:
        """Convert cart to order (returns order ID).

        Args:
            customer_id: Customer ID

        Returns:
            Created order ID
        """
        cart = await self.cart_repo.get_by_customer(customer_id)
        if not cart or not cart.get("cart_items"):
            raise ValueError("Cart is empty")

        await self.cart_repo.calculate_total(cart["id"])

        # Create order (would use order_repo in real app)
        # order_id = await order_repo.create({...})

        # Clear cart
        await self.cart_repo.clear(cart["id"])

        logger.info(f"Checked out cart {cart['id']}")
        return "order_123"  # placeholder


class OrderService:
    """Service for order operations using repository."""

    def __init__(self, order_repo, shipping_repo):
        """Initialize with repositories.

        Args:
            order_repo: OrderRepository instance
            shipping_repo: ShippingRepository instance
        """
        self.order_repo = order_repo
        self.shipping_repo = shipping_repo

    async def get_customer_orders(self, customer_id: str) -> list[dict]:
        """Get all orders for customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of orders
        """
        orders = await self.order_repo.get_by_customer(customer_id)
        return orders

    async def get_pending_orders(self) -> list[dict]:
        """Get orders awaiting fulfillment.

        Returns:
            List of pending orders
        """
        orders = await self.order_repo.get_pending_fulfillment()
        return orders

    async def ship_order(self, order_id: str, carrier: str, tracking_number: str) -> dict:
        """Add shipment to order.

        Args:
            order_id: Order ID
            carrier: Shipping carrier
            tracking_number: Carrier tracking number

        Returns:
            Updated order
        """
        order = await self.order_repo.add_shipment(order_id, tracking_number, carrier)
        logger.info(f"Shipped order {order_id} via {carrier}")
        return order

    async def get_tracking(self, tracking_number: str, carrier: str) -> Optional[dict]:
        """Get shipment tracking status.

        Args:
            tracking_number: Tracking number
            carrier: Shipping carrier

        Returns:
            Tracking info or None
        """
        tracking = await self.shipping_repo.track(tracking_number, carrier)
        return tracking


# FastAPI route examples
def create_routes(app: FastAPI):
    """Create example routes using repositories.

    Args:
        app: FastAPI application
    """

    # Product routes
    @app.get("/products/{product_id}", response_model=ProductResponse)
    async def get_product(
        product_id: str,
        service=Depends(
            lambda: ProductService(
                __import__(
                    "repositories.dependencies", fromlist=["get_product_repo"]
                ).get_product_repo()
            )
        ),
    ):
        """Get product by ID."""
        product = await service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    @app.post("/products", response_model=ProductResponse)
    async def create_product(
        request: ProductRequest,
        service=Depends(
            lambda: ProductService(
                __import__(
                    "repositories.dependencies", fromlist=["get_product_repo"]
                ).get_product_repo()
            )
        ),
    ):
        """Create new product."""
        product = await service.create_product(request)
        return product

    @app.get("/products/search")
    async def search_products(
        q: str,
        service=Depends(
            lambda: ProductService(
                __import__(
                    "repositories.dependencies", fromlist=["get_product_repo"]
                ).get_product_repo()
            )
        ),
    ):
        """Search products."""
        products = await service.search_products(q)
        return products

    # Cart routes
    @app.post("/cart/add-item")
    async def add_to_cart(
        customer_id: str,
        request: AddToCartRequest,
        cart_repo=Depends(
            __import__("repositories.dependencies", fromlist=["get_cart_repo"]).get_cart_repo()
        ),
        product_repo=Depends(
            __import__(
                "repositories.dependencies", fromlist=["get_product_repo"]
            ).get_product_repo()
        ),
    ):
        """Add item to customer's cart."""
        service = CartService(cart_repo, product_repo)
        try:
            cart = await service.add_to_cart(customer_id, request.product_id, request.quantity)
            return cart
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/cart/{customer_id}")
    async def get_cart(
        customer_id: str,
        cart_repo=Depends(
            __import__("repositories.dependencies", fromlist=["get_cart_repo"]).get_cart_repo()
        ),
        product_repo=Depends(
            __import__(
                "repositories.dependencies", fromlist=["get_product_repo"]
            ).get_product_repo()
        ),
    ):
        """Get customer's cart summary."""
        service = CartService(cart_repo, product_repo)
        cart = await service.get_cart_summary(customer_id)
        return cart

    # Order routes
    @app.get("/orders/{customer_id}")
    async def get_orders(
        customer_id: str,
        order_repo=Depends(
            __import__("repositories.dependencies", fromlist=["get_order_repo"]).get_order_repo()
        ),
        shipping_repo=Depends(
            __import__(
                "repositories.dependencies", fromlist=["get_shipping_repo"]
            ).get_shipping_repo()
        ),
    ):
        """Get customer's orders."""
        service = OrderService(order_repo, shipping_repo)
        orders = await service.get_customer_orders(customer_id)
        return orders

    @app.post("/orders/{order_id}/ship")
    async def ship_order(
        order_id: str,
        carrier: str,
        tracking_number: str,
        order_repo=Depends(
            __import__("repositories.dependencies", fromlist=["get_order_repo"]).get_order_repo()
        ),
        shipping_repo=Depends(
            __import__(
                "repositories.dependencies", fromlist=["get_shipping_repo"]
            ).get_shipping_repo()
        ),
    ):
        """Ship an order."""
        service = OrderService(order_repo, shipping_repo)
        try:
            order = await service.ship_order(order_id, carrier, tracking_number)
            return order
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
