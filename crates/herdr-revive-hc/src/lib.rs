// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

// Phenotype fork (0.3.1-hc.1): upstream was Unix-only. Everything that talks to
// a live Herdr Core socket, installs shell hooks, or introspects Unix processes
// is gated to Unix. The portable model/layout/planner layer stays compiled on
// every platform so agent-identity logic (including jcode/kcode) is testable
// on native Windows, where the binary prints an explicit unsupported notice.
#[cfg(unix)]
pub mod app;
#[cfg(unix)]
pub mod capture;
#[cfg(unix)]
pub mod core;
pub mod layout;
#[cfg(unix)]
pub mod migrate;
pub mod model;
pub mod platform;
pub mod planner;
pub mod store;
// `timer` drives the Unix restore loop through `app`; it is not part of the
// portable agent-identity layer.
#[cfg(unix)]
pub mod timer;
pub mod transport;
