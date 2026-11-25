# Phenotype Python Specification

> Python SDK and utilities

## Overview

Python utilities and SDK for the Phenotype ecosystem.

## Components

### SDK Client
```python
class PhenotypeClient:
    def __init__(self, api_key: str, base_url: str = "...")
    def work_items(self) -> WorkItemClient
    def sprints(self) -> SprintClient
    def teams(self) -> TeamClient
```

### Utilities
- `phenotype.utils.retry` - Retry decorators
- `phenotype.utils.auth` - Authentication helpers
- `phenotype.utils.config` - Configuration loading

### Testing
- `phenotype.testing.fixtures` - Test fixtures
- `phenotype.testing.mocks` - Mock implementations

## Async Support

```python
from phenotype.async_client import AsyncClient

async with AsyncClient() as client:
    items = await client.work_items.list()
```
