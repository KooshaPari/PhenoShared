# Phenotype Python

> Python utilities and SDK for Phenotype ecosystem

## Overview

Phenotype Python provides shared utilities, SDK clients, and tools for Python-based services in the Phenotype ecosystem.

## Features

- **SDK Client**: HTTP client for Phenotype APIs
- **Utilities**: Common functions and helpers
- **Testing**: Test fixtures and utilities
- **Async Support**: asyncio-compatible components

## Quick Start

```bash
# Install
pip install phenotype-python

# Use SDK
from phenotype import Client

client = Client(api_key="your-key")
result = client.work_items.list()
```

## Documentation

- [Specification](SPEC.md) - Technical details
- [Implementation Plan](PLAN.md) - Development roadmap

## License

MIT
