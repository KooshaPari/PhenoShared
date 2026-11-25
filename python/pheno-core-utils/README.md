# Pheno Core Utils

Standalone utility library providing generic, reusable utilities for database connections, connection pooling, deployment checking, and vendor management.

## Features

- **Connection Pool** (`connection_pool.py`): Advanced connection pooling with health monitoring, background cleanup, and configurable pool sizing
- **Database Connection** (`db_connection.py`): Async and sync PostgreSQL connection management with connection pooling, health checks, and metrics
- **Deployment Checker** (`deployment_checker.py`): Comprehensive pre-deployment validation with configurable checks for code quality, tests, security, and more
- **Vendor Manager** (`vendor_manager.py`): Automated local package vendoring with setup, sync, and cleanup capabilities

## Installation

```bash
pip install pheno-core-utils
```

## Usage

### Connection Pool

```python
from pheno_core_utils import ConnectionPool, PoolConfig, PoolState

# Configure pool
config = PoolConfig(min_size=2, max_size=10, max_idle_time=300, max_lifetime=3600)


# Create pool with custom connection factory
def create_connection():
    # Your connection factory logic
    return connection


pool = ConnectionPool(config, create_connection)

# Use connection
with pool.get_connection() as conn:
    # Use connection
    pass

# Close pool
pool.close()
```

### Database Connection

```python
from pheno_core_utils import DatabaseManager, ConnectionConfig

# From environment variables
config = ConnectionConfig.from_env()

# Or manual configuration
config = ConnectionConfig(
    host="localhost", port=5432, database="mydb", user="postgres", password="secret"
)

# Create manager
db_manager = DatabaseManager(config)

# Async usage
async with db_manager.get_async_pool().get_connection() as conn:
    result = await conn.fetch("SELECT * FROM users")

# Sync usage
with db_manager.get_sync_pool().get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
```

### Deployment Checker

```python
from pheno_core_utils import ReadinessChecker, CheckPriority

# Create checker
checker = ReadinessChecker("/path/to/project")

# Run all checks
results = checker.run_all_checks(priorities=[CheckPriority.CRITICAL, CheckPriority.HIGH])

# Generate report
report = checker.generate_report(results, format="markdown")
print(report)

# Run single check
result = checker.run_check("check_database_health")
```

### Vendor Manager

```python
from pheno_core_utils import VendorManager

# Create manager
vm = VendorManager("vendor")

# Add package
vm.add_package("requests", version="2.28.0")

# List packages
packages = vm.list_packages(detailed=True)

# Sync all packages
vm.sync_packages()

# Verify packages
results = vm.verify_packages()
```

## Dependencies

- `asyncpg>=0.28.0` - Async PostgreSQL driver
- `psycopg2-binary>=2.9.0` - Sync PostgreSQL driver

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy src/pheno_core_utils
```

## License

MIT
