//! GraphQL adapter using async-graphql.
//!
//! Provides schema definitions, query/mutation/subscription handling, and a
//! domain `Endpoint` implementation so GraphQL can be mounted on the existing
//! `Router`.

pub mod schema;
pub mod server;

pub use schema::*;
pub use server::*;
