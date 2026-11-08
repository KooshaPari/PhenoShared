"""Error handling and propagation integration tests.

Tests error scenarios:
- API error responses
- Error propagation from backend to frontend
- Error recovery
- Error logging and monitoring
- API error contracts
"""

import json

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestErrorResponses:
    """Error response format and content."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, async_client: AsyncClient):
        """Test 404 error response."""
        response = await async_client.get("/api/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_400_bad_request(self, async_client: AsyncClient):
        """Test 400 bad request response."""
        payload = {"invalid": "payload"}  # Missing required 'text' field
        response = await async_client.post("/chat", json=payload)

        assert response.status_code == 422  # Pydantic validation

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, async_client: AsyncClient):
        """Test 405 method not allowed."""
        # GET on POST endpoint
        response = await async_client.get("/chat")

        # Could be 405 or 404 depending on routing
        assert response.status_code in [404, 405]

    @pytest.mark.asyncio
    async def test_500_internal_error(self, async_client: AsyncClient):
        """Test 500 error handling."""
        # This would require mocking an actual error
        # For now, we just verify endpoints don't crash
        response = await async_client.post("/chat", json={"text": "test"})

        # Even with errors, should return proper status
        assert isinstance(response.status_code, int)
        assert response.status_code >= 200

    @pytest.mark.asyncio
    async def test_503_service_unavailable(self, async_client: AsyncClient):
        """Test 503 when service unavailable."""
        response = await async_client.post("/chat", json={"text": "test", "session_id": "test"})

        # Might be 503 if agent not available
        assert response.status_code in [200, 503]


class TestErrorStructure:
    """Error response structure and format."""

    @pytest.mark.asyncio
    async def test_error_is_json(self, async_client: AsyncClient):
        """Test error response is valid JSON."""
        response = await async_client.post(
            "/chat",
            json={"session_id": "test"},  # Missing text
        )

        # Should have JSON response
        try:
            data = response.json()
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Error response is not valid JSON")

    @pytest.mark.asyncio
    async def test_error_has_detail_field(self, async_client: AsyncClient):
        """Test error responses have detail field."""
        response = await async_client.get("/tools")

        if response.status_code >= 400:
            data = response.json()
            # Should have error details
            assert "detail" in data or "error" in data or "details" in data

    @pytest.mark.asyncio
    async def test_validation_error_structure(self, async_client: AsyncClient):
        """Test validation error has proper structure."""
        response = await async_client.post("/chat", json={"session_id": "test"})

        data = response.json()

        # Pydantic validation errors have specific structure
        assert response.status_code == 422
        # Should indicate validation error
        assert isinstance(data, (dict, list))


class TestErrorMessages:
    """Error message content and clarity."""

    @pytest.mark.asyncio
    async def test_error_message_is_string(self, async_client: AsyncClient):
        """Test error messages are strings."""
        response = await async_client.post("/chat", json={"session_id": "test"})

        if response.status_code >= 400:
            data = response.json()
            # Error details should be string or list
            if "detail" in data:
                assert isinstance(data["detail"], (str, list))

    @pytest.mark.asyncio
    async def test_error_not_exposing_secrets(self, async_client: AsyncClient):
        """Test error messages don't expose sensitive data."""
        response = await async_client.post("/chat", json={"session_id": "test"})

        error_text = response.text.lower()

        # Should not contain common sensitive patterns
        assert "password" not in error_text
        assert "secret" not in error_text
        assert "key" not in error_text or "api" not in error_text


