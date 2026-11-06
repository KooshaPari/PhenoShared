# Test Coverage Matrix - Stashly

**Project**: Stashly
**Document Version**: 1.1
**Last Updated**: 2026-04-02

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| Functional Requirements | 12 (see FR-CACHE, FR-BACKEND, FR-TTL, FR-EVICT) |
| Test Files | 0 |
| Test Functions | 0 |
| Lines of Code | 713 |
| Coverage Target | 80% |
| Current Coverage | 0% |

---

## Architecture

Hexagonal (Ports & Adapters):
- **Domain**: `src/domain/` - Pure business logic
- **Application**: `src/application/` - Use cases
- **Adapters**: `src/adapters/` - Implementations
- **Infrastructure**: `src/infrastructure/` - External concerns

---

## Test Categories

### Unit Tests
- **Location**: `src/**/*_test.rs`
- **Purpose**: Test individual components in isolation
- **Coverage Target**: 90%
- **Status**: NOT IMPLEMENTED

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test component interactions
- **Coverage Target**: 75%
- **Status**: NOT IMPLEMENTED

### Property-Based Tests
- **Location**: `tests/property/`
- **Purpose**: Randomized testing with shrinking
- **Coverage Target**: Key invariants
- **Status**: NOT IMPLEMENTED

---

## FR to Test Coverage Mapping

| FR ID | Description | Module | Test File | Coverage Status |
|-------|-------------|--------|-----------|-----------------|
| FR-CACHE-001 | get() method | domain/cache.rs | TBD | NOT COVERED |
| FR-CACHE-002 | put() method | domain/cache.rs | TBD | NOT COVERED |
| FR-CACHE-003 | delete() method | domain/cache.rs | TBD | NOT COVERED |
| FR-CACHE-004 | Async support | adapters/ | TBD | NOT COVERED |
| FR-BACKEND-001 | In-memory backend | adapters/memory.rs | TBD | NOT COVERED |
| FR-BACKEND-002 | Redis backend | adapters/redis.rs | TBD | NOT COVERED |
| FR-BACKEND-003 | Backend trait | domain/backend.rs | TBD | NOT COVERED |
| FR-TTL-001 | Entry TTL | domain/entry.rs | TBD | NOT COVERED |
| FR-TTL-002 | Auto expiration | application/ | TBD | NOT COVERED |
| FR-TTL-003 | TTL options | domain/entry.rs | TBD | NOT COVERED |
| FR-EVICT-001 | LRU policy | domain/eviction.rs | TBD | NOT COVERED |
| FR-EVICT-002 | LFU policy | domain/eviction.rs | TBD | NOT COVERED |
| FR-EVICT-003 | FIFO policy | domain/eviction.rs | TBD | NOT COVERED |

---

## Test File Index

| Test File | Purpose | FRs Covered |
|-----------|---------|-------------|
| NONE | Tests need to be created | N/A |

---

## Coverage Gaps

### Critical Gaps
1. **No tests exist** - All 12 FRs lack test coverage
2. Domain types not tested
3. Backend adapters not tested
4. Eviction policies not tested

### Partial Coverage
1. N/A - No coverage exists

---

## Recommendations

### Immediate Actions (This Week)
1. Create `src/domain/cache_test.rs` with tests for FR-CACHE-001/002/003
2. Create `src/domain/entry_test.rs` with tests for FR-TTL-001/003
3. Create `src/domain/eviction_test.rs` with tests for FR-EVICT-001/002/003

### Short-term Actions (This Sprint)
1. Add integration tests for backend adapters
2. Add property-based tests for serialization
3. Target: 60% coverage

### Medium-term Actions (This Month)
1. Add Redis integration tests
2. Add performance benchmarks
3. Target: 80% coverage

---

**Total Functional Requirements**: 12
**Covered**: 0
**Coverage Percentage**: 0%
**Last Updated**: 2026-04-02
