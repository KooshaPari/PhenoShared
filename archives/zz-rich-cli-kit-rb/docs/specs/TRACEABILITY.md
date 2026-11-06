# Traceability Matrix — rich-cli-kit

This document maps functional requirements (FRs) to test cases, providing bidirectional traceability between specifications and implementation verification.

## Overview

| FR ID | FR Title | Test Files | Test Count | Coverage Status |
|-------|----------|------------|------------|-----------------|
| FR-001 | Terminal Capability Detection | `crates/rck-core/src/capabilities.rs`, `tests/integration/test_capabilities.rs` | 4 | ✓ Complete |
| FR-002 | Kitty Graphics Protocol Encoding | `crates/rck-core/src/encoder.rs`, `tests/integration/test_encoder.rs` | 5 | ✓ Complete |
| FR-003 | Progress Bar Rendering | `tests/integration/test_progress.rs`, `mcp/tests/test_rck_wrapper.py` | 3 | ✓ Complete |
| FR-004 | Status Panel Rendering | `tests/integration/test_panel.rs`, `mcp/tests/test_rck_wrapper.py` | 2 | ✓ Complete |
| FR-005 | OSC Sequence Emission | `tests/integration/test_osc_sequences.rs`, `mcp/tests/test_rck_wrapper.py` | 4 | ✓ Complete |
| FR-006 | Interactive Input Primitives | `mcp/tests/test_rck_wrapper.py` | 3 | ⚠ Partial (TTY-only paths not covered) |
| FR-007 | Image Data Handling | `tests/integration/test_image_handling.rs` | 3 | ✓ Complete |
| FR-008 | Shader Management | N/A | 0 | ⚠ Not tested |

## Detailed Mappings

### FR-001: Terminal Capability Detection

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `plain_is_safe_default` | `crates/rck-core/src/capabilities.rs` | 303-314 | Verifies plain capabilities have all flags disabled | AC-001.4 |
| `detect_returns_a_value` | `crates/rck-core/src/capabilities.rs` | 316-322 | Ensures detection never panics and returns non-empty terminal | AC-001.5 |
| `test_capability_detection_env_vars` | `tests/integration/test_capabilities.rs` | 5-25 | Verifies environment-based detection for known terminals | AC-001.1 |
| `test_capability_tty_check` | `tests/integration/test_capabilities.rs` | 27-40 | Validates graphics disabled when stdout not a TTY | AC-001.3 |

### FR-002: Kitty Graphics Protocol Encoding

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `single_chunk_envelope_matches_spec` | `crates/rck-core/src/encoder.rs` | 74-88 | Validates single-frame APC structure with `a=T,f=100,q=2` | AC-002.1, AC-002.2, AC-002.7 |
| `multi_chunk_has_correct_m_keys` | `crates/rck-core/src/encoder.rs` | 90-107 | Ensures multi-chunk frames use `m=1` and final `m=0` | AC-002.3, AC-002.4, AC-002.5 |
| `chunks_respect_max_size` | `crates/rck-core/src/encoder.rs` | 109-129 | Validates each chunk ≤4096 bytes | AC-002.3 |
| `test_base64_alignment` | `tests/integration/test_encoder.rs` | 8-22 | Verifies chunk lengths are multiples of 4 for base64 alignment | AC-002.6 |
| `test_encoder_large_image` | `tests/integration/test_encoder.rs` | 24-45 | End-to-end test with 20KB image producing multiple chunks | AC-002.3, AC-002.4, AC-002.5 |

### FR-003: Progress Bar Rendering

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `test_progress_clamping` | `tests/integration/test_progress.rs` | 8-22 | Validates ratio clamping to [0.0, 1.0] | AC-003.1 |
| `test_progress_ascii_style` | `tests/integration/test_progress.rs` | 24-38 | Verifies ASCII progress bar format with `[====>  ]` | AC-003.3 |
| `test_progress_renders_percentage` | `mcp/tests/test_rck_wrapper.py` | 33-37 | End-to-end test via Python wrapper validating percentage display | AC-003.4, AC-003.5 |

