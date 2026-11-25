# State-of-the-Art Analysis: HexaGo

**Domain:** Go hexagonal architecture toolkit  
**Analysis Date:** 2026-04-02  
**Standard:** 4-Star Research Depth

---

## Executive Summary

HexaGo provides hexagonal architecture for Go. It competes against Go architecture patterns and frameworks.

---

## Alternative Comparison Matrix

### Tier 1: Go Architecture

| Solution | Type | DI | Testing | Web | Maturity |
|----------|------|-----|---------|-----|----------|
| **Standard Layout** | Community | Manual | ✅ | Any | L5 |
| **go-clean-arch** | Template | Manual | ✅ | Gin | L4 |
| **wild-workouts** | Example | Wire | ✅ | Any | L4 |
| **ThreeDotsLabs** | Patterns | Watermill | ✅ | Any | L4 |
| **go-hexagonal** | Framework | Built-in | ✅ | HTTP | L3 |
| **gobuffalo** | Full | Built-in | ✅ | Buffalo | L4 |
| **go-kit** | Microservices | Manual | ✅ | HTTP/gRPC | L5 |
| **go-zero** | Microservices | Built-in | ✅ | HTTP | L4 |
| **HexaGo (selected)** | [Type] | [DI] | [Test] | [Web] | L3 |

### Tier 2: Go Web Frameworks

| Solution | Type | Notes |
|----------|------|-------|
| **Gin** | Web | Fast |
| **Echo** | Web | Minimal |
| **Fiber** | Web | Express-like |

---

## Academic References

1. **"Go Clean Architecture"** (ThreeDotsLabs)
   - Go patterns
   - Application: HexaGo structure

2. **"Domain-Driven Design in Go"** (community)
   - Go DDD patterns
   - Application: HexaGo domain layer

---

## Innovation Log

### HexaGo Novel Solutions

1. **[Innovation]**
   - **Innovation:** [Description]

---

## Gaps vs. SOTA

| Gap | SOTA | Status | Priority |
|-----|------|--------|----------|
| Standard layout | Community | [Status] | P1 |
| DI | Wire/dig | [Status] | P2 |
| Testing | Clean arch | [Status] | P2 |

---

**Next Update:** 2026-04-16
