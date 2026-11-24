"""
Tests for pyhex ports layer
"""


from pyhex.domain import DomainEvent
from pyhex.ports import (
    Condition,
    Filter,
    FilterOperator,
)


class TestInputPort:
    def test_input_port_is_class(self):
        from pyhex.ports import InputPort

        assert InputPort is not None


class TestOutputPort:
    def test_output_port_is_class(self):
        from pyhex.ports import OutputPort

        assert OutputPort is not None


class TestRepository:
    def test_repository_protocol_exists(self):
        from pyhex.ports import Repository

        assert Repository is not None


class TestEventStore:
    def test_event_store_is_abstract(self):
        from pyhex.ports import EventStore

        class MyEventStore(EventStore[DomainEvent]):
            async def append(
                self,
                aggregate_id: str,
                events: list[DomainEvent],
                expected_version: int,
            ) -> None:
                pass

            async def get_events(self, aggregate_id: str) -> list[DomainEvent]:
                return []

        store = MyEventStore()
        assert isinstance(store, EventStore)


class TestMessageBus:
    def test_message_bus_is_abstract(self):
        from pyhex.ports import MessageBus

        class MyMessageBus(MessageBus):
            async def publish(self, topic: str, event: DomainEvent) -> None:
                pass

            def subscribe(self, topic: str, handler) -> None:
                pass

        bus = MyMessageBus()
        assert isinstance(bus, MessageBus)


class TestFilter:
    def test_create_empty_filter(self):
        f = Filter()
        assert f.conditions == []
        assert f.limit is None
        assert f.offset is None

    def test_create_filter_with_conditions(self):
        f = Filter(
            conditions=[
                Condition("name", FilterOperator.EQ, "Test"),
            ],
            limit=10,
            offset=0,
        )
        assert len(f.conditions) == 1
        assert f.limit == 10
        assert f.offset == 0

    def test_add_condition_returns_self(self):
        f = Filter()
        result = f.add_condition("name", FilterOperator.CONTAINS, "test")
        assert result is f
        assert len(f.conditions) == 1

    def test_filter_chaining(self):
        f = Filter()
        f.add_condition("a", FilterOperator.EQ, 1).add_condition(
            "b", FilterOperator.GT, 2
        )
        assert len(f.conditions) == 2


class TestCondition:
    def test_create_condition(self):
        c = Condition("name", FilterOperator.EQ, "Test")
        assert c.field == "name"
        assert c.operator == "eq"
        assert c.value == "Test"


class TestFilterOperator:
    def test_all_operators_defined(self):
        assert FilterOperator.EQ == "eq"
        assert FilterOperator.NE == "ne"
        assert FilterOperator.GT == "gt"
        assert FilterOperator.LT == "lt"
        assert FilterOperator.GTE == "gte"
        assert FilterOperator.LTE == "lte"
        assert FilterOperator.CONTAINS == "contains"
        assert FilterOperator.STARTS_WITH == "startsWith"
        assert FilterOperator.IN == "in"
