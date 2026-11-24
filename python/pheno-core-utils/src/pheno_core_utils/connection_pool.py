#!/usr/bin/env python3
"""
Advanced Connection Pool Implementation High-performance connection pooling with
advanced features.
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PoolState(Enum):
    """
    Connection pool states.
    """

    INITIALIZING = "initializing"
    READY = "ready"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionWrapper:
    """
    Wrapper for database connections with metadata.
    """

    connection: Any
    created_at: float
    last_used: float
    usage_count: int = 0
    is_active: bool = True
    checkout_count: int = 0

    def age(self) -> float:
        """
        Get connection age in seconds.
        """
        return time.time() - self.created_at

    def idle_time(self) -> float:
        """
        Get idle time in seconds.
        """
        return time.time() - self.last_used


@dataclass
class PoolConfig:
    """
    Connection pool configuration.
    """

    min_size: int = 2
    max_size: int = 10
    max_idle_time: int = 300  # 5 minutes
    max_lifetime: int = 3600  # 1 hour
    max_overflow: int = 5
    checkout_timeout: int = 30
    health_check_interval: int = 60
    connection_factory: Callable | None = None
    test_on_borrow: bool = True
    test_on_return: bool = False
    test_while_idle: bool = True

    def validate(self) -> None:
        """
        Validate configuration.
        """
        if self.min_size < 0:
            raise ValueError("min_size must be >= 0")
        if self.max_size <= self.min_size:
            raise ValueError("max_size must be > min_size")
        if self.max_overflow < 0:
            raise ValueError("max_overflow must be >= 0")
        if self.checkout_timeout <= 0:
            raise ValueError("checkout_timeout must be > 0")


class ConnectionPool:
    """
    Advanced connection pool with health monitoring.
    """

    def __init__(self, config: PoolConfig, connection_factory: Callable):
        config.validate()
        self.config = config
        self.connection_factory = connection_factory

        # Pool state
        self._state = PoolState.INITIALIZING
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        # Connection storage
        self._available_connections: deque[ConnectionWrapper] = deque()
        self._active_connections: set[ConnectionWrapper] = set()
        self._overflow_connections: set[ConnectionWrapper] = set()

        # Monitoring
        self._created_count = 0
        self._destroyed_count = 0
        self._checkout_count = 0
        self._return_count = 0
        self._error_count = 0
        self._last_health_check = 0.0

        # Background tasks
        self._cleanup_thread: threading.Thread | None = None
        self._health_check_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

        # Statistics
        self.stats = {
            "pool_size": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "overflow_connections": 0,
            "total_connections": 0,
            "created": 0,
            "destroyed": 0,
            "checkouts": 0,
            "returns": 0,
            "errors": 0,
        }

        self.logger = logging.getLogger(__name__)

        # Initialize pool
        self._initialize()

    def _initialize(self) -> None:
        """
        Initialize the connection pool.
        """
        try:
            with self._lock:
                # Create minimum connections
                for _ in range(self.config.min_size):
                    conn_wrapper = self._create_connection()
                    if conn_wrapper:
                        self._available_connections.append(conn_wrapper)

                # Start background maintenance tasks
                self._cleanup_thread = threading.Thread(
                    target=self._cleanup_worker,
                    name=f"{self.__class__.__name__}-cleanup",
                    daemon=True,
                )
                self._cleanup_thread.start()

                self._health_check_thread = threading.Thread(
                    target=self._health_check_worker,
                    name=f"{self.__class__.__name__}-health",
                    daemon=True,
                )
                self._health_check_thread.start()

                self._state = PoolState.READY
                self.logger.info(
                    f"Connection pool initialized with {len(self._available_connections)} connections",
                )

        except Exception as e:
            self._state = PoolState.ERROR
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def _create_connection(self) -> ConnectionWrapper | None:
        """
        Create a new database connection.
        """
        try:
            conn = self.connection_factory()
            if not conn:
                return None

            conn_wrapper = ConnectionWrapper(
                connection=conn,
                created_at=time.time(),
                last_used=time.time(),
            )

            self._created_count += 1
            return conn_wrapper

        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Failed to create connection: {e}")
            return None

    def _destroy_connection(self, conn_wrapper: ConnectionWrapper) -> None:
        """
        Destroy a database connection.
        """
        try:
            if hasattr(conn_wrapper.connection, "close"):
                conn_wrapper.connection.close()
            self._destroyed_count += 1

        except Exception as e:
            self.logger.warning(f"Error closing connection: {e}")

    def _is_connection_healthy(self, conn_wrapper: ConnectionWrapper) -> bool:
        """
        Check if connection is healthy.
        """
        try:
            conn = conn_wrapper.connection

            # Check age
            if conn_wrapper.age() > self.config.max_lifetime:
                return False

            # Check idle time
            if conn_wrapper.idle_time() > self.config.max_idle_time:
                return False

            # Test connection if configured
            if hasattr(conn, "ping"):  # MySQL-style
                conn.ping()
            elif hasattr(conn, "connection"):  # PostgreSQL-style
                conn.connection.poll()
            elif hasattr(conn, "execute"):  # Generic SQL test
                conn.execute("SELECT 1")

            return True

        except Exception as e:
            self.logger.debug(f"Connection health check failed: {e}")
            return False

    @contextmanager
    def get_connection(self, timeout: float | None = None):
        """
        Get a connection from the pool.
        """
        timeout = timeout or self.config.checkout_timeout
        start_time = time.time()

        with self._lock:
            while time.time() - start_time < timeout:
                # Try to get an available connection
                if self._available_connections:
                    conn_wrapper = self._available_connections.popleft()

                    # Validate connection
                    if self.config.test_on_borrow and not self._is_connection_healthy(conn_wrapper):
                        self._destroy_connection(conn_wrapper)
                        continue

                    # Move to active connections
                    conn_wrapper.last_used = time.time()
                    conn_wrapper.usage_count += 1
                    conn_wrapper.checkout_count += 1
                    self._active_connections.add(conn_wrapper)
                    self._checkout_count += 1

                    # Update stats
                    self._update_stats()

                    try:
                        yield conn_wrapper.connection
                        return

                    finally:
                        # Return connection to pool
                        self._return_connection(conn_wrapper)

                # Create new connection if under max_size
                total_connections = len(self._available_connections) + len(self._active_connections)

                if total_connections < self.config.max_size:
                    conn_wrapper = self._create_connection()
                    if conn_wrapper:
                        conn_wrapper.checkout_count += 1
                        self._active_connections.add(conn_wrapper)
                        self._checkout_count += 1
                        self._update_stats()

                        try:
                            yield conn_wrapper.connection
                            return

                        finally:
                            self._return_connection(conn_wrapper)

                # Wait for a connection to become available
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 0:
                    self._condition.wait(remaining_time)
                else:
                    break

            # Timeout reached
            raise TimeoutError(f"Failed to get connection within {timeout} seconds")

    def _return_connection(self, conn_wrapper: ConnectionWrapper) -> None:
        """
        Return a connection to the pool.
        """
        with self._lock:
            if conn_wrapper not in self._active_connections:
                return  # Already returned

            self._active_connections.remove(conn_wrapper)
            self._return_count += 1

            # Test connection on return if configured
            if self.config.test_on_return and not self._is_connection_healthy(conn_wrapper):
                self._destroy_connection(conn_wrapper)
                self._update_stats()
                return

            # Return to available connections if under limit
            total_connections = len(self._available_connections) + len(self._active_connections)
            if total_connections <= self.config.max_size:
                conn_wrapper.last_used = time.time()
                self._available_connections.append(conn_wrapper)
            else:
                # Pool is full, destroy the connection
                self._destroy_connection(conn_wrapper)

            self._update_stats()
            self._condition.notify()  # Notify waiting threads

    def _cleanup_worker(self) -> None:
        """
        Background cleanup worker thread.
        """
        while not self._shutdown_event.wait(30):  # Check every 30 seconds
            try:
                self._cleanup_idle_connections()
                self._cleanup_expired_connections()

            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}")

    def _cleanup_idle_connections(self) -> None:
        """
        Remove idle connections that have been inactive too long.
        """
        with self._lock:
            current_time = time.time()
            to_remove = []

            # Check available connections
            for conn_wrapper in self._available_connections:
                if current_time - conn_wrapper.last_used > self.config.max_idle_time:
                    # Keep minimum connections
                    if len(self._available_connections) - len(to_remove) > self.config.min_size:
                        to_remove.append(conn_wrapper)

            # Remove connections
            for conn_wrapper in to_remove:
                self._available_connections.remove(conn_wrapper)
                self._destroy_connection(conn_wrapper)

            if to_remove:
                self.logger.debug(f"Cleaned up {len(to_remove)} idle connections")
                self._update_stats()

    def _cleanup_expired_connections(self) -> None:
        """
        Remove connections that have exceeded their lifetime.
        """
        with self._lock:
            current_time = time.time()
            to_remove = []

            # Check available connections
            for conn_wrapper in self._available_connections:
                if current_time - conn_wrapper.created_at > self.config.max_lifetime:
                    # Keep minimum connections if they're not expired
                    if conn_wrapper.age() > self.config.max_lifetime:
                        to_remove.append(conn_wrapper)

            # Remove connections
            for conn_wrapper in to_remove:
                self._available_connections.remove(conn_wrapper)
                self._destroy_connection(conn_wrapper)

            if to_remove:
                self.logger.debug(f"Cleaned up {len(to_remove)} expired connections")
                self._update_stats()

    def _health_check_worker(self) -> None:
        """
        Background health check worker thread.
        """
        while not self._shutdown_event.wait(self.config.health_check_interval):
            try:
                if self.config.test_while_idle:
                    self._health_check_idle_connections()

                self._last_health_check = time.time()

            except Exception as e:
                self.logger.error(f"Health check worker error: {e}")

    def _health_check_idle_connections(self) -> None:
        """
        Check health of idle connections.
        """
        with self._lock:
            to_remove = []

            for conn_wrapper in self._available_connections:
                if not self._is_connection_healthy(conn_wrapper):
                    to_remove.append(conn_wrapper)

            # Remove unhealthy connections
            for conn_wrapper in to_remove:
                self._available_connections.remove(conn_wrapper)
                self._destroy_connection(conn_wrapper)

            # Replace unhealthy connections if under minimum
            current_size = len(self._available_connections)
            if current_size < self.config.min_size:
                for _ in range(self.config.min_size - current_size):
                    conn_wrapper = self._create_connection()
                    if conn_wrapper:
                        self._available_connections.append(conn_wrapper)

            if to_remove:
                self.logger.info(f"Removed {len(to_remove)} unhealthy connections")
                self._update_stats()

    def _update_stats(self) -> None:
        """
        Update pool statistics.
        """
        self.stats.update(
            {
                "pool_size": len(self._available_connections) + len(self._active_connections),
                "active_connections": len(self._active_connections),
                "idle_connections": len(self._available_connections),
                "overflow_connections": len(self._overflow_connections),
                "total_connections": self._created_count,
                "created": self._created_count,
                "destroyed": self._destroyed_count,
                "checkouts": self._checkout_count,
                "returns": self._return_count,
                "errors": self._error_count,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.
        """
        with self._lock:
            stats = self.stats.copy()
            stats.update(
                {
                    "state": self._state.value,
                    "config": {
                        "min_size": self.config.min_size,
                        "max_size": self.config.max_size,
                        "max_idle_time": self.config.max_idle_time,
                        "max_lifetime": self.config.max_lifetime,
                    },
                    "last_health_check": self._last_health_check,
                },
            )
            return stats

    def resize(self, min_size: int = None, max_size: int = None) -> None:
        """
        Resize the connection pool.
        """
        with self._lock:
            old_min, old_max = self.config.min_size, self.config.max_size

            # Update configuration
            if min_size is not None:
                self.config.min_size = min_size
            if max_size is not None:
                self.config.max_size = max_size

            # Validate new configuration
            self.config.validate()

            # Adjust connections if needed
            current_size = len(self._available_connections)

            # Increase minimum connections
            if self.config.min_size > old_min and current_size < self.config.min_size:
                needed = self.config.min_size - current_size
                for _ in range(needed):
                    conn_wrapper = self._create_connection()
                    if conn_wrapper:
                        self._available_connections.append(conn_wrapper)

            # Decrease minimum connections
            elif self.config.min_size < old_min and current_size > self.config.min_size:
                excess = current_size - self.config.min_size
                to_remove = list(self._available_connections)[:excess]
                for conn_wrapper in to_remove:
                    self._available_connections.remove(conn_wrapper)
                    self._destroy_connection(conn_wrapper)

            self._update_stats()
            self.logger.info(
                f"Pool resized from {old_min}-{old_max} to "
                f"{self.config.min_size}-{self.config.max_size}",
            )

    def close(self) -> None:
        """
        Close the connection pool.
        """
        with self._lock:
            if self._state in [PoolState.CLOSING, PoolState.CLOSED]:
                return

            self._state = PoolState.CLOSING

            # Signal shutdown to background threads
            self._shutdown_event.set()

            # Close all connections
            all_connections = list(self._available_connections) + list(self._active_connections)

            for conn_wrapper in all_connections:
                self._destroy_connection(conn_wrapper)

            self._available_connections.clear()
            self._active_connections.clear()
            self._overflow_connections.clear()

            self._state = PoolState.CLOSED
            self.logger.info("Connection pool closed")

    def __del__(self):
        """
        Destructor to ensure cleanup.
        """
        if self._state not in [PoolState.CLOSING, PoolState.CLOSED]:
            self.close()


