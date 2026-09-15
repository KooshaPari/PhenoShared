# Tests

This directory contains tests for Stashly.

## Structure

- `unit/` - Unit tests for internal modules
- `integration/` - Integration tests for public API
- `e2e/` - End-to-end tests

## Running Tests

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_name
```
