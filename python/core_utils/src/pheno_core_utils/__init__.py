"""
Pheno Core Utils - Standalone utility library for database connections,
connection pooling, deployment checking, and vendor management.

This package provides generic, reusable utilities with no dependencies
on the pheno ecosystem, making it suitable for standalone use.
"""

# Connection Pool exports
from .connection_pool import (
    ConnectionPool,
    ConnectionWrapper,
    PoolConfig,
    PoolManager,
    PoolState,
    get_pool_manager,
)

# Database Connection exports
from .db_connection import (
    AsyncConnectionPool,
    ConnectionConfig,
    ConnectionMetrics,
    ConnectionStatus,
    DatabaseManager,
    HealthChecker,
    IsolationLevel,
    SyncConnectionPool,
    get_async_connection,
    get_db_manager,
    get_sync_connection,
)

# Deployment Checker exports
from .deployment_checker import (
    CheckPriority,
    CheckResult,
    CheckStatus,
    ReadinessChecker,
)

# Vendor Manager exports
from .vendor_manager import (
    PackageInfo,
    VendorManager,
)

__version__ = "0.1.0"

__all__ = [
    # Connection Pool
    "ConnectionPool",
    "ConnectionWrapper",
    "PoolConfig",
    "PoolManager",
    "PoolState",
    "get_pool_manager",
    # Database Connection
    "AsyncConnectionPool",
    "ConnectionConfig",
    "ConnectionMetrics",
    "ConnectionStatus",
    "DatabaseManager",
    "HealthChecker",
    "IsolationLevel",
    "SyncConnectionPool",
    "get_async_connection",
    "get_db_manager",
    "get_sync_connection",
    # Deployment Checker
    "CheckPriority",
    "CheckResult",
    "CheckStatus",
    "ReadinessChecker",
    # Vendor Manager
    "PackageInfo",
    "VendorManager",
]
