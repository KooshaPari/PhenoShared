"""
Tests for pyhex domain layer
"""

from datetime import datetime

from pyhex.domain import (
    DomainError,
    DomainEvent,
    EntityId,
    Errors,
)


# Test EntityId directly
class TestEntityId:
    def test_create_generates_unique_id(self):
        id1 = EntityId.create()
        id2 = EntityId.create()
        assert id1.value != id2.value
        assert isinstance(id1.value, str)
        assert len(id1.value) > 0

    def test_create_with_specific_value(self):
        id = EntityId(value="test-123")
        assert id.value == "test-123"

    def test_equals_same_value(self):
        id1 = EntityId(value="test-123")
        id2 = EntityId(value="test-123")
        assert id1 == id2

    def test_equals_different_value(self):
        id1 = EntityId(value="test-1")
        id2 = EntityId(value="test-2")
        assert id1 != id2

    def test_str_conversion(self):
        id = EntityId(value="test-123")
        assert str(id) == "test-123"

    def test_hash_consistency(self):
        id1 = EntityId(value="test-123")
        id2 = EntityId(value="test-123")
        assert hash(id1) == hash(id2)


class TestDomainEvent:
    def test_create_domain_event(self):
        event = DomainEvent.__new__(DomainEvent)
        event._event_type = "TestEvent"
        event._aggregate_id = "test-123"
        event._occurred_at = datetime.now()

        assert event.event_type == "TestEvent"
        assert event.aggregate_id == "test-123"
        assert isinstance(event.occurred_at, datetime)

    def test_occurred_at_defaults_to_now(self):
        # DomainEvent requires event_type and aggregate_id
        before = datetime.utcnow()
        event = DomainEvent(event_type="TestEvent", aggregate_id="aggregate-1")
        after = datetime.utcnow()

        assert before <= event.occurred_at <= after


class TestDomainError:
    def test_create_domain_error(self):
        error = DomainError("TEST_ERROR", "Test error message")
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert str(error) == "TEST_ERROR: Test error message"

    def test_domain_error_with_cause(self):
        cause = ValueError("Cause error")
        error = DomainError("TEST_ERROR", "Test", cause)
        assert error.cause is cause

    def test_repr(self):
        error = DomainError("TEST_ERROR", "Test")
        assert repr(error) == "DomainError(code='TEST_ERROR', message='Test')"


class TestErrors:
    def test_not_found_error(self):
        error = Errors.NotFound("Resource not found")
        assert error.code == "NOT_FOUND"
        assert error.message == "Resource not found"

    def test_invalid_input_error(self):
        error = Errors.InvalidInput("Invalid data")
        assert error.code == "INVALID_INPUT"
        assert error.message == "Invalid data"

    def test_conflict_error(self):
        error = Errors.Conflict("Already exists")
        assert error.code == "CONFLICT"
        assert error.message == "Already exists"

    def test_default_messages(self):
        assert Errors.NotFound().message == "Entity not found"
        assert Errors.InvalidInput().message == "Invalid input"
        assert Errors.Conflict().message == "Conflict"


class TestAggregateRootBehavior:
    """Test aggregate behavior through concrete implementations"""

    def test_aggregate_adds_events_and_increments_version(self):
        from pyhex.domain import AggregateRoot

        class TestAggregate(AggregateRoot[EntityId]):
            def __init__(self, id: EntityId):
                super().__init__(id)
                self._status = "pending"

            @property
            def status(self) -> str:
                return self._status

            def confirm(self) -> None:
                self._status = "confirmed"
                # Create and add event
                evt = DomainEvent.__new__(DomainEvent)
                evt._event_type = "Confirmed"
                evt._aggregate_id = str(self.id)
                evt._occurred_at = datetime.now()
                self.add_event(evt)

        agg_id = EntityId.create()
        agg = TestAggregate(agg_id)

        assert agg.id == agg_id
        assert agg.version == 1
        assert agg.pending_events == []

        agg.confirm()
        assert agg.status == "confirmed"
        assert agg.version == 2
        assert len(agg.pending_events) == 1

        # Pull events clears them
        events = agg.pull_events()
        assert len(events) == 1
        assert agg.pending_events == []

    def test_aggregate_multiple_events(self):
        from pyhex.domain import AggregateRoot

        class TestAggregate(AggregateRoot[EntityId]):
            def __init__(self, id: EntityId):
                super().__init__(id)
                self._count = 0

            def add_multiple(self, n: int) -> None:
                for i in range(n):
                    evt = DomainEvent.__new__(DomainEvent)
                    evt._event_type = f"Event{i}"
                    evt._aggregate_id = str(self.id)
                    evt._occurred_at = datetime.now()
                    self.add_event(evt)

        agg = TestAggregate(EntityId.create())
        initial_version = agg.version

        agg.add_multiple(5)
        assert agg.version == initial_version + 5
        assert len(agg.pending_events) == 5
