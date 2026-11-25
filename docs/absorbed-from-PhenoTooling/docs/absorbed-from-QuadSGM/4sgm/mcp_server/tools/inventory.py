"""Inventory management tools for 4SGM MCP server."""

import logging
from datetime import datetime, timezone

from ..models import InventoryResponse, UpdateInventoryResponse
from ..exceptions import (
    InventoryNotFoundError,
    InsufficientInventoryError,
    InventoryError,
)
from ..repositories import InventoryRepository

logger = logging.getLogger(__name__)


def register_inventory_tools(mcp, inventory_repo: InventoryRepository):
    """Register inventory tools with the FastMCP instance."""

    @mcp.tool
    async def get_inventory(product_id: str) -> dict:
        """Check product inventory levels.

        Retrieves current stock status including total stock, reserved quantity,
        available units, and warehouse locations.

        Args:
            product_id: The product identifier

        Returns:
            InventoryResponse with stock details (in_stock, reserved, available,
            warehouse_locations).

        Raises:
            InventoryNotFoundError: If product inventory not found
            InventoryError: If inventory lookup fails
        """
        try:
            if not inventory_repo:
                raise InventoryError("Inventory repository not initialized")

            inventory = await inventory_repo.get_inventory(product_id)
            if not inventory:
                raise InventoryNotFoundError(
                    f"Inventory for product {product_id} not found"
                )

            response = InventoryResponse(
                product_id=inventory.product_id,
                in_stock=inventory.in_stock,
                reserved=inventory.reserved,
                available=inventory.available,
                warehouse_locations=inventory.warehouse_locations,
            )
            return response.model_dump()

        except InventoryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching inventory for {product_id}: {str(e)}")
            raise InventoryError(f"Failed to fetch inventory: {str(e)}")

    @mcp.tool
    async def update_inventory(product_id: str, quantity: int) -> dict:
        """Update product inventory quantity.

        Adds or removes stock from inventory. Positive numbers add stock,
        negative numbers reduce stock.

        Args:
            product_id: The product identifier
            quantity: Quantity change (positive or negative integer)

        Returns:
            UpdateInventoryResponse with updated inventory status and timestamp.

        Raises:
            InventoryNotFoundError: If product doesn't exist
            InsufficientInventoryError: If attempting to reduce below zero
            InventoryError: If update fails
        """
        try:
            if not inventory_repo:
                raise InventoryError("Inventory repository not initialized")

            if quantity == 0:
                raise InventoryError("Quantity change must be non-zero")

            inventory = await inventory_repo.update_inventory(product_id, quantity)
            if not inventory:
                raise InventoryNotFoundError(f"Product {product_id} not found")

            response = UpdateInventoryResponse(
                product_id=inventory.product_id,
                quantity_updated=quantity,
                new_total=inventory.in_stock,  # BaseInventory.in_stock maps from quantity
                timestamp=datetime.now(timezone.utc),
            )
            return response.model_dump()

        except (InventoryNotFoundError, InsufficientInventoryError):
            raise
        except Exception as e:
            logger.error(f"Error updating inventory for {product_id}: {str(e)}")
            raise InventoryError(f"Failed to update inventory: {str(e)}")
