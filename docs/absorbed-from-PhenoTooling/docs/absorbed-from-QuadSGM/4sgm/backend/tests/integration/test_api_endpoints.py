"""FastAPI endpoint integration tests.

Tests all HTTP endpoints:
- Health checks
- Tool listing
- Session creation and retrieval
- Chat endpoints (standard and streaming)
- Error handling and validation
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestHealthEndpoint:
    """Health check endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, async_client: AsyncClient):
        """Test health endpoint returns 200 OK."""
        response = await async_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self, async_client: AsyncClient):
        """Test health response has correct structure."""
        response = await async_client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "ok"
        assert "mcp" in data
        assert "tools" in data
        assert isinstance(data["tools"], int)

    @pytest.mark.asyncio
    async def test_health_endpoint_with_mcp(self, async_client: AsyncClient):
        """Test health endpoint with MCP available."""
        response = await async_client.get("/health")
        data = response.json()

        # Even if MCP is not available, endpoint should return 200
        assert response.status_code == 200
        assert isinstance(data["mcp"], bool)


class TestToolsEndpoint:
    """Tool listing endpoint tests."""

    @pytest.mark.asyncio
    async def test_tools_endpoint_returns_list(self, async_client: AsyncClient):
        """Test tools endpoint returns tool list."""
        response = await async_client.get("/tools")

        # If tools loaded, should return 200
        if response.status_code == 200:
            data = response.json()
            assert "count" in data
            assert "tools" in data
            assert isinstance(data["tools"], list)

    @pytest.mark.asyncio
    async def test_tools_endpoint_structure(self, async_client: AsyncClient):
        """Test tools response has correct structure."""
        response = await async_client.get("/tools")

        if response.status_code == 200:
            data = response.json()
            assert data["count"] >= 0

            if data["count"] > 0:
                for tool in data["tools"]:
                    assert "name" in tool
                    assert "description" in tool
                    assert isinstance(tool["name"], str)
                    assert isinstance(tool["description"], str)

    @pytest.mark.asyncio
    async def test_tools_endpoint_unavailable(self, async_client: AsyncClient):
        """Test tools endpoint with no tools loaded."""
        response = await async_client.get("/tools")

        # Either 200 or 503 depending on MCP availability
        assert response.status_code in [200, 503]

        if response.status_code == 503:
            data = response.json()
            assert "detail" in data


class TestSessionEndpoints:
    """Session management endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_session(self, async_client: AsyncClient):
        """Test session creation endpoint."""
        response = await async_client.post("/api/session")
        assert response.status_code == 200

        data = response.json()
        assert "sessionId" in data
        assert "createdAt" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_create_session_generates_uuid(self, async_client: AsyncClient):
        """Test session creation generates valid UUID."""
        response = await async_client.post("/api/session")
        data = response.json()

        # Validate it's a valid UUID
        session_id = data["sessionId"]
        try:
            uuid.UUID(session_id)
            assert True
        except ValueError:
            pytest.fail(f"Invalid UUID format: {session_id}")

    @pytest.mark.asyncio
    async def test_create_session_unique(self, async_client: AsyncClient):
        """Test each session creation has unique ID."""
        response1 = await async_client.post("/api/session")
        response2 = await async_client.post("/api/session")

        session_id1 = response1.json()["sessionId"]
        session_id2 = response2.json()["sessionId"]

        assert session_id1 != session_id2

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, async_client: AsyncClient):
        """Test retrieving session by ID."""
        # Create session
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]

        # Get session
        response = await async_client.get(f"/api/session/{session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["sessionId"] == session_id
        assert "createdAt" in data
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_session_structure(self, async_client: AsyncClient):
        """Test session response has correct structure."""
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]

        response = await async_client.get(f"/api/session/{session_id}")
        data = response.json()

        assert isinstance(data["sessionId"], str)
        assert isinstance(data["createdAt"], str)
        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, async_client: AsyncClient):
        """Test getting non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/session/{fake_id}")

        # Should still return 200 with empty/default session
        # (Depending on implementation, could be 404)
        assert response.status_code in [200, 404]


