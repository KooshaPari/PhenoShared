// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

// Phenotype fork (0.3.1-hc.1): upstream was Unix-only. Everything that installs
// shell hooks, introspects Unix processes, or drives the Unix layout rebuild is
// gated to Unix. The portable model/layout/planner/store layer stays compiled on
// every platform, and native Windows has its own capture backend
// (`capture_windows`) and command surface (`winapp`), which take a pane's
// program identity from Herdr Core instead of from process introspection.
#[cfg(unix)]
pub mod app;
/// The exact-command layer (argv + reported agent session -> resume command)
/// is pure model logic and is shared by every capture backend.
pub mod command;
#[cfg(unix)]
pub mod capture;
#[cfg(windows)]
#[path = "capture_windows.rs"]
pub mod capture;
#[cfg(unix)]
pub mod core;
pub mod layout;
#[cfg(unix)]
pub mod migrate;
pub mod model;
#[cfg(unix)]
pub mod platform;
pub mod planner;
pub mod store;
// `timer` drives the Unix restore loop through `app`; it is not part of the
// portable agent-identity layer.
#[cfg(unix)]
pub mod timer;
pub mod transport;
#[cfg(windows)]
pub mod winapp;
