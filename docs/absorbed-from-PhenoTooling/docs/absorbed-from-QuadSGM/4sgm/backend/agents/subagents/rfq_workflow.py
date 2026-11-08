"""RFQ (Request For Quote) processing StateGraph subagent."""

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


class RFQState(TypedDict):
    """RFQ processing state."""

    messages: Annotated[list[AnyMessage], "Chat messages"]
    rfq_id: Annotated[str, "RFQ identifier"]
    customer_id: Annotated[str, "Customer identifier"]
    status: Annotated[str, "RFQ status"]
    items: Annotated[list[dict], "Requested items"]
    quotes: Annotated[list[dict], "Generated quotes"]
    selected_quote: Annotated[dict, "Selected quote"]


def create_graph() -> StateGraph:
    """
    Create RFQWorkflow StateGraph for quote processing.

    Returns:
        Compiled StateGraph for RFQ management.
    """

    def parse_request(state: RFQState) -> RFQState:
        """Parse RFQ request."""
        rfq_id = state.get("rfq_id", "UNKNOWN")
        logger.info(f"Parsing RFQ request: {rfq_id}")

        items = state.get("items", [])
        if not items:
            state["status"] = "parsing_failed"
            return state

        state["status"] = "request_parsed"
        return state

    def check_inventory(state: RFQState) -> RFQState:
        """Check inventory availability."""
        items = state.get("items", [])
        logger.info(f"Checking inventory for {len(items)} items")

        for item in items:
            # Mark available quantity (simplified)
            item["available"] = item.get("quantity", 0)

        state["status"] = "inventory_checked"
        return state

    def generate_quotes(state: RFQState) -> RFQState:
        """Generate pricing quotes."""
        items = state.get("items", [])
        logger.info(f"Generating quotes for {len(items)} items")

        quotes = []
        total_price = 0

        for item in items:
            unit_price = item.get("base_price", 0) * (1 - 0.1)  # 10% bulk discount
            item_total = unit_price * item.get("quantity", 0)
            total_price += item_total

            quotes.append(
                {
                    "sku": item.get("sku"),
                    "unit_price": unit_price,
                    "quantity": item.get("quantity"),
                    "subtotal": item_total,
                }
            )

        state["quotes"] = quotes
        state["status"] = "quotes_generated"
        logger.info(f"Generated quote total: ${total_price}")

        return state

    def apply_discounts(state: RFQState) -> RFQState:
        """Apply volume and customer discounts."""
        quotes = state.get("quotes", [])
        logger.info(f"Applying discounts to {len(quotes)} line items")

        total = sum(q.get("subtotal", 0) for q in quotes)

        # Volume discount
        if total > 1000:
            discount_rate = 0.15
        elif total > 500:
            discount_rate = 0.10
        else:
            discount_rate = 0.05

        for quote in quotes:
            quote["discount"] = discount_rate
            quote["final_price"] = quote.get("subtotal", 0) * (1 - discount_rate)

        state["status"] = "discounts_applied"
        return state

    def format_quote(state: RFQState) -> RFQState:
        """Format final quote."""
        quotes = state.get("quotes", [])
        rfq_id = state.get("rfq_id", "UNKNOWN")

        logger.info(f"Formatting final quote for {rfq_id}")

        final_quote = {
            "rfq_id": rfq_id,
            "line_items": quotes,
            "total": sum(q.get("final_price", 0) for q in quotes),
            "valid_until": "2025-12-26",  # 7 days
        }

        state["selected_quote"] = final_quote
        state["status"] = "quote_ready"
        return state

    # Build graph
    graph = StateGraph(RFQState)

    # Add nodes
    graph.add_node("parse", parse_request)
    graph.add_node("inventory", check_inventory)
    graph.add_node("quote", generate_quotes)
    graph.add_node("discount", apply_discounts)
    graph.add_node("format", format_quote)

    # Define edges
    graph.set_entry_point("parse")
    graph.add_edge("parse", "inventory")
    graph.add_edge("inventory", "quote")
    graph.add_edge("quote", "discount")
    graph.add_edge("discount", "format")
    graph.add_edge("format", END)

    return graph


def compile() -> object:
    """Compile and return ready-to-run RFQ workflow."""
    graph = create_graph()
    return graph.compile()
