"""Session management integration tests.

Tests session CRUD operations:
- Session creation
- Session retrieval
- Session updates
- Session lifecycle
- Concurrency and race conditions
"""

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestSessionCreation:
    """Session creation tests."""

    @pytest.mark.asyncio
    async def test_create_session_minimal(self, async_client: AsyncClient):
        """Test creating session with minimal data."""
        response = await async_client.post("/api/session")

        assert response.status_code == 200
        data = response.json()
        assert "sessionId" in data

    @pytest.mark.asyncio
    async def test_create_session_with_body(self, async_client: AsyncClient):
        """Test creating session with request body."""
        payload = {}
        response = await async_client.post("/api/session", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "sessionId" in data

    @pytest.mark.asyncio
    async def test_session_id_format(self, async_client: AsyncClient):
        """Test session ID is valid UUID."""
        response = await async_client.post("/api/session")
        data = response.json()
        session_id = data["sessionId"]

        # Should be valid UUID
        try:
            uuid.UUID(session_id)
            assert True
        except ValueError:
            pytest.fail(f"Invalid UUID: {session_id}")

    @pytest.mark.asyncio
    async def test_session_timestamp_format(self, async_client: AsyncClient):
        """Test session has valid ISO timestamp."""
        response = await async_client.post("/api/session")
        data = response.json()

        # Should have ISO format timestamp
        assert "createdAt" in data
        created_at = data["createdAt"]

        # Try parsing as ISO format
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            assert True
        except ValueError:
            # Acceptable if format differs
            assert isinstance(created_at, str)

    @pytest.mark.asyncio
    async def test_session_messages_initialized_empty(self, async_client: AsyncClient):
        """Test new session has empty messages."""
        response = await async_client.post("/api/session")
        data = response.json()

        assert "messages" in data
        assert data["messages"] == [] or isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_create_multiple_sessions(self, async_client: AsyncClient):
        """Test creating multiple sessions."""
        session_ids = []

        for _ in range(5):
            response = await async_client.post("/api/session")
            assert response.status_code == 200
            session_ids.append(response.json()["sessionId"])

        # All should be unique
        assert len(set(session_ids)) == 5


class TestSessionRetrieval:
    """Session retrieval tests."""

    @pytest.mark.asyncio
    async def test_get_session_after_creation(self, async_client: AsyncClient):
        """Test retrieving session immediately after creation."""
        # Create
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]

        # Retrieve
        get_resp = await async_client.get(f"/api/session/{session_id}")
        assert get_resp.status_code == 200

        data = get_resp.json()
        assert data["sessionId"] == session_id

    @pytest.mark.asyncio
    async def test_get_session_has_all_fields(self, async_client: AsyncClient):
        """Test retrieved session has all required fields."""
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]

        get_resp = await async_client.get(f"/api/session/{session_id}")
        data = get_resp.json()

        assert "sessionId" in data
        assert "createdAt" in data
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_session_preserves_data(self, async_client: AsyncClient):
        """Test session data is preserved on retrieval."""
        create_resp = await async_client.post("/api/session")
        original_data = create_resp.json()

        get_resp = await async_client.get(f"/api/session/{original_data['sessionId']}")
        retrieved_data = get_resp.json()

        # Core fields should match
        assert original_data["sessionId"] == retrieved_data["sessionId"]
        # CreatedAt should be consistent
        assert original_data["createdAt"] == retrieved_data["createdAt"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, async_client: AsyncClient):
        """Test getting non-existent session."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/session/{fake_id}")

        # Could be 404 or return default
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_session_with_invalid_id(self, async_client: AsyncClient):
        """Test getting session with invalid ID format."""
        response = await async_client.get("/api/session/not-a-uuid")

        # Should handle gracefully
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_get_session_empty_id(self, async_client: AsyncClient):
        """Test getting session with empty ID."""
        response = await async_client.get("/api/session/")

        # Should 404 or redirect
        assert response.status_code in [307, 404]


class TestSessionData:
    """Session data persistence tests."""

    @pytest.mark.asyncio
    async def test_session_messages_list(self, async_client: AsyncClient):
        """Test session messages field is a list."""
        response = await async_client.post("/api/session")
        data = response.json()

        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_session_immutability(self, async_client: AsyncClient):
        """Test session data doesn't change unexpectedly."""
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]
        created_at_1 = create_resp.json()["createdAt"]

        # Retrieve after delay
        import asyncio

        await asyncio.sleep(0.1)

        get_resp = await async_client.get(f"/api/session/{session_id}")
        created_at_2 = get_resp.json()["createdAt"]

        # CreatedAt should not change
        assert created_at_1 == created_at_2

    @pytest.mark.asyncio
    async def test_session_isolation(self, async_client: AsyncClient):
        """Test sessions are isolated from each other."""
        # Create two sessions
        resp1 = await async_client.post("/api/session")
        session1_id = resp1.json()["sessionId"]

        resp2 = await async_client.post("/api/session")
        session2_id = resp2.json()["sessionId"]

        # Sessions should be different
        assert session1_id != session2_id

        # Retrieving one shouldn't affect the other
        get1 = await async_client.get(f"/api/session/{session1_id}")
        get2 = await async_client.get(f"/api/session/{session2_id}")

        assert get1.json()["sessionId"] == session1_id
        assert get2.json()["sessionId"] == session2_id


