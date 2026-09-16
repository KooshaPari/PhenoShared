# Test Coverage Matrix

**Project**: phenotype-vessel  
**Document Version**: 1.1  
**Last Updated**: 2026-04-02

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| Functional Requirements | 24 (FR-VESSEL-INTEGRATION-001 to 024) |
| Test Files | 2 (lib.rs:12, tests/integration.rs:24) |
| Test Functions | 36 (12 unit + 24 integration) |
| Coverage Target | 80% |
| Current Coverage | ~75% (estimated) |

---

## Test Categories

### Unit Tests
- **Location**: `src/*.rs` (#[cfg(test)] modules)
- **Purpose**: Test individual components in isolation
- **Count**: 12 tests
- **Coverage Target**: 90%

### Integration Tests
- **Location**: `tests/integration.rs`
- **Purpose**: Test ContainerClient API and runtime interactions
- **Count**: 24 tests
- **Coverage Target**: 75%

---

## FR to Test Coverage Mapping

| FR ID | Description | Test Location | Status |
|-------|-------------|--------------|--------|
| FR-VESSEL-001 | ContainerRuntime trait definition | src/runtime.rs | N/A |
| FR-VESSEL-002 | ContainerStatus display | src/container.rs | Covered |
| FR-VESSEL-003 | Container short_id | src/container.rs | Covered |
| FR-VESSEL-004 | Container is_running | src/container.rs | Covered |
| FR-VESSEL-INTEGRATION-001 | Integration test suite | tests/integration.rs:1 | Covered |
| FR-VESSEL-INTEGRATION-002 | Client creation | tests/integration.rs:50 | Covered |
| FR-VESSEL-INTEGRATION-003 | Client availability | tests/integration.rs:62 | Covered |
| FR-VESSEL-INTEGRATION-004 | Unavailable runtime | tests/integration.rs:73 | Covered |
| FR-VESSEL-INTEGRATION-005 | List containers empty | tests/integration.rs:87 | Covered |
| FR-VESSEL-INTEGRATION-006 | List containers with data | tests/integration.rs:100 | Covered |
| FR-VESSEL-INTEGRATION-007 | Pull image | tests/integration.rs:120 | Covered |
| FR-VESSEL-INTEGRATION-008 | Remove image | tests/integration.rs:132 | Covered |
| FR-VESSEL-INTEGRATION-009 | Run container | tests/integration.rs:145 | Covered |
| FR-VESSEL-INTEGRATION-010 | Create container only | tests/integration.rs:165 | Covered |
| FR-VESSEL-INTEGRATION-011 | Unavailable runtime error | tests/integration.rs:282 | Covered |
| FR-VESSEL-INTEGRATION-012 | VesselError types | tests/integration.rs:294 | Covered |
| FR-VESSEL-INTEGRATION-013 | PortMapping creation | tests/integration.rs:311 | Covered |
| FR-VESSEL-INTEGRATION-014 | VolumeMapping creation | tests/integration.rs:323 | Covered |
| FR-VESSEL-INTEGRATION-015 | Protocol variants | tests/integration.rs:337 | Covered |
| FR-VESSEL-INTEGRATION-016 | Image struct | tests/integration.rs:348 | Covered |
| FR-VESSEL-INTEGRATION-017 | ContainerStatus from string | tests/integration.rs:360 | Covered |
| FR-VESSEL-INTEGRATION-018 | Docker runtime name | tests/integration.rs:375 | Covered |
| FR-VESSEL-INTEGRATION-019 | Podman runtime name | tests/integration.rs:382 | Covered |
| FR-VESSEL-INTEGRATION-020 | Docker runtime debug | tests/integration.rs:389 | Covered |
| FR-VESSEL-INTEGRATION-021 | Container struct | tests/integration.rs:398 | Covered |
| FR-VESSEL-INTEGRATION-022 | Container short_id | tests/integration.rs:419 | Covered |
| FR-VESSEL-INTEGRATION-023 | Container exited status | tests/integration.rs:435 | Covered |
| FR-VESSEL-INTEGRATION-024 | ContainerInfo clone | tests/integration.rs:450 | Covered |
| FR-VESSEL-INTEGRATION-025 | ContainerCreateConfig with env | tests/integration.rs:464 | Covered |

---

## Coverage Gaps

### Critical Gaps
1. Docker runtime actual implementation (requires Docker daemon)
2. Podman runtime actual implementation (requires Podman)
3. Real container lifecycle tests (create, start, stop, remove)

### Partial Coverage
1. PortMapping/VolumeMapping roundtrip serialization
2. Error propagation from runtime to client

---

## Recommendations

1. Add more integration tests with mock runtimes
2. Add property-based tests for PortMapping/VolumeMapping
3. Add concurrent container operation tests