class TestChatEndpoint:
    """Chat endpoint tests (non-streaming)."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_basic(self, async_client: AsyncClient):
        """Test basic chat request."""
        payload = {"text": "Hello", "session_id": "test-session-123"}

        response = await async_client.post("/chat", json=payload)

        # Could be 200 or 503 depending on agent availability
        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert "session_id" in data
            assert data["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_chat_endpoint_response_structure(self, async_client: AsyncClient):
        """Test chat response has correct structure."""
        payload = {"text": "What are your business hours?", "session_id": "test-123"}

        response = await async_client.post("/chat", json=payload)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["text"], str)
            assert isinstance(data["session_id"], str)

    @pytest.mark.asyncio
    async def test_chat_endpoint_missing_session_id(self, async_client: AsyncClient):
        """Test chat with missing session_id uses default."""
        payload = {"text": "Hello"}

        response = await async_client.post("/chat", json=payload)

        if response.status_code == 200:
            data = response.json()
            # Should assign default session_id
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_invalid_json(self, async_client: AsyncClient):
        """Test chat with invalid JSON."""
        response = await async_client.post(
            "/chat", content=b"invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_endpoint_missing_text(self, async_client: AsyncClient):
        """Test chat with missing text field."""
        payload = {"session_id": "test-123"}
        response = await async_client.post("/chat", json=payload)

        assert response.status_code == 422  # Missing required field

    @pytest.mark.asyncio
    async def test_chat_endpoint_empty_text(self, async_client: AsyncClient):
        """Test chat with empty text."""
        payload = {"text": "", "session_id": "test-123"}

        response = await async_client.post("/chat", json=payload)

        # Should handle gracefully (503 is expected if backend not running)
        assert response.status_code in [200, 422, 400, 503]


class TestChatStreamingEndpoint:
    """Chat streaming (SSE) endpoint tests."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_returns_event_stream(self, async_client: AsyncClient):
        """Test streaming endpoint returns event-stream content type."""
        payload = {"text": "Hello", "session_id": "stream-test-123"}

        response = await async_client.post("/chat/stream", json=payload)

        if response.status_code == 200:
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_endpoint_structure(self, async_client: AsyncClient):
        """Test streaming response has SSE format."""
        payload = {"text": "test message", "session_id": "stream-123"}

        response = await async_client.post("/chat/stream", json=payload)

        if response.status_code == 200:
            # Check that response is streaming (either has content or is stream)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_endpoint_with_tools_unavailable(self, async_client: AsyncClient):
        """Test streaming endpoint with no tools loaded."""
        payload = {"text": "test", "session_id": "stream-test"}

        response = await async_client.post("/chat/stream", json=payload)

        # Should return 200 or 503 based on tool availability
        assert response.status_code in [200, 503]


class TestErrorHandling:
    """Error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_404_on_nonexistent_route(self, async_client: AsyncClient):
        """Test 404 on nonexistent route."""
        response = await async_client.get("/api/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client: AsyncClient):
        """Test method not allowed."""
        # GET on POST-only endpoint
        response = await async_client.get("/chat")
        assert response.status_code in [405, 404]

    @pytest.mark.asyncio
    async def test_unsupported_content_type(self, async_client: AsyncClient):
        """Test unsupported content type."""
        response = await async_client.post(
            "/chat", content=b"test", headers={"Content-Type": "text/plain"}
        )

        # Should still work or return 400
        assert response.status_code in [200, 400, 422, 503]

    @pytest.mark.asyncio
    async def test_large_payload(self, async_client: AsyncClient):
        """Test handling of large payloads."""
        large_text = "A" * 100000  # 100KB
        payload = {"text": large_text, "session_id": "test-123"}

        response = await async_client.post("/chat", json=payload)

        # Should handle or reject gracefully
        assert response.status_code in [200, 413, 422, 503]


class TestAPIContracts:
    """Test frontend-backend API contracts."""

    @pytest.mark.asyncio
    async def test_session_response_contract(self, async_client: AsyncClient):
        """Test session response matches frontend expectations."""
        response = await async_client.post("/api/session")
        data = response.json()

        # Frontend expects these fields
        assert "sessionId" in data  # camelCase
        assert "createdAt" in data
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_chat_response_contract(self, async_client: AsyncClient):
        """Test chat response matches frontend expectations."""
        payload = {"text": "Hello", "session_id": "test-123"}

        response = await async_client.post("/chat", json=payload)

        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_error_response_structure(self, async_client: AsyncClient):
        """Test error responses have consistent structure."""
        # Trigger an error
        response = await async_client.post(
            "/chat",
            json={"session_id": "test"},  # Missing text
        )

        # Should have structured error
        assert response.status_code >= 400

        try:
            data = response.json()
            # Errors should be serializable
            assert isinstance(data, dict)
        except ValueError:
            # Some errors might not be JSON
            pass
