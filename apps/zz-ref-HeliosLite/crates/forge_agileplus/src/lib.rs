//! # forge_agileplus — AgilePlus delivery-quality OS (P3.2)
//!
//! `forge_agileplus` is the Rust implementation of the AgilePlus operating
//! system for delivery quality. It encodes the 31-pillar engineering
//! scorecard, sprint records, and the rolling five-sprint velocity
//! predictor described in `docs/AGILEPLUS-SETUP.md` and
//! `docs/31-pillar-scorecard.md`.
//!
//! ## Modules
//!
//! - [`pillar`] — the [`Pillar`] enum (31 variants) and the [`Score`]
//!   newtype used by [`scorecard::PillarScorecard`].
//! - [`scorecard`] — the [`PillarScorecard`] struct: serde JSON in/out,
//!   validation (all 31 pillars present), average, letter grade, and
//!   at-target count.
//! - [`sprint`] — the [`Sprint`] record (number, goal, dates,
//!   acceptance criteria, risks) with serde JSON in/out and validation
//!   (`start_date < end_date`, goal non-empty).
//! - [`velocity`] — [`VelocityReport`] plus a rolling five-sprint
//!   average helper.
//! - [`commands`] — minimal CLI surface (`validate`, `score`, `pillars`)
//!   that the parent `helioslite` binary uses to expose
//!   `helioslite agileplus <subcommand>`.
//!
//! ## Quick start
//!
//! ```
//! use forge_agileplus::{Pillar, PillarScorecard, Score};
//!
//! let mut card = PillarScorecard::new();
//! for pillar in Pillar::all() {
//!     card.set(pillar, Score::new(7.0).unwrap());
//! }
//! assert!(card.validate().is_ok());
//! assert_eq!(card.average(), Some(7.0));
//! assert_eq!(card.grade().unwrap().letter(), 'B');
//! ```

#![forbid(unsafe_code)]
#![warn(missing_docs)]

pub mod commands;
pub mod pillar;
pub mod scorecard;
pub mod sprint;
pub mod velocity;

// Ergonomic re-exports — consumers import from the crate root.
pub use pillar::{Pillar, Score};
pub use scorecard::{
    AgilePlusError, Grade, PillarScorecard, Result, SCHEMA_VERSION, TARGET_OVERALL,
};
pub use sprint::{Sprint, SprintError};
pub use velocity::{ROLLING_WINDOW, VelocityReport, rolling_average, with_rolling_averages};
