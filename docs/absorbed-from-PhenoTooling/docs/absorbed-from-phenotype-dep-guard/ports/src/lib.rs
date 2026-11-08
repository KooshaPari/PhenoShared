// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// Copyright ©2026 Koosha Paridehpour

//! phenotype-dep-guard hexagonal port definitions and adapters.
//!
//! This crate defines the `SupplyChain` trait (the port) and ecosystem-specific
//! adapters (Cargo, npm, etc.) that implement it.

pub mod supply_chain;
pub mod adapters;
