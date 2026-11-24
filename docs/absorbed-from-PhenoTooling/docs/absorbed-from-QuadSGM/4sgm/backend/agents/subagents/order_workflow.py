"""Order processing StateGraph subagent."""

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class OrderState(TypedDict):
    """Order processing state."""

    messages: Annotated[list[AnyMessage], "Chat messages"]
    order_id: Annotated[str, "Order identifier"]
    customer_id: Annotated[str, "Customer identifier"]
    status: Annotated[str, "Current order status"]
    items: Annotated[list[dict], "Order items"]
    total: Annotated[float, "Order total amount"]


def create_graph() -> StateGraph:
    """
    Create OrderWorkflow StateGraph for processing orders.

    Returns:
        Compiled StateGraph for order processing.
    """

    def initialize_order(state: OrderState) -> OrderState:
        """Initialize order processing."""
        logger.info(f"Initializing order: {state.get('order_id')}")
        state["status"] = "initialized"
        return state

    def validate_items(state: OrderState) -> OrderState:
        """Validate order items."""
        items = state.get("items", [])
        logger.info(f"Validating {len(items)} items")

        # Check for invalid items
        if not items:
            state["status"] = "validation_failed"
            return state

        for item in items:
            if not item.get("sku") or not item.get("quantity"):
                state["status"] = "validation_failed"
                return state

        state["status"] = "items_validated"
        return state

    def calculate_total(state: OrderState) -> OrderState:
        """Calculate order total."""
        items = state.get("items", [])
        total = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)
        state["total"] = total
        logger.info(f"Calculated order total: ${total}")
        state["status"] = "total_calculated"
        return state

    def process_payment(state: OrderState) -> OrderState:
        """Process payment (simplified)."""
        total = state.get("total", 0)
        logger.info(f"Processing payment: ${total}")

        if total <= 0:
            state["status"] = "payment_failed"
            return state

        state["status"] = "payment_processed"
        return state

    def confirm_order(state: OrderState) -> OrderState:
        """Confirm order creation."""
        logger.info(f"Confirming order: {state.get('order_id')}")
        state["status"] = "confirmed"
        return state

    # Build graph
    graph = StateGraph(OrderState)

    # Add nodes
    graph.add_node("initialize", initialize_order)
    graph.add_node("validate", validate_items)
    graph.add_node("calculate", calculate_total)
    graph.add_node("payment", process_payment)
    graph.add_node("confirm", confirm_order)

    # Define edges
    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "validate")
    graph.add_edge("validate", "calculate")
    graph.add_edge("calculate", "payment")
    graph.add_edge("payment", "confirm")
    graph.add_edge("confirm", END)

    return graph


def compile() -> object:
    """Compile and return ready-to-run order workflow."""
    graph = create_graph()
    return graph.compile()
