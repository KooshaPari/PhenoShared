#!/usr/bin/env python3
"""
Enhanced Database Connection Management Advanced connection handling with pooling and
health checks.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncContextManager

import asyncpg
from psycopg2 import pool
from psycopg2.extras import RealDictCursor


class ConnectionStatus(Enum):
    """
    Database connection status.
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    MAINTENANCE = "maintenance"


class IsolationLevel(Enum):
    """
    Transaction isolation levels.
    """

    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


@dataclass
class ConnectionConfig:
    """
    Database connection configuration.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "pheno"
    user: str = "postgres"
    password: str = ""
    sslmode: str = "prefer"
    application_name: str = "pheno-sdk"
    connect_timeout: int = 10
    command_timeout: int = 30
    idle_timeout: int = 300  # 5 minutes
    max_lifetime: int = 3600  # 1 hour
    pool_min_size: int = 2
    pool_max_size: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 30  # seconds

    @classmethod
    def from_env(cls) -> "ConnectionConfig":
        """
        Create config from environment variables.
        """
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "pheno"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            sslmode=os.getenv("DB_SSLMODE", "prefer"),
            application_name=os.getenv("DB_APP_NAME", "pheno-sdk"),
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
            command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "30")),
            idle_timeout=int(os.getenv("DB_IDLE_TIMEOUT", "300")),
            max_lifetime=int(os.getenv("DB_MAX_LIFETIME", "3600")),
            pool_min_size=int(os.getenv("DB_POOL_MIN", "2")),
            pool_max_size=int(os.getenv("DB_POOL_MAX", "10")),
            retry_attempts=int(os.getenv("DB_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("DB_RETRY_DELAY", "1.0")),
            health_check_interval=int(os.getenv("DB_HEALTH_CHECK_INTERVAL", "30")),
        )

    @property
    def dsn(self) -> str:
        """
        Generate DSN string.
        """
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.sslmode}&application_name={self.application_name}"
        )


@dataclass
class ConnectionMetrics:
    """
    Connection pool metrics.
    """

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    slow_queries: int = 0
    avg_query_time: float = 0.0
    last_health_check: datetime | None = None
    uptime: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class HealthChecker:
    """
    Database health checking.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._last_check = None
        self._status = ConnectionStatus.DISCONNECTED

    async def check_health(self) -> ConnectionStatus:
        """
        Perform comprehensive health check.
        """
        try:
            # Test basic connectivity
            conn = await asyncpg.connect(self.config.dsn, timeout=self.config.connect_timeout)

            # Test query execution
            result = await conn.fetchval("SELECT 1")

            # Check database size and limits
            db_size = await conn.fetchval(
                "SELECT pg_size_pretty(pg_database_size(current_database()))",
            )

            num_connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()",
            )

            await conn.close()

            if result == 1:
                self._status = ConnectionStatus.HEALTHY
                self._last_check = datetime.now()

                self.logger.info(
                    f"Database health check passed. "
                    f"Size: {db_size}, Connections: {num_connections}",
                )

            else:
                self._status = ConnectionStatus.UNHEALTHY

        except Exception as e:
            self._status = ConnectionStatus.UNHEALTHY
            self.logger.error(f"Database health check failed: {e}")

        return self._status

    @property
    def last_check(self) -> datetime | None:
        """
        Get last health check time.
        """
        return self._last_check

    @property
    def status(self) -> ConnectionStatus:
        """
        Get current status.
        """
        return self._status


