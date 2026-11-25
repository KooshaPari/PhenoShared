// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Specification parser and models for heliosHarness
//!
//! This module provides the core types and parsing logic for
//! specification-driven development (SDD) in autonomous agents.

pub mod error;
pub mod models;
pub mod parser;
pub mod validation;

pub use error::*;
pub use models::*;
pub use parser::*;
pub use validation::*;
