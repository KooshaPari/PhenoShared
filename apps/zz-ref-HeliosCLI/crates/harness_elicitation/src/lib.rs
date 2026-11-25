// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Elicitation Handler
//!
//! Converts natural language ideas into specifications for autonomous execution.

pub mod classifier;
pub mod error;
pub mod generator;
pub mod intent;

pub use classifier::*;
pub use error::*;
pub use generator::*;
pub use intent::*;
