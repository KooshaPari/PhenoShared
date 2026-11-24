"""
Tests for pyhex application layer
"""

from datetime import datetime

import pytest

from pyhex.application import (
    DTO,
    AppErrors,
    ApplicationError,
    Command,
    DtoMeta,
    PaginatedResult,
    PaginationInput,
    Query,
    QueryFilter,
)


class TestDTO:
    def test_create_dto_with_data(self):
        dto = DTO(data={"name": "Test"})
        assert dto.data == {"name": "Test"}
        assert dto.meta is None

    def test_create_dto_with_meta(self):
        meta = DtoMeta(version="1.0", request_id="req-123")
        dto = DTO(data={"name": "Test"}, meta=meta)
        assert dto.meta is meta
        assert dto.meta.version == "1.0"
        assert dto.meta.request_id == "req-123"


class TestDtoMeta:
    def test_create_with_defaults(self):
        meta = DtoMeta()
        assert meta.version is None
        assert meta.request_id is None
        assert isinstance(meta.timestamp, datetime)

    def test_create_with_values(self):
        meta = DtoMeta(version="2.0", request_id="req-456")
        assert meta.version == "2.0"
        assert meta.request_id == "req-456"


class TestPaginatedResult:
    def test_create_paginated_result(self):
        result = PaginatedResult(
            data=[{"id": "1"}, {"id": "2"}],
            page=1,
            page_size=10,
            total=25,
        )
        assert len(result.data) == 2
        assert result.page == 1
        assert result.page_size == 10
        assert result.total == 25

    def test_total_pages_calculation(self):
        result = PaginatedResult(
            data=[],
            page=1,
            page_size=10,
            total=25,
        )
        assert result.total_pages == 3  # ceil(25/10)

    def test_total_pages_exact_division(self):
        result = PaginatedResult(
            data=[],
            page=1,
            page_size=10,
            total=30,
        )
        assert result.total_pages == 3


class TestCommand:
    def test_create_command(self):
        cmd = Command(
            command_type="CreateUser",
            payload={"name": "Test"},
        )
        assert cmd.command_type == "CreateUser"
        assert cmd.payload == {"name": "Test"}
        assert cmd.metadata == {}

    def test_create_command_with_metadata(self):
        cmd = Command(
            command_type="UpdateUser",
            payload={"id": "123"},
            metadata={"user_id": "user-1"},
        )
        assert cmd.metadata == {"user_id": "user-1"}


class TestQuery:
    def test_create_empty_query(self):
        q = Query(query_type="GetUsers")
        assert q.query_type == "GetUsers"
        assert q.filters == []
        assert q.pagination is None

    def test_create_query_with_filters(self):
        q = Query(
            query_type="GetUsers",
            filters=[QueryFilter("status", "eq", "active")],
        )
        assert len(q.filters) == 1


class TestQueryFilter:
    def test_create_filter(self):
        f = QueryFilter("name", "contains", "test")
        assert f.field == "name"
        assert f.operator == "contains"
        assert f.value == "test"


class TestPaginationInput:
    def test_create_with_defaults(self):
        p = PaginationInput()
        assert p.page == 1
        assert p.page_size == 20

    def test_create_with_values(self):
        p = PaginationInput(page=2, page_size=50)
        assert p.page == 2
        assert p.page_size == 50

    def test_page_minimum_enforced(self):
        p = PaginationInput(page=0)
        assert p.page == 1

    def test_page_size_maximum_enforced(self):
        p = PaginationInput(page_size=200)
        assert p.page_size == 100


class TestUseCaseFunc:
    @pytest.mark.asyncio
    async def test_execute_calls_function(self):
        from pyhex.application import UseCaseFunc

        async def async_fn(x):
            return len(x)

        use_case = UseCaseFunc(async_fn)
        result = await use_case.execute("hello")
        assert result == 5


class TestCommandHandler:
    @pytest.mark.asyncio
    async def test_handle_calls_use_case(self):
        from pyhex.application import CommandHandler, UseCaseFunc

        async def create_user(name: str) -> str:
            return f"user-{name}"

        use_case = UseCaseFunc(create_user)
        handler = CommandHandler(use_case)

        result = await handler.handle("alice")
        assert result == "user-alice"


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_handle_calls_use_case(self):
        from pyhex.application import QueryHandler, UseCaseFunc

        async def get_user(id: str) -> dict:
            return {"id": id, "name": "Test"}

        use_case = UseCaseFunc(get_user)
        handler = QueryHandler(use_case)

        result = await handler.handle("123")
        assert result == {"id": "123", "name": "Test"}


class TestApplicationError:
    def test_create_error(self):
        error = ApplicationError("VALIDATION_ERROR", "Invalid input")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert str(error) == "VALIDATION_ERROR: Invalid input"

    def test_error_with_cause(self):
        cause = ValueError("Cause")
        error = ApplicationError("SYSTEM_ERROR", "Failure", cause)
        assert error.cause is cause

    def test_repr(self):
        error = ApplicationError("TEST", "Message")
        assert repr(error) == "ApplicationError(code='TEST', message='Message')"


class TestAppErrors:
    def test_validation_error(self):
        error = AppErrors.Validation("Field is required")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Field is required"

    def test_not_found_error(self):
        error = AppErrors.NotFound("User not found")
        assert error.code == "NOT_FOUND"
        assert error.message == "User not found"

    def test_conflict_error(self):
        error = AppErrors.Conflict("Email already exists")
        assert error.code == "CONFLICT"
        assert error.message == "Email already exists"

    def test_unauthorized_error(self):
        error = AppErrors.Unauthorized("Access denied")
        assert error.code == "UNAUTHORIZED"
        assert error.message == "Access denied"
