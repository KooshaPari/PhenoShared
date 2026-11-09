"""Clean FastAPI + LangGraph + MCP Server with DeepAgent architecture."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel

from agents.deep_agent import create_4sgm_agent, route_to_subagent, should_use_subagent

load_dotenv()  # Load .env file

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global state
mcp_client: Optional[MultiServerMCPClient] = None
mcp_tools: list = []
agent: Optional[object] = None


async def init_mcp():
    """Initialize MCP client connection."""
    global mcp_client, mcp_tools

    try:
        # Get the project root (parent of backend directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Create MCP client that connects to running MCP server
        # Use PYTHONPATH to ensure the mcp_server module is found
        mcp_client = MultiServerMCPClient(
            {
                "4sgm": {
                    "command": "python",
                    "args": ["-m", "mcp_server.server"],
                    "transport": "stdio",
                    "env": {
                        "PYTHONPATH": project_root,
                        "PATH": os.environ.get("PATH", ""),
                    },
                }
            }
        )

        # Load tools from MCP server
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"✅ Loaded {len(mcp_tools)} MCP tools")
        return True
    except Exception as e:
        logger.warning(f"⚠️  MCP not available: {e}")
        logger.info("💡 Start MCP server with: 4sgm mcp")
        return False


async def close_mcp():
    """Close MCP connection."""
    global mcp_client
    try:
        if mcp_client:
            # MultiServerMCPClient doesn't have a close method
            # It will be cleaned up by garbage collection
            logger.info("✅ MCP cleanup")
    except Exception as e:
        logger.error(f"Error closing MCP: {e}")


async def init_agent():
    """Initialize DeepAgent with MCP tools."""
    global agent, mcp_tools
    try:
        if mcp_tools and not agent:
            agent = create_4sgm_agent(mcp_tools)
            logger.info(f"✅ DeepAgent initialized with {len(mcp_tools)} tools")
            return True
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        return False
    return agent is not None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    logger.info("🚀 FastAPI starting with DeepAgent...")

    # Try to initialize MCP on startup
    mcp_initialized = await init_mcp()
    if mcp_initialized:
        logger.info("✅ MCP connected and ready")
        agent_initialized = await init_agent()
        if agent_initialized:
            logger.info("✅ DeepAgent initialized and ready")
        else:
            logger.warning("⚠️  DeepAgent initialization failed")
    else:
        logger.warning("⚠️  MCP not available - will retry on first request")

    yield

    await close_mcp()
    logger.info("🛑 FastAPI shutting down...")


# Create app
app = FastAPI(
    title="4SGM API",
    description="LangGraph + MCP Server",
    lifespan=lifespan,
)


# Models
class Message(BaseModel):
    """Chat message."""

    text: str
    session_id: Optional[str] = None


class Response(BaseModel):
    """Chat response."""

    text: str
    session_id: str


# Endpoints
@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "mcp": mcp_client is not None,
        "tools": len(mcp_tools),
    }


@app.get("/tools")
async def list_tools():
    """List MCP tools."""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="Tools not loaded")

    return {
        "count": len(mcp_tools),
        "tools": [{"name": t.name, "description": t.description} for t in mcp_tools],
    }


@app.post("/api/session")
async def create_session():
    """Create a new session."""
    import uuid

    session_id = str(uuid.uuid4())
    return {
        "sessionId": session_id,
        "createdAt": "2025-11-16T23:31:15Z",
        "messages": [],
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session by ID."""
    return {
        "sessionId": session_id,
        "createdAt": "2025-11-16T23:31:15Z",
        "messages": [],
    }


