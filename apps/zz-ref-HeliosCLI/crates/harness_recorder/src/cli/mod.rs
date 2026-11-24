use std::path::PathBuf;

use clap::Subcommand;

pub mod commands;

#[derive(Subcommand)]
pub enum Commands {
    /// Record a terminal session from a script
    Record {
        /// Script file to execute (.kla.yaml)
        #[arg(value_name = "SCRIPT")]
        script: PathBuf,

        /// Output directory for recordings
        #[arg(short, long, default_value = "./output")]
        output: PathBuf,

        /// Output format (png, gif, mp4)
        #[arg(short, long, default_value = "gif")]
        format: String,
    },

    /// Take a screenshot of a single command
    Screenshot {
        /// Command to execute
        #[arg(value_name = "COMMAND")]
        command: String,

        /// Output file name
        #[arg(short, long, default_value = "screenshot.png")]
        output: PathBuf,
    },

    /// Run interactive demo mode
    Demo {
        /// Script file to execute
        #[arg(value_name = "SCRIPT")]
        script: PathBuf,

        /// Step through commands manually
        #[arg(short, long)]
        interactive: bool,
    },

    /// Convert between recording formats
    Convert {
        /// Input file
        #[arg(value_name = "INPUT")]
        input: PathBuf,

        /// Output file
        #[arg(value_name = "OUTPUT")]
        output: PathBuf,
    },
}

pub async fn execute_command(command: Commands) -> anyhow::Result<()> {
    match command {
        Commands::Record { script, output, format } => {
            commands::record_command(script, output, format).await
        }
        Commands::Screenshot { command, output } => {
            commands::screenshot_command(command, output).await
        }
        Commands::Demo { script, interactive } => commands::demo_command(script, interactive).await,
        Commands::Convert { input, output } => commands::convert_command(input, output).await,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn execute_command_dispatches_convert() {
        let dir = tempfile::tempdir().expect("tempdir");
        let input = dir.path().join("dispatch.kla.yaml");
        let output = dir.path().join("dispatch.json");
        let yaml = r#"name: dispatch-test
settings:
  width: 80
  height: 24
  shell: sh
steps:
  - type: command
    text: echo dispatch
"#;
        std::fs::write(&input, yaml).expect("write yaml");
        execute_command(Commands::Convert { input, output }).await.expect("convert dispatch");
    }
}
