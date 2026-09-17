---
layout: home
title: HexaType - TypeScript Hexagonal Architecture Kit
titleTemplate: false
---

# HexaType

TypeScript/JavaScript Hexagonal Architecture Kit.

## Overview

`HexaType` is a lightweight, dependency-free hexagonal architecture kit for TypeScript/JavaScript applications. It provides structural patterns for building applications with Ports & Adapters.

## Features

- **Hexagonal Architecture**: Ports & Adapters pattern
- **Zero dependencies in domain**: Pure business logic
- **TypeScript-first**: Full type safety
- **Framework agnostic**: Works with any framework

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
│             Application Layer           │
└─────────────────────────────────────────┘
```

## Links

- [Repository](https://github.com/KooshaPari/hexatype)
