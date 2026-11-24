//! # Ports Layer
//!
//! Interfaces that define how the domain interacts with the outside world.
//!
//! ## Hexagonal Architecture Ports
//!
//! - **Driven Ports**: Interfaces that the domain defines for infrastructure
//! - **Driving Ports**: Interfaces that the application uses to interact with users

pub mod driven;
pub mod driving;