class PoolManager:
    """
    Manages multiple named connection pools.
    """

    def __init__(self):
        self._pools: dict[str, ConnectionPool] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def create_pool(
        self,
        name: str,
        config: PoolConfig,
        connection_factory: Callable,
    ) -> ConnectionPool:
        """
        Create a new named connection pool.
        """
        with self._lock:
            if name in self._pools:
                raise ValueError(f"Pool '{name}' already exists")

            pool = ConnectionPool(config, connection_factory)
            self._pools[name] = pool

            self.logger.info(f"Created connection pool: {name}")
            return pool

    def get_pool(self, name: str) -> ConnectionPool | None:
        """
        Get an existing connection pool.
        """
        with self._lock:
            return self._pools.get(name)

    def remove_pool(self, name: str) -> bool:
        """
        Remove a connection pool.
        """
        with self._lock:
            if name in self._pools:
                pool = self._pools.pop(name)
                pool.close()
                self.logger.info(f"Removed connection pool: {name}")
                return True
            return False

    def close_all(self) -> None:
        """
        Close all connection pools.
        """
        with self._lock:
            for pool in self._pools.values():
                pool.close()
            self._pools.clear()
            self.logger.info("All connection pools closed")

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all pools.
        """
        with self._lock:
            return {name: pool.get_stats() for name, pool in self._pools.items()}


# Global pool manager instance
_pool_manager = PoolManager()


def get_pool_manager() -> PoolManager:
    """
    Get the global pool manager.
    """
    return _pool_manager
