"""
Tests for pyhex adapters layer
"""

import pytest

from pyhex.adapters import (
    InMemoryMessageBus,
    InMemoryRepository,
    RestAdapter,
    RestError,
    RestResponse,
)
from pyhex.domain import EntityId


class TestInMemoryRepository:
    @pytest.mark.asyncio
    async def test_save_entity(self):
        repo = InMemoryRepository()
        entity = {"id": EntityId.create(), "name": "Test"}

        saved = await repo.save(entity)
        assert saved is entity

    @pytest.mark.asyncio
    async def test_find_by_id(self):
        repo = InMemoryRepository()
        entity_id = EntityId(value="test-1")
        entity = {"id": entity_id, "name": "Test"}
        await repo.save(entity)

        found = await repo.find_by_id(entity_id)
        assert found is entity

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_for_missing(self):
        repo = InMemoryRepository()
        found = await repo.find_by_id(EntityId(value="non-existent"))
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        repo = InMemoryRepository()
        entity_id = EntityId(value="test-1")
        entity = {"id": entity_id, "name": "Test"}
        await repo.save(entity)

        await repo.delete(entity_id)
        found = await repo.find_by_id(entity_id)
        assert found is None

    @pytest.mark.asyncio
    async def test_find_all(self):
        repo = InMemoryRepository()
        await repo.save({"id": EntityId(value="1"), "name": "One"})
        await repo.save({"id": EntityId(value="2"), "name": "Two"})

        all_entities = await repo.find_all()
        assert len(all_entities) == 2

    @pytest.mark.asyncio
    async def test_exists(self):
        repo = InMemoryRepository()
        entity_id = EntityId(value="test-1")
        entity = {"id": entity_id, "name": "Test"}
        await repo.save(entity)

        assert await repo.exists(entity_id) is True
        assert await repo.exists(EntityId(value="non-existent")) is False

    @pytest.mark.asyncio
    async def test_clear(self):
        repo = InMemoryRepository()
        await repo.save({"id": EntityId(value="1"), "name": "One"})
        await repo.save({"id": EntityId(value="2"), "name": "Two"})

        repo.clear()
        all_entities = await repo.find_all()
        assert len(all_entities) == 0


class TestRestAdapter:
    @pytest.mark.asyncio
    async def test_returns_404_for_unregistered_route(self):
        adapter = RestAdapter()
        response = await adapter.handle("GET", "/unknown")

        assert response.status == 404
        assert response.error is not None
        assert response.error.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handles_registered_route(self):
        adapter = RestAdapter()

        async def handler(body, query):
            return {"message": "ok"}

        adapter.register("GET", "/api/test", handler)
        response = await adapter.handle("GET", "/api/test")

        assert response.status == 200
        assert response.body == {"message": "ok"}

    @pytest.mark.asyncio
    async def test_handles_post_with_body(self):
        adapter = RestAdapter()

        async def handler(body, query):
            return {"received": body}

        adapter.register("POST", "/api/test", handler)
        response = await adapter.handle("POST", "/api/test", body={"name": "Test"})

        assert response.status == 200
        assert response.body == {"received": {"name": "Test"}}

    @pytest.mark.asyncio
    async def test_returns_500_on_handler_error(self):
        adapter = RestAdapter()

        async def handler(body, query):
            raise ValueError("Handler error")

        adapter.register("GET", "/api/error", handler)
        response = await adapter.handle("GET", "/api/error")

        assert response.status == 500
        assert response.error is not None
        assert response.error.code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_method_case_insensitive(self):
        adapter = RestAdapter()

        async def handler(body, query):
            return {"method": "get"}

        adapter.register("get", "/api/test", handler)
        response = await adapter.handle("GET", "/api/test")

        assert response.status == 200


class TestRestResponse:
    def test_create_success_response(self):
        response = RestResponse(status=200, body={"data": "test"})
        assert response.status == 200
        assert response.body == {"data": "test"}
        assert response.headers == {}

    def test_create_error_response(self):
        error = RestError(code="NOT_FOUND", message="Route not found")
        response = RestResponse(status=404, error=error)
        assert response.status == 404
        assert response.error is error


class TestRestError:
    def test_create_error(self):
        error = RestError(code="TEST", message="Test error", details={"key": "value"})
        assert error.code == "TEST"
        assert error.message == "Test error"
        assert error.details == {"key": "value"}

    def test_to_dict(self):
        error = RestError(code="TEST", message="Error", details={"key": "value"})
        d = error.to_dict()
        assert d == {"code": "TEST", "message": "Error", "details": {"key": "value"}}


class TestInMemoryMessageBus:
    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self):
        bus = InMemoryMessageBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test-topic", handler)
        await bus.publish("test-topic", {"event_type": "Test", "data": "hello"})

        assert len(received) == 1
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = InMemoryMessageBus()
        received1 = []
        received2 = []

        async def handler1(event):
            received1.append(event)

        async def handler2(event):
            received2.append(event)

        bus.subscribe("test-topic", handler1)
        bus.subscribe("test-topic", handler2)

        await bus.publish("test-topic", {"event_type": "Test", "data": "broadcast"})

        assert len(received1) == 1
        assert len(received2) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = InMemoryMessageBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test-topic", handler)
        await bus.publish("test-topic", {"event_type": "Test", "data": "first"})

        bus.unsubscribe("test-topic", handler)
        await bus.publish("test-topic", {"event_type": "Test", "data": "second"})

        assert len(received) == 1
        assert received[0]["data"] == "first"

    @pytest.mark.asyncio
    async def test_publish_to_topic_with_no_subscribers(self):
        bus = InMemoryMessageBus()
        # Should not raise
        await bus.publish("no-subscribers", {"event_type": "Test", "data": "test"})

    @pytest.mark.asyncio
    async def test_subscribe_to_multiple_topics(self):
        bus = InMemoryMessageBus()
        received_topic1 = []
        received_topic2 = []

        async def handler1(event):
            received_topic1.append(event)

        async def handler2(event):
            received_topic2.append(event)

        bus.subscribe("topic1", handler1)
        bus.subscribe("topic2", handler2)

        await bus.publish("topic1", {"event_type": "Test", "data": "topic1"})
        await bus.publish("topic2", {"event_type": "Test", "data": "topic2"})

        assert len(received_topic1) == 1
        assert len(received_topic2) == 1
        assert received_topic1[0]["data"] == "topic1"
        assert received_topic2[0]["data"] == "topic2"