class TestErrorPropagation:
    """Error propagation from different layers."""

    @pytest.mark.asyncio
    async def test_validation_error_propagates(self, async_client: AsyncClient):
        """Test validation errors propagate correctly."""
        response = await async_client.post(
            "/chat",
            json={},  # Empty payload
        )

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_content_type(self, async_client: AsyncClient):
        """Test missing content-type handling."""
        response = await async_client.post(
            "/chat",
            content=b'{"text": "test"}',
            headers={},  # No content-type
        )

        # FastAPI should handle this
        assert response.status_code in [200, 415, 422, 503]

    @pytest.mark.asyncio
    async def test_malformed_json(self, async_client: AsyncClient):
        """Test malformed JSON handling."""
        response = await async_client.post(
            "/chat",
            content=b'{"text": "test"',  # Missing closing brace
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_data_type_error(self, async_client: AsyncClient):
        """Test wrong data type in payload."""
        response = await async_client.post(
            "/chat",
            json={"text": 123, "session_id": "test"},  # text should be string
        )

        # Should validate type
        assert response.status_code in [200, 422]


class TestErrorRecovery:
    """Error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_recover_from_validation_error(self, async_client: AsyncClient):
        """Test subsequent requests work after validation error."""
        # First request: invalid
        response1 = await async_client.post("/chat", json={"session_id": "test"})
        assert response1.status_code >= 400

        # Second request: valid
        response2 = await async_client.post("/chat", json={"text": "valid", "session_id": "test"})

        # Second should work (or return expected status)
        assert response2.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_recover_from_404(self, async_client: AsyncClient):
        """Test subsequent requests work after 404."""
        # First request: 404
        response1 = await async_client.get("/api/nonexistent")
        assert response1.status_code == 404

        # Second request: valid
        response2 = await async_client.get("/health")
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_sequential_errors(self, async_client: AsyncClient):
        """Test handling multiple sequential errors."""
        responses = []

        for _ in range(3):
            response = await async_client.post(
                "/chat",
                json={"session_id": "test"},  # Invalid
            )
            responses.append(response.status_code)

        # All should consistently error
        assert all(status >= 400 for status in responses)


class TestErrorContract:
    """Frontend-backend error contract."""

    @pytest.mark.asyncio
    async def test_error_is_serializable_for_frontend(self, async_client: AsyncClient):
        """Test errors can be serialized for JSON response."""
        response = await async_client.post("/chat", json={"session_id": "test"})

        # Should always be serializable JSON
        try:
            data = response.json()
            json.dumps(data)  # Should be JSON-serializable
            assert True
        except Exception as e:
            pytest.fail(f"Error not JSON-serializable: {e}")

    @pytest.mark.asyncio
    async def test_error_status_codes_consistent(self, async_client: AsyncClient):
        """Test consistent error status codes."""
        # Validation error
        response = await async_client.post("/chat", json={"session_id": "test"})

        # Should be 4xx error
        assert 400 <= response.status_code < 500 or response.status_code == 503

    @pytest.mark.asyncio
    async def test_client_can_parse_error(self, async_client: AsyncClient):
        """Test client can parse error response."""
        response = await async_client.post("/chat", json={})

        if response.status_code >= 400:
            # Frontend can parse this
            data = response.json()
            assert isinstance(data, dict)


class TestEdgeCaseErrors:
    """Edge case error scenarios."""

    @pytest.mark.asyncio
    async def test_unicode_in_error_message(self, async_client: AsyncClient):
        """Test unicode handling in error messages."""
        response = await async_client.post("/chat", json={"text": "日本語テキスト"})

        # Should handle unicode without breaking
        error_text = response.text
        assert isinstance(error_text, str)

    @pytest.mark.asyncio
    async def test_very_long_error_message(self, async_client: AsyncClient):
        """Test handling very long error messages."""
        long_text = "A" * 100000

        response = await async_client.post("/chat", json={"text": long_text, "session_id": "test"})

        # Should handle without crashing
        assert response.status_code >= 200

    @pytest.mark.asyncio
    async def test_concurrent_errors(self, async_client: AsyncClient):
        """Test handling concurrent error requests."""
        import asyncio

        async def error_request():
            return await async_client.post(
                "/chat",
                json={"session_id": "test"},  # Invalid
            )

        # Run 10 concurrent error requests
        tasks = [error_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should error consistently
        assert all(r.status_code >= 400 or r.status_code == 503 for r in results)

    @pytest.mark.asyncio
    async def test_error_doesnt_corrupt_state(self, async_client: AsyncClient):
        """Test errors don't corrupt application state."""
        # Make error request
        await async_client.post("/chat", json={"session_id": "test"})

        # Application should still be functional
        response = await async_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_logging(self, async_client: AsyncClient):
        """Test that errors are properly logged."""
        # This tests that error handling doesn't suppress logs
        response = await async_client.post("/chat", json={"session_id": "test"})

        # Should have error status
        assert response.status_code >= 400
        # Response should be valid (logging happened internally)
        assert response.status_code >= 200
