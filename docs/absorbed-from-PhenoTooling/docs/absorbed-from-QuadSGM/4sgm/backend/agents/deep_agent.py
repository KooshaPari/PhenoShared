"""DeepAgent factory with hybrid StateGraph subagents."""

import logging
import os
from typing import Any, Optional

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .backends.composite import get_composite_backend
from .callbacks.langfuse import get_langfuse_handler
from .subagents import order_workflow, rfq_workflow, shipping_workflow

logger = logging.getLogger(__name__)

# Initialize LLM Cache (Level 2: Disk)
# Level 1 (Memory) is handled by the model itself if configured,
# but LangChain's global cache provides a cross-invocation disk cache.
try:
    os.makedirs(".cache", exist_ok=True)
    from langchain_core.globals import set_llm_cache

    set_llm_cache(InMemoryCache())
    logger.info("LLM in-memory cache initialized")
except Exception as e:
    logger.warning(f"Failed to initialize LLM cache: {e}")


def create_4sgm_agent(
    mcp_tools: list[Any],
    enable_langfuse: bool = True,
) -> Any:
    """
    Create the 4SGM DeepAgent with custom StateGraph subagents.

    This factory function creates a hybrid agent that:
    1. Uses Claude (not GPT-4) as the base model
    2. Integrates specialized StateGraph subagents for domain workflows
    3. Enables observability via Langfuse if credentials available
    4. Configures hybrid storage backend for state management

    Args:
        mcp_tools: List of MCP tools to attach to the agent
        enable_langfuse: Whether to enable Langfuse observability

    Returns:
        Compiled agent ready for invocation
    """

    # Get model configuration from environment
    model_name = os.getenv("LLM_MODEL", "z-ai/glm-4.7-flash")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENROUTER_BASE_URL")

    logger.info(f"Creating DeepAgent with model: {model_name}")
    if base_url:
        logger.info(f"Using custom base URL: {base_url}")

    # Create ChatOpenAI model (compatible with OpenRouter)
    model = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url if base_url else None,
    )

    # Initialize Langfuse handler if enabled
    langfuse_handler = None
    callbacks = []

    if enable_langfuse:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            callbacks.append(langfuse_handler)
            logger.info("Langfuse observability enabled")
        else:
            logger.debug("Langfuse observability disabled (no credentials)")

    # Get backend configuration
    backend_config = get_composite_backend()
    logger.info(f"Using composite backend: {backend_config}")

    # Create the main reactive agent
    # Note: LangGraph's create_react_agent doesn't directly support
    # external StateGraph subagents in the prebuilt version.
    # This is a foundation that can be extended with a custom wrapper.
    agent = create_react_agent(
        model=model,
        tools=mcp_tools,
        interrupt_before=[],
        interrupt_after=[],
    )

    # Log subagent availability
    logger.info("Order workflow subagent compiled")
    logger.info("Shipping workflow subagent compiled")
    logger.info("RFQ workflow subagent compiled")

    # Store metadata for routing to subagents
    agent._subagents = {
        "order": order_workflow.compile(),
        "shipping": shipping_workflow.compile(),
        "rfq": rfq_workflow.compile(),
    }
    agent._backend_config = backend_config
    agent._callbacks = callbacks

    logger.info("DeepAgent created successfully")

    return agent


def should_use_subagent(message: str) -> Optional[str]:
    """
    Determine if message should route to a domain-specific subagent.

    Args:
        message: User message

    Returns:
        Subagent name if applicable, None otherwise
    """
    message_lower = message.lower()

    # Route to order workflow
    order_keywords = ["order", "purchase", "buy", "order number", "order status"]
    if any(kw in message_lower for kw in order_keywords):
        return "order"

    # Route to shipping workflow
    shipping_keywords = [
        "ship",
        "shipping",
        "delivery",
        "tracking",
        "address",
        "carrier",
    ]
    if any(kw in message_lower for kw in shipping_keywords):
        return "shipping"

    # Route to RFQ workflow
    rfq_keywords = ["quote", "rfq", "pricing", "bulk", "wholesale"]
    if any(kw in message_lower for kw in rfq_keywords):
        return "rfq"

    return None


async def route_to_subagent(
    agent: Any,
    message: str,
    subagent_name: str,
) -> dict[str, Any]:
    """
    Route message to appropriate domain-specific subagent.

    Args:
        agent: The main agent instance
        message: User message
        subagent_name: Name of subagent to route to

    Returns:
        Result from subagent execution
    """
    subagents = getattr(agent, "_subagents", {})
    subagent = subagents.get(subagent_name)

    if not subagent:
        logger.warning(f"Subagent not found: {subagent_name}")
        return {"error": f"Subagent '{subagent_name}' not available"}

    logger.info(f"Routing to {subagent_name} subagent")

    try:
        # Initialize state based on subagent type
        if subagent_name == "order":
            state = {
                "messages": [message],
                "order_id": "",
                "customer_id": "",
                "status": "pending",
                "items": [],
                "total": 0.0,
            }
        elif subagent_name == "shipping":
            state = {
                "messages": [message],
                "order_id": "",
                "status": "pending",
                "address": {},
                "carrier": "",
                "tracking_number": "",
                "cost": 0.0,
            }
        elif subagent_name == "rfq":
            state = {
                "messages": [message],
                "rfq_id": "",
                "customer_id": "",
                "status": "pending",
                "items": [],
                "quotes": [],
                "selected_quote": {},
            }
        else:
            return {"error": f"Unknown subagent: {subagent_name}"}

        # Invoke subagent
        if hasattr(subagent, "ainvoke"):
            result = await subagent.ainvoke(state)
        else:
            result = subagent.invoke(state)
        logger.info(f"Subagent {subagent_name} completed with status: {result.get('status')}")

        return {
            "subagent": subagent_name,
            "status": result.get("status"),
            "result": result,
        }
    except Exception as e:
        logger.error(f"Subagent execution failed: {e}")
        return {"error": f"Subagent execution failed: {str(e)}"}