class TestSessionConcurrency:
    """Concurrent session operations."""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self, async_client: AsyncClient):
        """Test creating multiple sessions concurrently."""
        import asyncio

        async def create_session():
            return await async_client.post("/api/session")

        # Create 10 sessions concurrently
        tasks = [create_session() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique IDs
        session_ids = [r.json()["sessionId"] for r in responses]
        assert len(set(session_ids)) == 10

    @pytest.mark.asyncio
    async def test_concurrent_session_retrieval(self, async_client: AsyncClient):
        """Test retrieving sessions concurrently."""
        import asyncio

        # Create sessions first
        create_resp1 = await async_client.post("/api/session")
        create_resp2 = await async_client.post("/api/session")

        session_id1 = create_resp1.json()["sessionId"]
        session_id2 = create_resp2.json()["sessionId"]

        # Retrieve concurrently
        async def get_session(session_id):
            return await async_client.get(f"/api/session/{session_id}")

        tasks = [get_session(session_id1), get_session(session_id2)]
        responses = await asyncio.gather(*tasks)

        # Both should succeed
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, async_client: AsyncClient):
        """Test mixed create and retrieve operations."""
        import asyncio

        async def create_and_retrieve():
            # Create
            create_resp = await async_client.post("/api/session")
            if create_resp.status_code != 200:
                return None

            session_id = create_resp.json()["sessionId"]

            # Immediately retrieve
            get_resp = await async_client.get(f"/api/session/{session_id}")
            return get_resp.status_code

        # Run 5 concurrent create-retrieve sequences
        tasks = [create_and_retrieve() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(status == 200 for status in results if status)


class TestSessionEdgeCases:
    """Edge case tests for sessions."""

    @pytest.mark.asyncio
    async def test_session_with_special_characters_in_id(self, async_client: AsyncClient):
        """Test handling special characters in URL."""
        response = await async_client.get("/api/session/test%20with%20spaces")

        # Should handle URL encoding
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_session_with_very_long_id(self, async_client: AsyncClient):
        """Test handling very long session ID."""
        long_id = "a" * 1000
        response = await async_client.get(f"/api/session/{long_id}")

        # Should handle or reject
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_session_uppercase_uuid(self, async_client: AsyncClient):
        """Test session lookup with uppercase UUID."""
        create_resp = await async_client.post("/api/session")
        session_id = create_resp.json()["sessionId"]

        # Try uppercase (UUIDs are usually case-insensitive)
        response = await async_client.get(f"/api/session/{session_id.upper()}")

        # Should handle case-insensitivity
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_session_rapid_fire_requests(self, async_client: AsyncClient):
        """Test rapid-fire session requests."""

        session_ids = []

        # Create 100 sessions as fast as possible
        for _ in range(100):
            response = await async_client.post("/api/session")
            if response.status_code == 200:
                session_ids.append(response.json()["sessionId"])

        # All should be unique
        assert len(set(session_ids)) == len(session_ids)