class AsyncConnectionPool:
    """
    Async connection pool with advanced features.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.pool: asyncpg.Pool | None = None
        self.health_checker = HealthChecker(config)
        self.metrics = ConnectionMetrics()
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        self._startup_time = datetime.now()

    async def initialize(self) -> None:
        """
        Initialize connection pool.
        """
        async with self._lock:
            if self.pool and not self.pool._closed:
                return

            try:
                self.pool = await asyncpg.create_pool(
                    self.config.dsn,
                    min_size=self.config.pool_min_size,
                    max_size=self.config.pool_max_size,
                    command_timeout=self.config.command_timeout,
                    setup=self._setup_connection,
                    init=self._init_connection,
                )

                # Perform initial health check
                await self.health_checker.check_health()

                # Start health check task
                asyncio.create_task(self._health_check_loop())

                self.logger.info(
                    f"Connection pool initialized: {self.config.pool_min_size}-{self.config.pool_max_size} connections",
                )

            except Exception as e:
                self.logger.error(f"Failed to initialize connection pool: {e}")
                raise

    async def _setup_connection(self, conn: asyncpg.Connection) -> None:
        """
        Setup connection configuration.
        """
        # Set timezone
        await conn.execute("SET timezone TO 'UTC'")

        # Set search path
        await conn.execute("SET search_path TO public, pheno")

        # Configure statement timeout
        await conn.execute(f"SET statement_timeout TO {self.config.command_timeout}s")

        # Enable better analyzer
        await conn.execute("SET enable_seqscan = off")

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        """
        Initialize connection with custom settings.
        """
        # This is called after connection is established from pool

    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """
        Get connection from pool.
        """
        if not self.pool or self.pool._closed:
            await self.initialize()

        start_time = time.time()

        try:
            async with self.pool.acquire() as conn:
                self.metrics.active_connections += 1
                yield conn

        except Exception as e:
            self.metrics.failed_connections += 1
            self.logger.error(f"Connection error: {e}")
            raise
        finally:
            self.metrics.active_connections -= 1
            query_time = time.time() - start_time
            self.metrics.avg_query_time = (
                self.metrics.avg_query_time * self.metrics.total_queries + query_time
            ) / (self.metrics.total_queries + 1)
            self.metrics.total_queries += 1

            if query_time > 5.0:  # Slow query threshold
                self.metrics.slow_queries += 1
                self.logger.warning(f"Slow query detected: {query_time:.2f}s")

    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Execute query and return result.
        """
        async with self.get_connection() as conn:
            return await conn.execute(query, *args, **kwargs)

    async def fetch(self, query: str, *args, **kwargs) -> list:
        """
        Execute query and return results.
        """
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """
        Execute query and return single value.
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    async def fetchrow(self, query: str, *args, **kwargs) -> asyncpg.Record:
        """
        Execute query and return single row.
        """
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def _health_check_loop(self) -> None:
        """
        Background health check loop.
        """
        try:
            while self.pool and not self.pool._closed:
                await asyncio.sleep(self.config.health_check_interval)

                old_status = self.health_checker.status
                new_status = await self.health_checker.check_health()

                if old_status != new_status:
                    self.logger.info(
                        f"Database status changed: {old_status.value} -> {new_status.value}",
                    )

                self.metrics.last_health_check = self.health_checker.last_check

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Health check loop error: {e}")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get pool metrics.
        """
        if self.pool:
            self.metrics.total_connections = self.pool.get_size()
            self.metrics.idle_connections = self.pool.get_idle_size()

        return {
            "connections": {
                "total": self.metrics.total_connections,
                "active": self.metrics.active_connections,
                "idle": self.metrics.idle_connections,
                "failed": self.metrics.failed_connections,
            },
            "queries": {
                "total": self.metrics.total_queries,
                "slow": self.metrics.slow_queries,
                "avg_time": self.metrics.avg_query_time,
            },
            "health": {
                "status": self.health_checker.status.value,
                "last_check": (
                    self.health_checker.last_check.isoformat()
                    if self.health_checker.last_check
                    else None
                ),
            },
            "uptime": (datetime.now() - self._startup_time).total_seconds(),
        }

    async def close(self) -> None:
        """
        Close connection pool.
        """
        if self.pool and not self.pool._closed:
            await self.pool.close()
            self.logger.info("Connection pool closed")


