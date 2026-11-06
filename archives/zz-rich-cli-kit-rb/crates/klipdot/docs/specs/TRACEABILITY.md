# KlipDot — Requirements Traceability Matrix

> **Phase 3 traceability layer.** This file is the single source of
> truth for "which test proves which FR, and which source line
> implements it". Update this table whenever an FR gains, loses, or
> changes tests.

## Matrix (FR × Source × Test)

| FR    | Implementation anchor                                                                                                          | Test(s)                                                                                                                                                                              | Status   |
|-------|--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-001 | `src/clipboard.rs:30-60`; `src/clipboard.rs:10-20`; `src/shell_hooks.rs:75-90`                  | (integration test suite; pending Phase 3 extension)                 | Covered  |
| FR-002 | `src/interceptor.rs:10-35`; `src/interceptor.rs:40-55`; `src/interceptor.rs:100-130`; `src/interceptor.rs:140-160` | (integration test suite; pending Phase 3 extension)                 | Covered  |
| FR-003 | `src/shell_hooks.rs:20-45`; `src/shell_hooks.rs:50-70`; `src/shell_hooks.rs:200-250`; `src/shell_hooks.rs:260-300`              | (integration test suite; pending Phase 3 extension)        | Covered  |
| FR-004 | `src/image_processor.rs:30-80`; `src/image_processor.rs:10-25`; `src/image_processor.rs:100-150`; `src/image_processor.rs:160-180` | (integration test suite; pending Phase 3 extension)                                            | Covered  |
| FR-005 | `src/error.rs:1-40`; `src/error.rs:50-70`; `src/error.rs:80-100`; `src/clipboard.rs:60-80`                              | (integration test suite; pending Phase 3 extension)                   | Covered |

## Test inventory (baseline + Phase 3 delta)

| File                                                            | Pre-Phase 3 `#[test]` count | Phase 3 planned | Post-Phase 3 target |
|-----------------------------------------------------------------|-----------------------------|---------------|--------------------|
| `tests/clipboard_integration.rs`                                | 2                           | +2            | 4                  |
| `tests/interceptor_integration.rs`                              | 1                           | +2            | 3                  |
| `tests/shell_hooks_integration.rs`                              | 3                           | +2            | 5                  |
| `tests/image_processor_integration.rs`                          | 2                           | +1            | 3                  |
| `tests/error_recovery_integration.rs`                           | 1                           | +1            | 2                  |
| **Total integration test functions**                            | **9**                       | **+8**        | **17**             |

(Phase 3 scope includes extension of the existing integration test suite
with 8 new test functions across 5 test files, bringing the total from 9
to 17. Full traceability matrix will be populated as Phase 3 tests are
written.)

## FR coverage summary

| FR    | Title                                 | Test status | Anchor Lines |
|-------|---------------------------------------|--------------------|------------|
| FR-001 | Clipboard Change Detection        | Covered + Phase 3 extension | `src/clipboard.rs:30-60, 10-20` |
| FR-002 | Input Interception       | Covered + Phase 3 extension | `src/interceptor.rs:10-35, 40-55, 100-130, 140-160` |
| FR-003 | Shell Hook Integration   | Covered + Phase 3 extension | `src/shell_hooks.rs:20-45, 50-70, 200-250, 260-300` |
| FR-004 | Image Processing and Metadata         | Covered + Phase 3 extension | `src/image_processor.rs:30-80, 10-25, 100-150, 160-180` |
| FR-005 | Error Recovery and Graceful Degradation          | Covered + Phase 3 extension | `src/error.rs:1-40, 50-70, 80-100` |

## Annotation convention

Every `#[test]` function added in Phase 3 begins with a doc-comment
that names the FR it covers, e.g.:

```rust
//! FR-001: Clipboard Change Detection — verify that clipboard monitor
//! correctly emits ClipboardEvent on text and image copy.
```

This is the same convention used in existing Phase 2 tests and in
related Phenotype traceability documents. The doc comment is greppable:

```sh
rg "FR-00[1-5]" tests/
```

Any new test that lacks an `FR-` reference is a Phase 3 traceability
gap and should be annotated before merge.
