//! Adapters layer — concrete implementations of ports.

pub mod cli;
pub mod file;
pub mod repl;

pub use cli::CliAdapter;
pub use file::FileAdapter;
pub use repl::ReplAdapter;
