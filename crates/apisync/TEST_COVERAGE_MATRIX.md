# Test and Requirement Traceability Matrix

**Project:** Apisync  
**Release scope:** the implemented item CRUD server, domain store, GraphQL schema,
WebSocket adapter, and mandatory quality gates  
**Version:** 2.0  
**Measured:** 2026-07-17

This matrix deliberately excludes the unimplemented client-side roadmap in
`FUNCTIONAL_REQUIREMENTS.md` from the release denominator. Those requirements
remain visible backlog; moving them into this release requires implementation
and evidence, not relabeling.

## Exact summary

| Metric | Numerator | Denominator | Result | Gate |
|---|---:|---:|---:|---:|
| Defined loopback E2E journeys | 10 | 10 | 100.0% | >=85% |
| Release requirement traceability | 16 | 16 | 100.0% | >=85% |
| Non-benchmark Rust tests | 75 | 75 | 100.0% | 100% |

The test count is 51 library tests + 11 property tests + 10 REST E2E tests +
3 executable traceability-contract tests. Criterion benchmarks are build
targets, not tests, and are therefore compiled with `cargo bench --no-run`
rather than executed by the test gate.

## Release requirements and evidence

The executable contract in `tests/traceability_contract.rs` checks the exact
16-row denominator, the 10-row E2E denominator, the >=85% gates, and that every
cited evidence symbol exists.

| ID | Type | Requirement | Evidence | Status |
|---|---|---|---|---|
| RQ-E2E-001 | E2E | Listing a new store returns an empty collection. | `test_list_items_empty` | Covered |
| RQ-E2E-002 | E2E | Creating an item returns 201 and preserves fields. | `test_create_item` | Covered |
| RQ-E2E-003 | E2E | A created item can be retrieved by ID. | `test_get_item` | Covered |
| RQ-E2E-004 | E2E | Retrieving an unknown item returns 404. | `test_get_item_not_found` | Covered |
| RQ-E2E-005 | E2E | A created item can be updated. | `test_update_item` | Covered |
| RQ-E2E-006 | E2E | Updating an unknown item returns 404. | `test_update_item_not_found` | Covered |
| RQ-E2E-007 | E2E | A created item can be deleted and is then absent. | `test_delete_item` | Covered |
| RQ-E2E-008 | E2E | Deleting an unknown item returns 404. | `test_delete_item_not_found` | Covered |
| RQ-E2E-009 | E2E | Listing returns all created items in stable ID order. | `test_list_items_with_data` | Covered |
| RQ-E2E-010 | E2E | Invalid JSON on create returns 400. | `test_create_item_invalid_body` | Covered |
| RQ-DOM-001 | Property | Creation preserves values and assigns monotonic IDs. | `prop_item_creation_with_random_data` | Covered |
| RQ-DOM-002 | Property | Create/get/update/delete round trips preserve invariants. | `prop_item_store_roundtrip`<br>`prop_item_store_partial_update_roundtrip` | Covered |
| RQ-DOM-003 | Property | Concurrent mutation and read access remain safe. | `prop_concurrent_access_safety`<br>`prop_concurrent_read_only_access` | Covered |
| RQ-GQL-001 | Component | GraphQL query and mutation behavior is tested. | `test_query_item_by_id`<br>`test_mutation_create_item` | Covered |
| RQ-WS-001 | Component | WebSocket connections, broadcast, create, and get are tested. | `test_websocket_connection_and_broadcast`<br>`test_websocket_create_item`<br>`test_websocket_get_items` | Covered |
| RQ-QUAL-001 | Gate | Locked fmt, clippy, test, docs, build, benchmark-build, audit, and package gates are mandatory. | `cargo test --lib --tests --locked`<br>`cargo package --locked` | Covered |

## Out-of-scope backlog

`FR-API-*`, `FR-GQL-*`, `FR-WS-*`, and `FR-OBS-*` client requirements in
`FUNCTIONAL_REQUIREMENTS.md` describe a future client API that is not exported
by the current crate. They are not claimed as implemented or covered.
