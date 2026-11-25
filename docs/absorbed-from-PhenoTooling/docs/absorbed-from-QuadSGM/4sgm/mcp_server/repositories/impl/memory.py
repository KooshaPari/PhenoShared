"""In-memory repository implementations for testing and development."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ..product import ProductRepository, Product
from ..inventory import InventoryRepository, Inventory
from ..pricing import PricingRepository
from ..cart import CartRepository, Cart, CartItem
from ..order import OrderRepository, Order
from ..shipping import ShippingRepository
from ..customer import CustomerRepository
from ..rfq import RFQRepository


@dataclass
class _FlatInventory:
    """Inventory view with flat interface field names (in_stock, available, warehouse_locations)."""

    product_id: str
    in_stock: int
    reserved: int
    available: int
    warehouse_locations: List[str] = field(default_factory=list)


# Sample product data
SAMPLE_PRODUCTS = {
    "LAPTOP-PRO-15": Product(
        id="1",
        sku="LAPTOP-PRO-15",
        name='Laptop Pro 15"',
        description="High-performance laptop with 16GB RAM and 512GB SSD",
        price=1299.99,
        category="electronics",
        brand="TechPro",
        in_stock=True,
        rating=4.5,
        reviews=128,
        quantity_on_hand=15,
    ),
    "MOUSE-WIRELESS": Product(
        id="2",
        sku="MOUSE-WIRELESS",
        name="Wireless Mouse",
        description="Ergonomic wireless mouse with long battery life",
        price=29.99,
        category="accessories",
        brand="PeriphCo",
        in_stock=True,
        rating=4.2,
        reviews=256,
        quantity_on_hand=100,
    ),
    "HUB-USB-C": Product(
        id="3",
        sku="HUB-USB-C",
        name="USB-C Hub",
        description="Multi-port USB-C hub with HDMI, USB-A, and SD card slots",
        price=49.99,
        category="accessories",
        brand="ConnectPlus",
        in_stock=True,
        rating=4.0,
        reviews=89,
        quantity_on_hand=45,
    ),
    "MONITOR-4K": Product(
        id="4",
        sku="MONITOR-4K",
        name="Monitor 4K",
        description="27-inch 4K UHD monitor with HDR support",
        price=399.99,
        category="electronics",
        brand="DisplayMax",
        in_stock=True,
        rating=4.7,
        reviews=312,
        quantity_on_hand=22,
    ),
    "KEYBOARD-MECH": Product(
        id="5",
        sku="KEYBOARD-MECH",
        name="Mechanical Keyboard",
        description="RGB mechanical gaming keyboard with Cherry MX switches",
        price=149.99,
        category="accessories",
        brand="KeyMaster",
        in_stock=True,
        rating=4.6,
        reviews=445,
        quantity_on_hand=67,
    ),
    "WEBCAM-HD": Product(
        id="6",
        sku="WEBCAM-HD",
        name="Webcam HD",
        description="1080p HD webcam with built-in microphone",
        price=79.99,
        category="electronics",
        brand="VidPro",
        in_stock=True,
        rating=4.1,
        reviews=178,
        quantity_on_hand=38,
    ),
    "HEADPHONES-PRO": Product(
        id="7",
        sku="HEADPHONES-PRO",
        name="Headphones Pro",
        description="Noise-cancelling wireless headphones with 30hr battery",
        price=199.99,
        category="audio",
        brand="SoundMax",
        in_stock=True,
        rating=4.8,
        reviews=523,
        quantity_on_hand=29,
    ),
    "LAMP-LED": Product(
        id="8",
        sku="LAMP-LED",
        name="Desk Lamp LED",
        description="Adjustable LED desk lamp with multiple brightness levels",
        price=59.99,
        category="lighting",
        brand="BrightHome",
        in_stock=True,
        rating=4.3,
        reviews=67,
        quantity_on_hand=55,
    ),
}


class InMemoryProductRepository(ProductRepository):
    """In-memory product repository."""

    def __init__(self):
        self._products = {p.id: p for p in SAMPLE_PRODUCTS.values()}
        self._by_sku = SAMPLE_PRODUCTS.copy()

    async def get(self, id: str) -> Optional[Product]:
        return self._products.get(id)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        return self._by_sku.get(sku.upper())

    async def search(
        self, query: str, limit: int = 10, category: Optional[str] = None
    ) -> List[Product]:
        query_lower = query.lower()
        results = []
        for product in self._products.values():
            if (
                query_lower in product.name.lower()
                or query_lower in product.description.lower()
            ):
                if category is None or product.category == category:
                    results.append(product)
        return results[:limit]

    async def list(self, category: Optional[str] = None, **filters) -> List[Product]:
        if category:
            return [p for p in self._products.values() if p.category == category]
        return list(self._products.values())

    async def create(self, **data) -> Product:
        product = Product(**data)
        self._products[product.id] = product
        self._by_sku[product.sku] = product
        return product

    async def update(self, id: str, **data) -> Product:
        if id in self._products:
            product = self._products[id]
            for key, value in data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            return product
        return None

    async def delete(self, id: str) -> bool:
        if id in self._products:
            product = self._products.pop(id)
            self._by_sku.pop(product.sku, None)
            return True
        return False

    async def get_pricing(self, product_id: str) -> dict:
        product = self._products.get(product_id)
        if product:
            return {"base_price": product.price, "currency": "USD"}
        return None

    async def apply_discount(self, product_id: str, discount_code: str) -> dict:
        product = self._products.get(product_id)
        if not product:
            return {"valid": False, "error": "Product not found"}
        discounts = {"SAVE10": 0.10, "SAVE20": 0.20, "BULK15": 0.15}
        rate = discounts.get(discount_code.upper(), 0)
        return {
            "valid": rate > 0,
            "discount_rate": rate,
            "original_price": product.price,
            "discounted_price": product.price * (1 - rate),
        }


class InMemoryInventoryRepository(InventoryRepository):
    """In-memory inventory repository."""

    def __init__(self):
        self._inventory: Dict[str, Inventory] = {}
        # Initialize with sample data
        for sku, product in SAMPLE_PRODUCTS.items():
            self._inventory[product.id] = Inventory(
                product_id=product.id, sku=sku, quantity=50, reserved=0
            )

    async def get(self, product_id: str) -> Optional[Inventory]:
        return self._inventory.get(product_id)

    async def get_by_sku(self, sku: str) -> Optional[Inventory]:
        for inv in self._inventory.values():
            if inv.sku == sku:
                return inv
        return None

    async def list(self, low_stock_only: bool = False, **filters) -> List[Inventory]:
        items = list(self._inventory.values())
        if low_stock_only:
            items = [i for i in items if i.quantity < i.reorder_point]
        return items

    async def create(self, **data) -> Inventory:
        inv = Inventory(**data)
        self._inventory[inv.product_id] = inv
        return inv

    async def update(self, id: str, **data) -> Inventory:
        if id in self._inventory:
            inv = self._inventory[id]
            for key, value in data.items():
                if hasattr(inv, key):
                    setattr(inv, key, value)
            return inv
        return None

    async def delete(self, id: str) -> bool:
        return self._inventory.pop(id, None) is not None

    async def update_quantity(
        self, product_id: str, quantity_change: int, reason: str = ""
    ) -> Inventory:
        inv = self._inventory.get(product_id)
        if inv:
            inv.quantity += quantity_change
            inv.last_updated = datetime.now().isoformat()
            return inv
        return None

    async def reserve(self, product_id: str, quantity: int) -> bool:
        inv = self._inventory.get(product_id)
        if inv and inv.quantity - inv.reserved >= quantity:
            inv.reserved += quantity
            return True
        return False

    async def release(self, product_id: str, quantity: int) -> bool:
        inv = self._inventory.get(product_id)
        if inv and inv.reserved >= quantity:
            inv.reserved -= quantity
            return True
        return False

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        inv = self._inventory.get(product_id)
        return inv is not None and (inv.quantity - inv.reserved) >= quantity

    async def get_inventory(self, product_id: str):
        """Get inventory for product with flat interface field names."""
        inv = self._inventory.get(product_id)
        if not inv:
            return None
        return _FlatInventory(
            product_id=inv.product_id,
            in_stock=inv.quantity,
            reserved=inv.reserved,
            available=inv.quantity - inv.reserved,
            warehouse_locations=[inv.warehouse_location]
            if inv.warehouse_location
            else [],
        )

    async def update_inventory(self, product_id: str, quantity_change: int):
        """Update inventory quantity with flat interface field names."""
        updated = await self.update_quantity(product_id, quantity_change)
        if not updated:
            return None
        return _FlatInventory(
            product_id=updated.product_id,
            in_stock=updated.quantity,
            reserved=updated.reserved,
            available=updated.quantity - updated.reserved,
            warehouse_locations=[updated.warehouse_location]
            if updated.warehouse_location
            else [],
        )


class InMemoryPricingRepository(PricingRepository):
    """In-memory pricing repository."""

    def __init__(self):
        self._bulk_tiers = [(1000, 0.20), (500, 0.15), (100, 0.10), (20, 0.05)]
        self._coupons = {
            "SAVE10": {"rate": 0.10, "min_order": 50},
            "SAVE20": {"rate": 0.20, "min_order": 100},
            "BULK15": {"rate": 0.15, "min_order": 200},
            "WELCOME": {"rate": 0.05, "min_order": 0},
        }
        self._promotions = [
            {"id": "promo1", "name": "Summer Sale", "discount": 0.15, "active": True},
            {"id": "promo2", "name": "Bulk Discount", "discount": 0.20, "active": True},
        ]

    async def get(self, id: str) -> Optional[Any]:
        return self._coupons.get(id)

    async def list(self, **filters) -> List[Any]:
        return list(self._coupons.values())

    async def create(self, **data) -> Any:
        return data

    async def update(self, id: str, **data) -> Any:
        if id in self._coupons:
            self._coupons[id].update(data)
        return self._coupons.get(id)

    async def delete(self, id: str) -> bool:
        return self._coupons.pop(id, None) is not None

    async def get_bulk_pricing(self, product_id: str, quantity: int) -> dict:
        # Get base price from product
        product = SAMPLE_PRODUCTS.get(product_id) or list(SAMPLE_PRODUCTS.values())[0]
        base_price = product.price if product else 100.0

        discount_rate = 0.0
        for threshold, rate in self._bulk_tiers:
            if quantity >= threshold:
                discount_rate = rate
                break

        unit_price = base_price * (1 - discount_rate)
        return {
            "base_price": base_price,
            "discount_rate": discount_rate,
            "unit_price": unit_price,
            "total": unit_price * quantity,
            "quantity": quantity,
        }

    async def apply_coupon(
        self, coupon_code: str, cart_total: float, customer_id: Optional[str] = None
    ) -> dict:
        coupon = self._coupons.get(coupon_code.upper())
        if not coupon:
            return {"valid": False, "error": "Invalid coupon code"}
        if cart_total < coupon["min_order"]:
            return {
                "valid": False,
                "error": f"Minimum order ${coupon['min_order']} required",
            }
        discount = cart_total * coupon["rate"]
        return {
            "valid": True,
            "discount_rate": coupon["rate"],
            "discount_amount": discount,
            "final_total": cart_total - discount,
        }

    async def get_promotions(self) -> List[dict]:
        return [p for p in self._promotions if p["active"]]

    async def calculate_savings(
        self, original_price: float, discount_rate: float
    ) -> dict:
        savings = original_price * discount_rate
        return {
            "original_price": original_price,
            "discount_rate": discount_rate,
            "savings": savings,
            "final_price": original_price - savings,
        }

    async def validate_coupon(self, coupon_code: str) -> bool:
        return coupon_code.upper() in self._coupons

    async def get_pricing(self, product_id: str, quantity: int = 1) -> dict:
        """Get pricing with bulk discounts (flat interface compatibility)."""
        return await self.get_bulk_pricing(product_id, quantity)

    async def validate_discount_code(self, code: str) -> float:
        """Validate discount code and return rate (flat interface compatibility)."""
        coupon = self._coupons.get(code.upper())
        if coupon:
            return float(coupon.get("rate", 0.0))
        return 0.0


class InMemoryCartRepository(CartRepository):
    """In-memory cart repository."""

    def __init__(self):
        self._carts: Dict[str, Cart] = {}

    async def get(self, cart_id: str) -> Optional[Cart]:
        return self._carts.get(cart_id)

    async def list(self, **filters) -> List[Cart]:
        return list(self._carts.values())

    async def create(self, customer_id: Optional[str] = None, **data) -> Cart:
        cart_id = str(uuid.uuid4())
        cart = Cart(
            id=cart_id,
            customer_id=customer_id,
            items=[],
            created_at=datetime.now().isoformat(),
        )
        self._carts[cart_id] = cart
        return cart

    async def update(self, id: str, **data) -> Cart:
        cart = self._carts.get(id)
        if cart:
            for key, value in data.items():
                if hasattr(cart, key):
                    setattr(cart, key, value)
            cart.updated_at = datetime.now().isoformat()
        return cart

    async def delete(self, id: str) -> bool:
        return self._carts.pop(id, None) is not None

    async def add_item(
        self, cart_id: str, product_id: str, quantity: int, unit_price: float = 0.0
    ):
        """Add item to cart. Returns Cart when called from package interface, dict from flat interface."""
        return await self._add_item_internal(cart_id, product_id, quantity)

    async def remove_item(self, cart_id: str, product_id: str) -> Cart:
        cart = self._carts.get(cart_id)
        if cart:
            cart.items = [i for i in cart.items if i.product_id != product_id]
            self._update_totals(cart)
        return cart

    async def update_item_quantity(
        self, cart_id: str, product_id: str, quantity: int
    ) -> Cart:
        cart = self._carts.get(cart_id)
        if cart:
            for item in cart.items:
                if item.product_id == product_id:
                    item.quantity = quantity
                    item.subtotal = item.quantity * item.unit_price
                    break
            self._update_totals(cart)
        return cart

    async def clear(self, cart_id: str) -> bool:
        cart = self._carts.get(cart_id)
        if cart:
            cart.items = []
            self._update_totals(cart)
            return True
        return False

    async def calculate_total(self, cart_id: str) -> dict:
        cart = self._carts.get(cart_id)
        if not cart:
            return {"error": "Cart not found"}
        self._update_totals(cart)
        return {
            "subtotal": cart.subtotal,
            "tax": cart.tax,
            "shipping": cart.shipping,
            "total": cart.total,
        }

    async def validate(self, cart_id: str) -> dict:
        cart = self._carts.get(cart_id)
        if not cart:
            return {"valid": False, "errors": ["Cart not found"]}
        if not cart.items:
            return {"valid": False, "errors": ["Cart is empty"]}
        return {"valid": True, "item_count": len(cart.items)}

    async def create_cart(self, user_id: str) -> dict:
        """Create new cart (flat interface compatibility)."""
        cart = await self.create(customer_id=user_id)
        return {
            "cart_id": cart.id,
            "user_id": cart.customer_id,
            "created_at": cart.created_at,
            "items": [],
            "total": cart.total,
        }

    async def get_cart(self, cart_id: str):
        """Get cart details (flat interface compatibility)."""
        cart = await self.get(cart_id)
        if not cart:
            return None
        return {
            "cart_id": cart.id,
            "user_id": cart.customer_id,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal,
                }
                for item in cart.items
            ],
            "total": cart.total,
        }

    async def _add_item_internal(
        self, cart_id: str, product_id: str, quantity: int
    ) -> Cart:
        """Internal add_item that returns Cart object."""
        cart = self._carts.get(cart_id)
        if not cart:
            return None

        # Find product
        product = None
        for p in SAMPLE_PRODUCTS.values():
            if p.id == product_id or p.sku == product_id:
                product = p
                break

        if not product:
            return cart

        # Check if item exists
        for item in cart.items:
            if item.product_id == product.id:
                item.quantity += quantity
                item.subtotal = item.quantity * item.unit_price
                self._update_totals(cart)
                return cart

        # Add new item
        item = CartItem(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            quantity=quantity,
            unit_price=product.price,
            subtotal=product.price * quantity,
        )
        cart.items.append(item)
        self._update_totals(cart)
        return cart

    async def get_items(self, cart_id: str) -> list:
        """Get all items in cart (flat interface compatibility)."""
        cart = await self.get(cart_id)
        if not cart:
            return []
        return [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
            for item in cart.items
        ]

    def _update_totals(self, cart: Cart):
        cart.subtotal = sum(item.subtotal for item in cart.items)
        cart.tax = cart.subtotal * 0.08  # 8% tax
        cart.shipping = 50.0 if cart.subtotal > 0 else 0  # Flat $50 shipping
        cart.total = cart.subtotal + cart.tax + cart.shipping


class InMemoryOrderRepository(OrderRepository):
    """In-memory order repository."""

    def __init__(self):
        self._orders: Dict[str, Order] = {}

    async def get(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def list(
        self, customer_id: Optional[str] = None, status: Optional[str] = None, **filters
    ) -> List[Order]:
        orders = list(self._orders.values())
        if customer_id:
            orders = [o for o in orders if o.customer_id == customer_id]
        if status:
            orders = [o for o in orders if o.status == status]
        return orders

    async def create(
        self,
        cart_id: str,
        customer_id: str,
        shipping_address: dict,
        billing_address: Optional[dict] = None,
        **data,
    ) -> Order:
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        order = Order(
            id=order_id,
            customer_id=customer_id,
            status="confirmed",
            shipping_address=shipping_address,
            billing_address=billing_address or shipping_address,
            tracking_number=f"TRK{uuid.uuid4().hex[:10].upper()}",
            created_at=datetime.now().isoformat(),
            **data,
        )
        self._orders[order_id] = order
        return order

    async def update(self, id: str, **data) -> Order:
        order = self._orders.get(id)
        if order:
            for key, value in data.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            order.updated_at = datetime.now().isoformat()
        return order

    async def delete(self, id: str) -> bool:
        return self._orders.pop(id, None) is not None

    async def update_status(self, order_id: str, status: str) -> Order:
        return await self.update(order_id, status=status)

    async def cancel(self, order_id: str, reason: str = "") -> bool:
        order = self._orders.get(order_id)
        if order and order.status not in ["shipped", "delivered"]:
            order.status = "cancelled"
            return True
        return False

    async def get_by_customer(self, customer_id: str, limit: int = 10) -> List[Order]:
        orders = [o for o in self._orders.values() if o.customer_id == customer_id]
        return orders[:limit]

    async def create_order(
        self,
        cart_id: str,
        user_id: str,
        shipping_address: str,
        items=None,
        subtotal=None,
        tax=None,
        shipping_cost=None,
        total=None,
    ) -> dict:
        """Create order from cart (flat interface compatibility)."""
        order = await self.create(
            cart_id=cart_id,
            customer_id=user_id,
            shipping_address={"address": shipping_address},
        )
        return {
            "order_id": order.id,
            "cart_id": cart_id,
            "user_id": user_id,
            "status": order.status,
            "created_at": order.created_at,
            "shipping_address": shipping_address,
            "tracking_number": order.tracking_number,
            "items": items or [],
        }

    async def get_order(self, order_id: str):
        """Get order details (flat interface compatibility)."""
        order = await self.get(order_id)
        if not order:
            return None
        return {
            "order_id": order.id,
            "status": order.status,
            "created_at": order.created_at,
            "shipping_address": order.shipping_address,
            "tracking_number": order.tracking_number,
        }


class InMemoryShippingRepository(ShippingRepository):
    """In-memory shipping repository."""

    def __init__(self):
        self._methods = [
            {
                "id": "standard",
                "name": "Standard Shipping",
                "price": 9.99,
                "days": "5-7",
            },
            {
                "id": "express",
                "name": "Express Shipping",
                "price": 19.99,
                "days": "2-3",
            },
            {
                "id": "overnight",
                "name": "Overnight Shipping",
                "price": 39.99,
                "days": "1",
            },
        ]
        self._tracking: Dict[str, dict] = {}

    async def get(self, id: str) -> Optional[Any]:
        for method in self._methods:
            if method["id"] == id:
                return method
        return None

    async def list(self, **filters) -> List[Any]:
        return self._methods

    async def create(self, **data) -> Any:
        return data

    async def update(self, id: str, **data) -> Any:
        return data

    async def delete(self, id: str) -> bool:
        return True

    async def calculate_shipping(
        self, origin: str, destination: str, weight_lbs: float
    ) -> dict:
        base_rates = {"standard": 9.99, "express": 19.99, "overnight": 39.99}
        # Weight surcharge
        weight_surcharge = max(0, (weight_lbs - 5) * 0.50)
        return {
            "origin": origin,
            "destination": destination,
            "weight_lbs": weight_lbs,
            "options": [
                {
                    "method": "standard",
                    "price": base_rates["standard"] + weight_surcharge,
                    "days": "5-7",
                },
                {
                    "method": "express",
                    "price": base_rates["express"] + weight_surcharge,
                    "days": "2-3",
                },
                {
                    "method": "overnight",
                    "price": base_rates["overnight"] + weight_surcharge,
                    "days": "1",
                },
            ],
        }

    async def get_shipping_methods(self) -> List[dict]:
        return self._methods

    async def track_shipment(self, tracking_number: str) -> dict:
        if tracking_number in self._tracking:
            return self._tracking[tracking_number]
        # Generate mock tracking
        return {
            "tracking_number": tracking_number,
            "status": "in_transit",
            "location": "Distribution Center",
            "events": [
                {"date": datetime.now().isoformat(), "status": "Package picked up"},
                {
                    "date": (datetime.now() - timedelta(hours=12)).isoformat(),
                    "status": "In transit",
                },
            ],
        }

    async def estimate_delivery(self, destination: str, shipping_method: str) -> dict:
        days_map = {"standard": 6, "express": 3, "overnight": 1}
        days = days_map.get(shipping_method, 5)
        delivery_date = datetime.now() + timedelta(days=days)
        return {
            "destination": destination,
            "shipping_method": shipping_method,
            "estimated_delivery": delivery_date.strftime("%Y-%m-%d"),
            "business_days": days,
        }

    async def validate_address(self, address: str) -> bool:
        return len(address) >= 10


class InMemoryCustomerRepository(CustomerRepository):
    """In-memory customer repository."""

    def __init__(self):
        self._customers: Dict[str, dict] = {}
        self._preferences: Dict[str, dict] = {}
        self._history: Dict[str, List[dict]] = {}

    async def get(self, id: str) -> Optional[Any]:
        return self._customers.get(id)

    async def list(self, **filters) -> List[Any]:
        return list(self._customers.values())

    async def create(self, **data) -> Any:
        customer_id = data.get("id", str(uuid.uuid4()))
        self._customers[customer_id] = data
        return data

    async def update(self, id: str, **data) -> Any:
        if id in self._customers:
            self._customers[id].update(data)
        return self._customers.get(id)

    async def delete(self, id: str) -> bool:
        return self._customers.pop(id, None) is not None

    async def get_customer_history(self, user_id: str, limit: int = 10) -> dict:
        orders = self._history.get(user_id, [])
        return {
            "user_id": user_id,
            "order_count": len(orders),
            "orders": orders[:limit],
            "total_spent": sum(o.get("total", 0) for o in orders),
        }

    async def get_customer_preferences(self, user_id: str) -> dict:
        prefs = self._preferences.get(user_id, {})
        return {
            "user_id": user_id,
            "preferences": prefs,
            "shipping_preference": prefs.get("shipping", "standard"),
            "notification_enabled": prefs.get("notifications", True),
        }

    async def save_customer_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> dict:
        self._preferences[user_id] = preferences
        return {"user_id": user_id, "preferences": preferences, "saved": True}

    async def customer_exists(self, user_id: str) -> bool:
        return user_id in self._customers

    async def get_customer_value(self, user_id: str) -> float:
        orders = self._history.get(user_id, [])
        return sum(o.get("total", 0) for o in orders)


class InMemoryRFQRepository(RFQRepository):
    """In-memory RFQ repository."""

    def __init__(self):
        self._rfqs: Dict[str, dict] = {}

    async def get(self, id: str) -> Optional[Any]:
        return self._rfqs.get(id)

    async def list(self, **filters) -> List[Any]:
        return list(self._rfqs.values())

    async def create(self, **data) -> Any:
        rfq_id = f"RFQ-{uuid.uuid4().hex[:8].upper()}"
        rfq = {
            "id": rfq_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            **data,
        }
        self._rfqs[rfq_id] = rfq
        return rfq

    async def update(self, id: str, **data) -> Any:
        if id in self._rfqs:
            self._rfqs[id].update(data)
        return self._rfqs.get(id)

    async def delete(self, id: str) -> bool:
        return self._rfqs.pop(id, None) is not None

    async def create_rfq(
        self,
        customer_name: str,
        customer_email: str,
        items: list,
        special_requirements: Optional[str] = None,
    ) -> dict:
        # Calculate estimated quote
        total = sum(item.get("quantity", 1) * 100 for item in items)  # Mock pricing
        discount = 0.15 if total > 1000 else 0.10 if total > 500 else 0.05
        quoted_total = total * (1 - discount)

        rfq = await self.create(
            customer_name=customer_name,
            customer_email=customer_email,
            items=items,
            special_requirements=special_requirements,
            original_total=total,
            discount_rate=discount,
            quoted_total=quoted_total,
        )
        return rfq

    async def get_rfq_status(self, rfq_id: str) -> dict:
        rfq = self._rfqs.get(rfq_id)
        if not rfq:
            return {"error": "RFQ not found"}
        return {
            "rfq_id": rfq_id,
            "status": rfq.get("status"),
            "quoted_total": rfq.get("quoted_total"),
            "expires_at": rfq.get("expires_at"),
        }

    async def accept_rfq(
        self, rfq_id: str, purchase_order_number: Optional[str] = None
    ) -> dict:
        rfq = self._rfqs.get(rfq_id)
        if not rfq:
            return {"error": "RFQ not found"}
        if rfq["status"] != "pending":
            return {"error": f"RFQ is {rfq['status']}, cannot accept"}
        rfq["status"] = "accepted"
        rfq["accepted_at"] = datetime.now().isoformat()
        rfq["purchase_order_number"] = purchase_order_number
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        return {
            "rfq_id": rfq_id,
            "status": "accepted",
            "order_id": order_id,
            "purchase_order_number": purchase_order_number,
            "total": rfq.get("quoted_total"),
        }

    async def rfq_exists(self, rfq_id: str) -> bool:
        return rfq_id in self._rfqs

    async def get_customer_rfqs(self, customer_email: str) -> List[dict]:
        return [
            r for r in self._rfqs.values() if r.get("customer_email") == customer_email
        ]
