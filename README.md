> **Work state:** SCAFFOLD · **Progress:** `[#######---] 70%`
<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/<REDACTED>/Logify/total?style=flat-square&label=downloads&color=blue) [![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net)
![GitHub release](https://img.shields.io/github/v/release/<REDACTED>/Logify?style=flat-square&label=release)
![License](https://img.shields.io/github/license/<REDACTED>/Logify?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->
> **Work state:** SCAFFOLD · **Progress:** `███░░░░░░░ 25%`
> Zero-cost structured-logging framework (Rust, hexagonal). GOAL: the org-shared logging surface (one sink/format contract for all Phenotype Rust crates); early at 17 files. Crate name `logkit` vs repo `Logify` drift to reconcile. · updated 2026-06-02

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
 

Use an existing sink through the builder when output needs backpressure or a
custom destination. The sink controls formatting; the builder name remains a
label for the default console logger. Sink write errors propagate from `log`.

```rust
use logkit::{Level, LogEntry, Logger, LoggerBuilder};
use logkit::adapters::sinks::{BoundedSink, ConsoleSink};

# async fn example() -> Result<(), logkit::LogError> {
let logger = LoggerBuilder::new("app")
    .level(Level::Info)
    .build_with_sink(BoundedSink::new(ConsoleSink, 16));
logger.log(LogEntry::new(Level::Info, "ready")).await?;
# Ok(())
# }
```
