//! Native opt-in Discord management projection. Never grants harness permission.
mod config;
mod gateway;
mod interactions;
mod mirror;
mod render;
mod rest;
pub use config::{Binding, Config};
pub use gateway::run_gateway;
pub use interactions::{Interaction, InteractionData, InteractionHandler, Member, Message, User};
pub use mirror::Mirror;
pub use render::{custom_id, render_message};
pub use rest::DiscordClient;