### FR-004: Status Panel Rendering

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `test_panel_border_styles` | `tests/integration/test_panel.rs` | 8-35 | Validates rounded, square, and ASCII border characters | AC-004.2, AC-004.3, AC-004.4 |
| `test_panel_renders_title` | `mcp/tests/test_rck_wrapper.py` | 40-45 | End-to-end test via Python wrapper validating title and body rendering | AC-004.1, AC-004.6, AC-004.7 |

### FR-005: OSC Sequence Emission

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `test_osc8_hyperlink_format` | `tests/integration/test_osc_sequences.rs` | 8-20 | Validates OSC 8 sequence format with URL and text | AC-005.1 |
| `test_osc52_clipboard_base64` | `tests/integration/test_osc_sequences.rs` | 22-35 | Verifies OSC 52 base64 encoding | AC-005.2 |
| `test_osc133_task_markers` | `tests/integration/test_osc_sequences.rs` | 37-52 | Validates OSC 133 A, C, D sequences | AC-005.3 |
| `test_tmux_passthrough_wrapping` | `tests/integration/test_osc_sequences.rs` | 54-72 | Ensures DCS passthrough when in tmux | AC-005.4 |

### FR-006: Interactive Input Primitives

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `test_ask_non_tty_defaults_to_cancel` | `mcp/tests/test_rck_wrapper.py` | 72-76 | Validates stdin fallback for `ask` command | AC-006.4 |
| `test_pick_non_tty` | `mcp/tests/test_rck_wrapper.py` | 79-81 | Validates stdin fallback for `pick` command | AC-006.4 |
| `test_input_non_tty` | `mcp/tests/test_rck_wrapper.py` | 84-86 | Validates stdin fallback for `input` command | AC-006.4 |

**Coverage Note:** TTY-enabled interactive paths (alt-screen, kitty-keyboard, ESC cancellation) require manual testing in a real terminal and are not covered by automated tests.

### FR-007: Image Data Handling

| Test Case | File | Line | Description | Acceptance Criteria |
|-----------|------|------|-------------|---------------------|
| `test_image_load_png` | `tests/integration/test_image_handling.rs` | 10-22 | Loads PNG file and validates dimensions and bytes | AC-007.1, AC-007.3 |
| `test_image_load_jpeg` | `tests/integration/test_image_handling.rs` | 24-38 | Loads JPEG file, verifies PNG re-encoding | AC-007.2, AC-007.3 |
| `test_image_load_error` | `tests/integration/test_image_handling.rs` | 40-50 | Validates error handling for missing file | AC-007.4 |

### FR-008: Shader Management

**Coverage Note:** Shader management is a low-priority feature. Testing requires filesystem mocking or temp directory setup and is deferred to future work.

---

## Test Execution Summary

**Total Test Cases:** 27  
**Rust Unit Tests:** 14  
**Rust Integration Tests:** 10  
**Python Integration Tests:** 3  
**Manual Test Cases:** 0 (interactive TTY paths require manual verification)

### Running Tests

```bash
# Rust tests (workspace-wide)
cargo test --workspace

# Python tests
cd mcp && pytest

# All tests
cargo test --workspace && cd mcp && pytest && cd ..
```

### Coverage Gaps

1. **FR-006 Interactive Primitives:** Alt-screen and kitty-keyboard paths require real TTY testing
2. **FR-008 Shader Management:** No automated tests; low priority
3. **Edge Cases:** Very large images (>100MB), unicode edge cases in panel rendering
4. **Performance:** No benchmarks for encoder chunking or progress bar width calculation

---

## Maintenance Notes

- **Adding a new FR:** Update both `FR.md` and this traceability matrix
- **Adding a new test:** Annotate with `// Traces to: FR-XXX` and update the appropriate table
- **Changing an FR:** Review all linked tests and update acceptance criteria
- **Deprecating an FR:** Mark as deprecated in both documents; do not remove to preserve history

---

**Document Status:** Active  
**Last Updated:** 2026-06-15  
**Version:** 1.0
