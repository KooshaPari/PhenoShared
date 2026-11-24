---
layout: home
title: HexaPy - Hexagonal Architecture Kit for Python
titleTemplate: false
---

# HexaPy

Hexagonal Architecture Kit for Python.

## Overview

`HexaPy` is a lightweight, dependency-free hexagonal architecture kit for Python applications. It provides structural patterns for building applications with Ports & Adapters while respecting Python's idioms.

## Features

- **Hexagonal Architecture**: Ports & Adapters pattern
- **Zero dependencies in domain**: Pure business logic
- **Event sourcing support**: Built-in domain events
- **Async support**: Full async/await compatibility

## Architecture

```
┌─────────────────────────────────────────┐
│              Adapters Layer              │
├─────────────────────────────────────────┤
│                Ports Layer               │
├─────────────────────────────────────────┤
│               Domain Layer               │
│        (ZERO external dependencies)      │
├─────────────────────────────────────────┤
│             Application Layer            │
└─────────────────────────────────────────┘
```

## Quick Start

```python
from pyhex import Domain, Port, Adapter

class MyDomain(Domain):
    def business_logic(self, input_data):
        # Pure business logic, no dependencies
        return self.transform(input_data)
```

## Links

- [Repository](https://github.com/KooshaPari/hexapy)
