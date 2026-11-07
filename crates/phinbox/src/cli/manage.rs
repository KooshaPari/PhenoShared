use clap::{Args, Subcommand};
use phinbox::management::{Command, Item, Store};
use std::path::{Path, PathBuf};

#[derive(Debug, Args)]
pub struct ManageArgs {
    /// Override the authoritative management database, shared by CLI and daemon.
    #[arg(long)]
    database: Option<PathBuf>,
    #[command(subcommand)]
    command: ManageCommand,
}
#[derive(Debug, Subcommand)]
enum ManageCommand {
    /// Run the elected native Discord management adapter (explicit opt-in).
    Discord {
        #[arg(long)]
        config: PathBuf,
        #[arg(long)]
        once: bool,
    },
    /// Import one complete item from a JSON file matching management::Item.
    Create {
        #[arg(long)]
        from_file: PathBuf,
    },
    Get {
        id: String,
    },
    List,
    /// CAS workflow action, NOT a permission answer. Actor is a trusted local principal.
    Apply {
        #[arg(long)]
        from_file: PathBuf,
    },
    /// Observe durable inbox files once, including writes from other processes.
    Observe,
    /// Read ordered authoritative events for a cockpit/ledger consumer.
    Events {
        #[arg(long, default_value_t = 0)]
        after: u64,
    },
}
pub fn run(args: ManageArgs, root: &Path) -> Result<(), String> {
    let store = Store::open(
        args.database
            .unwrap_or_else(|| root.join("management.sqlite")),
    )
    .map_err(|e| e.to_string())?;
    let result: anyhow::Result<serde_json::Value> = (|| {
        Ok(match args.command {
            ManageCommand::Discord { config, once } => super::discord::run(root, &config, once)?,
            ManageCommand::Create { from_file } => serde_json::to_value(
                store.create(serde_json::from_slice::<Item>(&std::fs::read(from_file)?)?)?,
            )?,
            ManageCommand::Get { id } => serde_json::to_value(store.get(&id)?)?,
            ManageCommand::List => serde_json::to_value(store.list()?)?,
            ManageCommand::Apply { from_file } => serde_json::to_value(store.apply(
                serde_json::from_slice::<Command>(&std::fs::read(from_file)?)?,
            )?)?,
            ManageCommand::Observe => serde_json::json!({"observed":store.observe_inbox(root)?}),
            ManageCommand::Events { after } => serde_json::to_value(store.events(after, 1000)?)?,
        })
    })();
    let value = result.map_err(|e| e.to_string())?;
    println!(
        "{}",
        serde_json::to_string_pretty(&value).map_err(|e| e.to_string())?
    );
    Ok(())
}
