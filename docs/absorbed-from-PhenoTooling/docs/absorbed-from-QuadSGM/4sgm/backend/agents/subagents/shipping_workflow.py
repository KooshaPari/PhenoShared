"""Shipping management StateGraph subagent."""

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class ShippingState(TypedDict):
    """Shipping management state."""

    messages: Annotated[list[AnyMessage], "Chat messages"]
    order_id: Annotated[str, "Order identifier"]
    status: Annotated[str, "Shipping status"]
    address: Annotated[dict, "Shipping address"]
    carrier: Annotated[str, "Shipping carrier"]
    tracking_number: Annotated[str, "Tracking number"]
    cost: Annotated[float, "Shipping cost"]


def create_graph() -> StateGraph:
    """
    Create ShippingWorkflow StateGraph for managing shipments.

    Returns:
        Compiled StateGraph for shipping management.
    """

    def validate_address(state: ShippingState) -> ShippingState:
        """Validate shipping address."""
        address = state.get("address", {})
        logger.info(f"Validating address: {address.get('zip_code')}")

        required_fields = ["street", "city", "state", "zip_code", "country"]
        if not all(address.get(field) for field in required_fields):
            state["status"] = "address_invalid"
            return state

        state["status"] = "address_validated"
        return state

    def select_carrier(state: ShippingState) -> ShippingState:
        """Select shipping carrier based on destination."""
        address = state.get("address", {})
        logger.info(f"Selecting carrier for {address.get('country')}")

        # Simple carrier selection logic
        country = address.get("country", "").lower()
        if country == "usa":
            state["carrier"] = "UPS"
        elif country == "canada":
            state["carrier"] = "Canada Post"
        else:
            state["carrier"] = "DHL"

        state["status"] = "carrier_selected"
        return state

    def calculate_shipping(state: ShippingState) -> ShippingState:
        """Calculate shipping cost."""
        carrier = state.get("carrier", "Unknown")
        logger.info(f"Calculating shipping cost with {carrier}")

        # Simplified cost calculation
        state["cost"] = 15.0

        state["status"] = "cost_calculated"
        return state

    def generate_label(state: ShippingState) -> ShippingState:
        """Generate shipping label."""
        order_id = state.get("order_id", "UNKNOWN")
        carrier = state.get("carrier", "Unknown")
        logger.info(f"Generating label for {order_id} with {carrier}")

        # Generate tracking number
        state["tracking_number"] = f"{carrier[:2].upper()}-{order_id}-TRACK"
        state["status"] = "label_generated"
        return state

    def schedule_pickup(state: ShippingState) -> ShippingState:
        """Schedule carrier pickup."""
        tracking_number = state.get("tracking_number", "")
        logger.info(f"Scheduling pickup for {tracking_number}")

        state["status"] = "pickup_scheduled"
        return state

    # Build graph
    graph = StateGraph(ShippingState)

    # Add nodes
    graph.add_node("validate", validate_address)
    graph.add_node("select_carrier", select_carrier)
    graph.add_node("calculate", calculate_shipping)
    graph.add_node("label", generate_label)
    graph.add_node("schedule", schedule_pickup)

    # Define edges
    graph.set_entry_point("validate")
    graph.add_edge("validate", "select_carrier")
    graph.add_edge("select_carrier", "calculate")
    graph.add_edge("calculate", "label")
    graph.add_edge("label", "schedule")
    graph.add_edge("schedule", END)

    return graph


def compile() -> object:
    """Compile and return ready-to-run shipping workflow."""
    graph = create_graph()
    return graph.compile()