class SyncConnectionPool:
    """
    Synchronous connection pool using psycopg2.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.pool: pool.ThreadedConnectionPool | None = None
        self.metrics = ConnectionMetrics()
        self.logger = logging.getLogger(__name__)
        self._startup_time = datetime.now()

    def initialize(self) -> None:
        """
        Initialize connection pool.
        """
        try:
            self.pool = pool.ThreadedConnectionPool(
                minconn=self.config.pool_min_size,
                maxconn=self.config.pool_max_size,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                sslmode=self.config.sslmode,
                application_name=self.config.application_name,
                connect_timeout=self.config.connect_timeout,
            )

            self.logger.info("Sync connection pool initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize sync connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self) -> Any:
        """
        Get connection from pool.
        """
        if not self.pool or self.pool.closed:
            self.initialize()

        conn = None
        start_time = time.time()

        try:
            conn = self.pool.getconn()
            self.metrics.active_connections += 1

            # Setup connection
            with conn.cursor() as cursor:
                cursor.execute("SET timezone TO 'UTC'")
                cursor.execute("SET statement_timeout TO '%s'", (self.config.command_timeout,))

            yield conn

        except Exception as e:
            self.metrics.failed_connections += 1
            self.logger.error(f"Sync connection error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)
                self.metrics.active_connections -= 1

            query_time = time.time() - start_time
            self.metrics.total_queries += 1
            self.metrics.avg_query_time = (
                self.metrics.avg_query_time * (self.metrics.total_queries - 1) + query_time
            ) / self.metrics.total_queries

    def execute(self, query: str, params: tuple = None) -> Any:
        """
        Execute query and return results.
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)

                if cursor.description:
                    return cursor.fetchall()
                return cursor.rowcount

    def get_metrics(self) -> dict[str, Any]:
        """
        Get pool metrics.
        """
        if self.pool:
            self.metrics.total_connections = self.pool.minconn + self.pool.maxconn
            # ThreadedConnectionPool doesn't expose idle connection count easily

        return {
            "connections": {
                "total": self.metrics.total_connections,
                "active": self.metrics.active_connections,
                "idle": "N/A",  # Not available in threaded pool
                "failed": self.metrics.failed_connections,
            },
            "queries": {
                "total": self.metrics.total_queries,
                "slow": self.metrics.slow_queries,
                "avg_time": self.metrics.avg_query_time,
            },
            "uptime": (datetime.now() - self._startup_time).total_seconds(),
        }

    def close(self) -> None:
        """
        Close connection pool.
        """
        if self.pool and not self.pool.closed:
            self.pool.closeall()
            self.logger.info("Sync connection pool closed")


class DatabaseManager:
    """
    Unified database manager supporting both async and sync operations.
    """

    def __init__(self, config: ConnectionConfig = None):
        self.config = config or ConnectionConfig.from_env()
        self.async_pool: AsyncConnectionPool | None = None
        self.sync_pool: SyncConnectionPool | None = None
        self.logger = logging.getLogger(__name__)

    async def initialize_async(self) -> None:
        """
        Initialize async connection pool.
        """
        self.async_pool = AsyncConnectionPool(self.config)
        await self.async_pool.initialize()

    def initialize_sync(self) -> None:
        """
        Initialize sync connection pool.
        """
        self.sync_pool = SyncConnectionPool(self.config)
        self.sync_pool.initialize()

    async def get_async_pool(self) -> AsyncConnectionPool:
        """
        Get async connection pool.
        """
        if not self.async_pool:
            await self.initialize_async()
        return self.async_pool

    def get_sync_pool(self) -> SyncConnectionPool:
        """
        Get sync connection pool.
        """
        if not self.sync_pool:
            self.initialize_sync()
        return self.sync_pool

    async def health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive health check.
        """
        async_pool = await self.get_async_pool()
        status = await async_pool.health_checker.check_health()

        metrics = async_pool.get_metrics()

        return {
            "status": status.value,
            "metrics": metrics,
            "config": {
                "database": self.config.database,
                "host": self.config.host,
                "pool_size": f"{self.config.pool_min_size}-{self.config.pool_max_size}",
            },
        }

    def get_all_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive metrics.
        """
        metrics = {}

        if self.async_pool:
            metrics["async"] = self.async_pool.get_metrics()

        if self.sync_pool:
            metrics["sync"] = self.sync_pool.get_metrics()

        return metrics

    async def close_all(self) -> None:
        """
        Close all connection pools.
        """
        if self.async_pool:
            await self.async_pool.close()

        if self.sync_pool:
            self.sync_pool.close()

    @classmethod
    def from_env(cls) -> "DatabaseManager":
        """
        Create database manager from environment.
        """
        return cls(ConnectionConfig.from_env())


# Global instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager.from_env()
    return _db_manager


async def get_async_connection():
    """
    Get async database connection (convenience function)
    """
    db_manager = get_db_manager()
    async_pool = await db_manager.get_async_pool()
    return async_pool.get_connection()


def get_sync_connection():
    """
    Get sync database connection (convenience function)
    """
    db_manager = get_db_manager()
    sync_pool = db_manager.get_sync_pool()
    return sync_pool.get_connection()
