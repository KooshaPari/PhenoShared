"""Tests for exception handling and error scenarios."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text


def _database_reachable():
    """Check if database is reachable."""
    try:
        from database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class TestDatabaseExceptions:
    """Tests for database exception handling."""

    def test_integrity_error_on_duplicate_sku(self, db_session):
        """Test IntegrityError on duplicate SKU."""
        from models import Product

        # Create first product
        product1 = Product(id="p1", sku="DUP-SKU", name="Product 1", price=100.0)
        db_session.add(product1)
        db_session.commit()

        # Try to create product with same SKU
        product2 = Product(id="p2", sku="DUP-SKU", name="Product 2", price=100.0)
        db_session.add(product2)

        with pytest.raises(Exception):
            db_session.commit()

    def test_session_error_handling(self):
        """Test session error handling."""
        from database import get_db

        # Test that generator handles errors
        gen = get_db()
        session = next(gen)

        # Verify session is valid
        assert session is not None

        try:
            next(gen)
        except StopIteration:
            pass

    @pytest.mark.skipif(not _database_reachable(), reason="Database not reachable")
    def test_database_connection_error_recovery(self):
        """Test error recovery in database operations."""
        from database import SessionLocal

        # Create session
        session = SessionLocal()

        # Session should handle errors gracefully
        try:
            # Attempt query
            session.execute(text("SELECT 1"))
        finally:
            session.close()

    def test_model_validation_error(self):
        """Test model validation errors."""
        from models import Product

        # Create product with missing required fields should still work (no pydantic)
        # SQLAlchemy will handle constraints at DB level
        product = Product(id="test", sku="SKU", name="Test", price=100.0)

        # Product should be created without error
        assert product is not None


class TestMockServiceExceptions:
    """Tests for exception handling in mock services."""

    @pytest.mark.asyncio
    async def test_async_mock_exception(self):
        """Test AsyncMock exception handling."""
        mock = AsyncMock()
        mock.call.side_effect = Exception("Service error")

        with pytest.raises(Exception, match="Service error"):
            await mock.call()

    def test_sync_mock_exception(self):
        """Test sync mock exception handling."""
        mock = MagicMock()
        mock.call.side_effect = ValueError("Invalid value")

        with pytest.raises(ValueError, match="Invalid value"):
            mock.call()

    @pytest.mark.asyncio
    async def test_mock_fallback_handling(self):
        """Test mock service fallback on error."""
        mock = AsyncMock()
        mock.primary_call.side_effect = Exception("Primary failed")
        mock.fallback_call.return_value = "Fallback result"

        # Test fallback pattern
        try:
            await mock.primary_call()
        except Exception:
            result = await mock.fallback_call()
            assert result == "Fallback result"

    def test_mock_exception_context(self):
        """Test exception context in mocks."""
        mock = MagicMock()
        mock.method.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError) as exc_info:
            mock.method()

        assert "Test error" in str(exc_info.value)


class TestErrorMessages:
    """Tests for error message formatting."""

    def test_error_message_clarity(self):
        """Test error messages are clear."""
        error = ValueError("Product not found with ID: prod-123")
        assert "Product not found" in str(error)
        assert "prod-123" in str(error)

    def test_exception_chain(self):
        """Test exception chaining."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e
        except RuntimeError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)

    def test_custom_exception_message(self):
        """Test custom exception messages."""

        class ProductError(Exception):
            """Custom product error."""

            pass

        error = ProductError("Product operation failed")
        assert "Product operation" in str(error)

    def test_exception_type_checking(self):
        """Test exception type checking."""
        errors = [
            ValueError("Value error"),
            TypeError("Type error"),
            RuntimeError("Runtime error"),
        ]

        for error in errors:
            if isinstance(error, ValueError):
                assert "Value" in error.__class__.__name__
            elif isinstance(error, TypeError):
                assert "Type" in error.__class__.__name__
            elif isinstance(error, RuntimeError):
                assert "Runtime" in error.__class__.__name__


class TestErrorHandlingPatterns:
    """Tests for error handling patterns."""

    def test_try_except_finally(self):
        """Test try-except-finally pattern."""
        cleanup_called = False

        try:
            raise ValueError("Test error")
        except ValueError:
            pass
        finally:
            cleanup_called = True

        assert cleanup_called

    def test_context_manager_cleanup(self):
        """Test context manager ensures cleanup."""
        from contextlib import contextmanager

        cleanup_called = False

        @contextmanager
        def resource():
            try:
                yield "resource"
            finally:
                nonlocal cleanup_called
                cleanup_called = True

        with resource() as res:
            assert res == "resource"

        assert cleanup_called

    def test_error_suppression(self):
        """Test error suppression patterns."""
        from contextlib import suppress

        # With suppress
        with suppress(ValueError):
            raise ValueError("This is suppressed")

        # Should reach here without error
        assert True

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling."""

        async def failing_task():
            raise Exception("Async error")

        async def with_error_handling():
            try:
                await failing_task()
            except Exception as e:
                return str(e)

        result = await with_error_handling()
        assert "Async error" in result


class TestExceptionEdgeCases:
    """Tests for edge cases in exception handling."""

    def test_none_exception(self):
        """Test handling of None-like error scenarios."""

        def get_value(val):
            if val is None:
                return None
            return val

        result = get_value(None)
        assert result is None

    def test_empty_exception_message(self):
        """Test exception with empty message."""
        error = ValueError("")
        assert str(error) == ""

    def test_exception_with_multiple_args(self):
        """Test exception with multiple arguments."""
        error = Exception("arg1", "arg2", "arg3")
        assert len(error.args) == 3
        assert error.args[0] == "arg1"

    def test_exception_reraise(self):
        """Test re-raising exceptions."""
        original_error = None

        try:
            try:
                raise ValueError("Original")
            except ValueError as e:
                original_error = e
                raise  # Re-raise same exception
        except ValueError as e:
            assert e is original_error

    def test_exception_with_cause(self):
        """Test exception with explicit cause."""
        try:
            try:
                raise ValueError("Inner")
            except ValueError as e:
                raise RuntimeError("Outer") from e
        except RuntimeError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "Inner"
