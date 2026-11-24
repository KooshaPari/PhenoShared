# State-of-the-Art Analysis: HexaPy

**Domain:** Python hexagonal architecture toolkit  
**Analysis Date:** 2026-04-02  
**Standard:** 4-Star Research Depth

---

## Executive Summary

HexaPy provides hexagonal architecture for Python. It competes against Python architecture patterns and frameworks.

---

## Alternative Comparison Matrix

### Tier 1: Python Architecture

| Solution | Type | DI | Async | Web | Maturity |
|----------|------|-----|-------|-----|----------|
| **Clean Architecture** | Book | Manual | ✅ | Any | L5 |
| **Architecture Patterns** | PyPI | lagom | ✅ | FastAPI | L4 |
| **fastapi-clean** | Example | Depends | ✅ | FastAPI | L3 |
| **django-ddd** | Example | Django | ❌ | Django | L3 |
| **lagom** | DI | Built-in | ✅ | Any | L4 |
| **dependency-injector** | DI | Built-in | ✅ | Any | L4 |
| **injector** | DI | Built-in | ✅ | Any | L4 |
| **apscheduler** | Jobs | Manual | ✅ | Any | L4 |
| **HexaPy (selected)** | [Type] | [DI] | [Async] | [Web] | L3 |

### Tier 2: Python Web Frameworks

| Solution | Type | Notes |
|----------|------|-------|
| **FastAPI** | Web | Modern |
| **Django** | Full | Batteries |
| **Flask** | Micro | Simple |

---

## Academic References

1. **"Architecture Patterns with Python"** (Percival & Gregory)
   - Python patterns
   - Application: HexaPy design

2. **"Clean Architecture"** (Martin, 2017)
   - Layer boundaries
   - Application: HexaPy structure

---

## Innovation Log

### HexaPy Novel Solutions

1. **[Innovation]**
   - **Innovation:** [Description]

---

## Gaps vs. SOTA

| Gap | SOTA | Status | Priority |
|-----|------|--------|----------|
| DI integration | lagom | [Status] | P1 |
| FastAPI support | FastAPI | [Status] | P2 |
| Async | AnyIO | [Status] | P2 |

---

**Next Update:** 2026-04-16
