// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! # arch_test - Architectural Tests for heliosCLI
//!
//! This crate provides architectural testing infrastructure including:
//! - Boundary enforcement tests
//! - TDD patterns (Red-Green-Refactor)
//! - Property-based testing with proptest

pub mod boundary;
pub mod proptest_patterns;
pub mod tdd;

pub use boundary::BoundaryEnforcer;
pub use proptest_patterns::PropertyTest;
pub use tdd::TestDriven;
