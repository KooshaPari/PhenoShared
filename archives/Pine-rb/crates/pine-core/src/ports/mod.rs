// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! Hexagonal ports for Pine.
//!
//! Each module in this directory is a *port* (a trait that the domain
//! needs but does not implement), together with at least one in-memory
//! adapter (the default wiring) and one mock adapter (for tests).
//!
//! Reference: kmobile/crates/kmobile-core/src/ports/ (Rust port),
//! phenotype-voxel/src/ports/ (Rust port).

pub mod assets;
pub mod resolve;
pub mod section;
pub mod serialization;
