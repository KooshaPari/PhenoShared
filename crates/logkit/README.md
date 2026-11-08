//! # logkit - Zero-cost Structured Logging Framework
//!
//! Hexagonal architecture with ports and adapters.

## Features

- Zero-cost abstraction
- Multiple sinks
- Structured logging
- Async support

## Usage

```rust
use logkit::{LoggerBuilder, Level};

let logger = LoggerBuilder::new("app")
    .level(Level::Info)
    .build();
```
