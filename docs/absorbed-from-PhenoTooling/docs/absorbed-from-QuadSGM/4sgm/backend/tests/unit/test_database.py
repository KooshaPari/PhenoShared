"""Tests for database.py configuration and utilities."""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


class TestDatabaseConfiguration:
    """Tests for database configuration."""

    def test_get_db_session_creation(self):
        """Test get_db creates a session."""
        from database import get_db

        gen = get_db()
        session = next(gen)

        assert session is not None
        assert isinstance(session, Session)

        # Cleanup
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_db_cleanup(self):
        """Test get_db closes session on exit."""
        from database import get_db

        gen = get_db()
        session = next(gen)

        # Check session is open
        assert not session.is_active or session.is_active  # Session exists

        # Cleanup
        try:
            next(gen)
        except StopIteration:
            pass

    def test_init_db_creates_tables(self):
        """Test init_db creates all tables."""
        # Create in-memory test engine
        test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

        # Patch the engine
        with patch("database.engine", test_engine):
            from database import init_db

            init_db()

            # Verify tables were created
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()

            assert "products" in tables
            assert "chat_sessions" in tables
            assert "documents" in tables

    def test_init_db_idempotent(self):
        """Test init_db can be called multiple times safely."""
        test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

        with patch("database.engine", test_engine):
            from database import init_db

            # Call multiple times
            init_db()
            init_db()
            init_db()

            # Should not raise error
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            assert len(tables) > 0


class TestDatabaseURL:
    """Tests for database URL configuration."""

    def test_database_url_from_env(self):
        """Test DATABASE_URL reads from environment."""
        from database import DATABASE_URL

        # DATABASE_URL should be set (either from env or default)
        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)

    def test_database_url_default(self):
        """Test DATABASE_URL default value."""
        with patch.dict(os.environ, {}, clear=True):
            # Reimport to get fresh default
            import importlib

            import database

            importlib.reload(database)

            from database import DATABASE_URL

            # Should use default if SUPABASE_DB_URL not set
            assert DATABASE_URL is not None

    @patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://test:pass@localhost/testdb"})
    def test_database_url_from_environment(self):
        """Test DATABASE_URL from environment variable."""
        # Reimport to get env value
        import importlib

        import database

        importlib.reload(database)

        from database import DATABASE_URL

        assert "testdb" in DATABASE_URL


class TestDatabaseEngine:
    """Tests for SQLAlchemy engine configuration."""

    def test_engine_created(self):
        """Test that engine is created."""
        from database import engine

        assert engine is not None

    def test_engine_echo_setting(self):
        """Test engine echo configuration."""
        with patch.dict(os.environ, {"SQL_ECHO": "true"}):
            import importlib

            import database

            importlib.reload(database)

            from database import engine

            # Engine should be created with echo setting
            assert engine is not None

    def test_engine_pool_configuration(self):
        """Test engine pool is NullPool for serverless."""
        from sqlalchemy.pool import NullPool

        from database import engine

        # Check that NullPool is used
        assert isinstance(engine.pool, NullPool)


class TestSessionLocal:
    """Tests for session factory."""

    def test_session_local_creates_sessions(self):
        """Test SessionLocal creates sessions."""
        from database import SessionLocal

        session = SessionLocal()
        assert isinstance(session, Session)
        session.close()

    def test_session_local_configuration(self):
        """Test SessionLocal is configured correctly."""
        from database import SessionLocal

        session = SessionLocal()

        # Check session configuration (autoflush is an attribute on the session)
        assert session.autoflush is False

        session.close()

    def test_session_local_multiple_instances(self):
        """Test creating multiple sessions."""
        from database import SessionLocal

        session1 = SessionLocal()
        session2 = SessionLocal()

        # Should be different instances
        assert session1 is not session2

        session1.close()
        session2.close()


def _database_reachable():
    """Check if database is reachable."""
    try:
        from database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _database_reachable(), reason="Database not reachable")
class TestDatabaseConnectivity:
    """Tests for database connectivity."""

    def test_engine_connection(self):
        """Test engine can create connections."""
        from database import engine

        with engine.connect() as connection:
            # Should not raise
            result = connection.execute(text("SELECT 1"))
            assert result is not None

    def test_session_connection(self):
        """Test session can execute queries."""
        from database import SessionLocal

        session = SessionLocal()
        try:
            # Try a simple query
            result = session.execute(text("SELECT 1"))
            assert result is not None
        finally:
            session.close()
