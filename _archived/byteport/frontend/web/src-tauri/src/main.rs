use clap::{Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(
    name = "byteport",
    version,
    about = "BytePort core engine CLI",
    long_about = None
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Launch the Tauri desktop shell
    Desktop,
}

fn main() {
    let cli = Cli::parse();

    match cli.command.unwrap_or(Command::Desktop) {
        Command::Desktop => app_lib::run(),
    }
}
