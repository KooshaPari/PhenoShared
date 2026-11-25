# State-of-the-Art Analysis: Hexacore

**Domain:** Hexagonal architecture core library  
**Analysis Date:** 2026-04-02  
**Standard:** 4-Star Research Depth

---

## Executive Summary

Hexacore provides hexagonal architecture primitives. It competes against architecture frameworks and patterns libraries.

---

## Alternative Comparison Matrix

### Tier 1: Architecture Frameworks

| Solution | Language | Pattern | DI | Testing | Maturity |
|----------|----------|---------|-----|---------|----------|
| **Clean Architecture** | Multi | Ports/Adapters | Manual | ✅ | L5 |
| **Hexagonal** | Multi | Ports/Adapters | Manual | ✅ | L5 |
| **Onion Architecture** | .NET | Layers | DI | ✅ | L4 |
| **Vertical Slice** | .NET | Features | MediatR | ✅ | L4 |
| **CQRS** | Multi | Commands/Queries | Bus | ✅ | L5 |
| **Event Sourcing** | Multi | Events | Event store | ✅ | L4 |
| **lagom** | Python | Ports/Adapters | Built-in | ✅ | L4 |
| **NestJS** | Node.js | Modules | Built-in | ✅ | L5 |
| **Hexacore (selected)** | [Lang] | [Pattern] | [DI] | [Test] | L3 |

### Tier 2: DI Containers

| Solution | Language | Type | Notes |
|----------|----------|------|-------|
| **google/wire** | Go | Compile-time | Code gen |
| **dig** | Go | Runtime | Uber |
| **dependency-injector** | Python | Runtime | Names |

---

## Academic References

1. **"Hexagonal Architecture"** (Cockburn, 2005)
   - Ports and adapters
   - Application: Hexacore design

2. **"Clean Architecture"** (Martin, 2017)
   - Dependency rule
   - Application: Hexacore principles

---

## Innovation Log

### Hexacore Novel Solutions

1. **[Innovation]**
   - **Innovation:** [Description]

---

## Gaps vs. SOTA

| Gap | SOTA | Status | Priority |
|-----|------|--------|----------|
| DI integration | lagom | [Status] | P1 |
| Testing support | Clean Arch | [Status] | P2 |
| Documentation | Martin | [Status] | P2 |

---

**Next Update:** 2026-04-16
