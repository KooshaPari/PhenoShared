# Product Requirements Document — template-lang-zig

**Product:** Phenotype Zig Language Templates
**Template Version:** 0.1.0
**Date:** 2026-04-02

## Purpose

Provide production-ready Zig project templates that follow Phenotype platform conventions and Zig ecosystem best practices.

## Target Users

1. **Systems Programmers** - Building performance-critical tools
2. **Tool Developers** - Creating CLI utilities
3. **Embedded Engineers** - Resource-constrained environments

## Problem Statement

Starting a new Zig project requires:
- build.zig configuration
- Project structure setup
- Error handling patterns
- Memory management scaffolding

This template accelerates onboarding.

## Solution

### Core Templates

1. **phenotype-zig-cli**
   - Command-line tool structure
   - Cross-platform support
   - Performance optimization

2. **hexagonal-zig**
   - Hexagonal architecture
   - Port/adapter patterns
   - Domain separation

### Key Features

- **Zig 0.12+** - Modern Zig syntax
- **Native Build** - build.zig system
- **Error Sets** - Type-safe errors
- **Comptime** - Compile-time execution
- **C Interop** - Seamless C integration

## User Stories

### US-ZIG-001: Generate New CLI Tool
**As a** tool developer
**I want to** generate a new Zig CLI
**So that** I can build fast utilities

### US-ZIG-002: Use Idiomatic Zig
**As a** systems programmer
**I want to** follow Zig patterns
**So that** my code is idiomatic

## Success Metrics

| Metric | Target |
|--------|--------|
| Build time | < 5 seconds |
| Binary size | Minimal |
| Test suite passing | 100% |

## Constraints

- Must use Zig 0.12+
- Must use native build system
- Error handling required
- Memory management explicit