@app.post("/chat")
async def chat(msg: Message):
    """Chat with DeepAgent."""
    global mcp_tools, agent

    # Lazy-load MCP tools and agent on first request
    if not mcp_tools:
        logger.info("🔄 Initializing MCP on first request...")
        await init_mcp()

    if not agent:
        logger.info("🔄 Initializing DeepAgent on first request...")
        await init_agent()

    if not agent:
        raise HTTPException(
            status_code=503, detail="Agent not ready - start MCP server with: 4sgm mcp"
        )

    try:
        # Check if message should route to a subagent
        subagent_name = should_use_subagent(msg.text)
        if subagent_name:
            logger.info(f"Routing to {subagent_name} subagent")
            subagent_result = await route_to_subagent(agent, msg.text, subagent_name)

            if "error" in subagent_result:
                response_text = f"Subagent error: {subagent_result['error']}"
            else:
                response_text = (
                    f"Request processed by {subagent_name} workflow. "
                    f"Status: {subagent_result.get('status', 'unknown')}"
                )
        else:
            # Use main agent for general queries
            result = await agent.ainvoke({"messages": [{"type": "human", "content": msg.text}]})

            response_text = (
                result.get("messages", [])[-1].content if result.get("messages") else "No response"
            )

        return Response(
            text=response_text,
            session_id=msg.session_id or "default",
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(msg: Message):
    """Streaming chat with DeepAgent."""
    global mcp_tools, agent

    if not mcp_tools:
        raise HTTPException(status_code=503, detail="Tools not loaded")

    if not agent:
        await init_agent()

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    async def generate():
        try:
            subagent_name = should_use_subagent(msg.text)

            if subagent_name:
                # Subagent routing (non-streaming for now)
                subagent_result = await route_to_subagent(agent, msg.text, subagent_name)
                if "error" in subagent_result:
                    yield f"data: {{'error': '{subagent_result['error']}'}}\n\n"
                else:
                    yield f"data: {subagent_result}\n\n"
            else:
                # Stream from main agent
                async for event in agent.astream(
                    {"messages": [{"type": "human", "content": msg.text}]}
                ):
                    yield f"data: {event}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {{'error': '{str(e)}'}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/stream-chat")
async def stream_chat_sse(
    message: str,
    session_id: str = "default",
    _conversation_history: str = "[]",  # Reserved for future use
):
    """SSE streaming chat endpoint for frontend.

    Query Parameters:
        message: User's message
        session_id: Session identifier
        conversation_history: JSON string of previous messages
    """
    import json

    global mcp_tools, agent

    # Lazy-load MCP tools and agent on first request
    if not mcp_tools:
        logger.info("🔄 Initializing MCP on first request...")
        await init_mcp()

    if not agent:
        logger.info("🔄 Initializing DeepAgent on first request...")
        await init_agent()

    async def generate():
        try:
            # Send metadata event
            metadata = {"type": "metadata", "session_id": session_id, "document_count": 0}
            yield f"data: {json.dumps(metadata)}\n\n"

            if not agent:
                error_event = {
                    "type": "error",
                    "message": "Agent not ready - MCP server may not be running",
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return

            # Check if message should route to a subagent
            subagent_name = should_use_subagent(message)
            response_text = ""
            token_count = 0

            if subagent_name:
                logger.info(f"Routing to {subagent_name} subagent")
                subagent_result = await route_to_subagent(agent, message, subagent_name)

                if "error" in subagent_result:
                    response_text = f"Error: {subagent_result['error']}"
                else:
                    response_text = (
                        f"Request processed by {subagent_name} workflow. "
                        f"Status: {subagent_result.get('status', 'unknown')}"
                    )

                # Send as single token for subagent responses
                token_event = {
                    "type": "token",
                    "data": response_text,
                    "token_count": len(response_text.split()),
                }
                yield f"data: {json.dumps(token_event)}\n\n"
                token_count = len(response_text.split())
            else:
                # Stream from main agent
                async for event in agent.astream(
                    {"messages": [{"type": "human", "content": message}]}
                ):
                    # Extract content from event
                    if hasattr(event, "get") and event.get("messages"):
                        for msg in event["messages"]:
                            if hasattr(msg, "content"):
                                chunk = msg.content
                                response_text += chunk
                                token_count += 1
                                token_event = {
                                    "type": "token",
                                    "data": chunk,
                                    "token_count": token_count,
                                }
                                yield f"data: {json.dumps(token_event)}\n\n"
                    else:
                        # Fallback: stringify event
                        chunk = str(event)
                        response_text += chunk
                        token_count += 1
                        token_event = {"type": "token", "data": chunk, "token_count": token_count}
                        yield f"data: {json.dumps(token_event)}\n\n"

            # Send complete event
            complete_event = {
                "type": "complete",
                "message": response_text,
                "token_count": token_count,
                "character_count": len(response_text),
            }
            yield f"data: {json.dumps(complete_event)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
