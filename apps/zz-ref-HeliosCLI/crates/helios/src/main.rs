// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Unified HeliosCLI binary -- wires harness_queue, harness_runner,
//! harness_rollback, harness_checkpoint, and helios_config together.

mod commands;

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

use commands::exec::ApprovalPolicy;

#[derive(Parser, Debug)]
#[command(
    name = "helios",
    about = "HeliosCLI -- Unified harness for agent task orchestration",
    version,
    long_about = "HeliosCLI combines task queuing, command execution, checkpoint/rollback,\nand configuration into a single CLI binary."
)]
struct Cli {
    /// Config file path
    #[arg(short, long, global = true)]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Run a command through the harness runner
    Run {
        /// Command to execute
        command: String,
        /// Working directory
        #[arg(short, long)]
        dir: Option<PathBuf>,
        /// Timeout in seconds
        #[arg(short = 't', long, default_value = "300")]
        timeout: u64,
        /// Run in shell mode
        #[arg(long)]
        shell: bool,
        /// Enable sandbox restrictions
        #[arg(long)]
        sandbox: bool,
    },

    /// Create a git checkpoint
    Checkpoint {
        /// Spec/project identifier
        #[arg(short, long, default_value = "default")]
        spec: String,
        /// Optional message
        #[arg(short, long)]
        message: Option<String>,
        /// Repository path
        #[arg(short, long)]
        repo: Option<PathBuf>,
    },

    /// Rollback to a checkpoint
    Rollback {
        /// Checkpoint ID (git SHA or checkpoint UUID)
        checkpoint_id: String,
        /// Repository path
        #[arg(short, long)]
        repo: Option<PathBuf>,
    },

    /// Show system status and harness crate versions
    Status,

    /// Enqueue a task for background processing
    Enqueue {
        /// Task payload (JSON string)
        payload: String,
        /// Queue capacity
        #[arg(short = 'C', long, default_value = "100")]
        capacity: usize,
    },

    /// Record a terminal session using KLA
    Record {
        /// Path to the KLA script (.kla.yaml)
        script: PathBuf,
        /// Output directory for recordings
        #[arg(short, long, default_value = "./output")]
        output: PathBuf,
        /// Output format (png, gif, both)
        #[arg(short, long, default_value = "both")]
        format: String,
    },

    /// Ask an AI question using an OpenAI-compatible API
    Ask {
        /// The question/prompt to send
        prompt: String,
        /// Provider URL (overrides HELIOS_AI_BASE_URL env)
        #[arg(short, long)]
        url: Option<String>,
        /// API key (overrides HELIOS_AI_API_KEY env)
        #[arg(short = 'k', long)]
        api_key: Option<String>,
        /// Model name (overrides HELIOS_AI_MODEL env)
        #[arg(short, long)]
        model: Option<String>,
        /// System prompt
        #[arg(short, long)]
        system: Option<String>,
        /// Enable interactive multi-turn chat mode
        #[arg(long)]
        chat: bool,
        /// Enable SSE streaming (tokens print as they arrive)
        #[arg(long)]
        stream: bool,
    },

    /// Execute an agent loop: send a prompt to the AI and display the response.
    Exec {
        /// The task prompt to send to the AI agent
        prompt: String,
        /// Provider URL (overrides HELIOS_AI_BASE_URL env)
        #[arg(short, long)]
        url: Option<String>,
        /// API key (overrides HELIOS_AI_API_KEY env)
        #[arg(short = 'k', long)]
        api_key: Option<String>,
        /// Model name (overrides HELIOS_AI_MODEL env)
        #[arg(short, long)]
        model: Option<String>,
        /// Approval policy: suggest (plan only), auto-edit (apply file edits), full-auto (execute all)
        #[arg(long, value_enum, default_value_t)]
        approval: ApprovalPolicy,
        /// Maximum number of agent iterations (default: 10)
        #[arg(long, default_value = "10")]
        max_iterations: u32,
        /// Budget ceiling in USD (default: 1.00)
        #[arg(long, default_value = "1.0")]
        budget: f64,
        /// Cost per input token in USD (default: $30/M = 0.000030)
        #[arg(long, default_value = "0.000030")]
        cost_per_input_tokens: f64,
        /// Cost per output token in USD (default: $60/M = 0.000060)
        #[arg(long, default_value = "0.000060")]
        cost_per_output_tokens: f64,
    },

    /// Resume a previous session.
    Resume {
        /// Resume the most recent session
        #[arg(long)]
        last: bool,
        /// Resume a specific session by UUID
        #[arg(short, long, conflicts_with = "last")]
        session_id: Option<String>,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Run { command, dir, timeout, shell, sandbox } => {
            commands::run::cmd_run(command, dir, timeout, shell, sandbox).await
        }
        Commands::Checkpoint { spec, message, repo } => {
            commands::checkpoint::cmd_checkpoint(spec, message, repo)
        }
        Commands::Rollback { checkpoint_id, repo } => {
            commands::rollback::cmd_rollback(checkpoint_id, repo)
        }
        Commands::Status => commands::status::cmd_status(),
        Commands::Enqueue { payload, capacity } => {
            commands::enqueue::cmd_enqueue(payload, capacity)
        }
        Commands::Record { script, output, format } => {
            commands::record::cmd_record(script, output, format).await
        }
        Commands::Ask { prompt, url, api_key, model, system, chat, stream } => {
            commands::ask::cmd_ask(prompt, url, api_key, model, system, chat, stream).await
        }
        Commands::Exec {
            prompt,
            url,
            api_key,
            model,
            approval,
            max_iterations,
            budget,
            cost_per_input_tokens,
            cost_per_output_tokens,
        } => {
            commands::exec::cmd_exec(
                prompt,
                url,
                api_key,
                model,
                approval,
                max_iterations,
                budget,
                cost_per_input_tokens,
                cost_per_output_tokens,
            )
            .await
        }
        Commands::Resume { last, session_id } => commands::resume::cmd_resume(last, session_id),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn cli_struct_is_valid() {
        Cli::command().debug_assert();
    }

    #[test]
    fn cli_all_subcommands_parse() {
        // Validated: all 9 subcommands parse without error
        let cases = [
            &["helios", "status"][..],
            &["helios", "run", "echo hello"],
            &["helios", "run", "echo test", "--sandbox"],
            &["helios", "checkpoint", "--spec", "my-spec"],
            &["helios", "rollback", "abc123"],
            &["helios", "enqueue", "{\"task\":\"test\"}"],
            &["helios", "record", "script.kla.yaml"],
            &["helios", "ask", "What is 2+2?"],
            &["helios", "exec", "fix the bug"],
            &["helios", "exec", "do it", "--approval", "full-auto"],
            &["helios", "resume", "--last"],
        ];
        for args in &cases {
            let cli = Cli::try_parse_from(*args);
            assert!(args[1] == "helios" || cli.is_ok(), "Failed to parse: {:?}", args);
            if cli.is_ok() {
                // Just verify it parsed — don't need to match every variant
            }
        }
    }

    #[test]
    fn cli_run_parses_command_and_flags() {
        let cli = Cli::try_parse_from(["helios", "run", "echo hello", "--sandbox"]);
        assert!(cli.is_ok());
        assert!(matches!(cli.unwrap().command, Commands::Run { sandbox: true, .. }));
    }

    #[test]
    fn cli_exec_parses_approval_policy() {
        let cli = Cli::try_parse_from(["helios", "exec", "do it", "--approval", "full-auto"]);
        assert!(cli.is_ok());
        assert!(matches!(
            cli.unwrap().command,
            Commands::Exec { approval: ApprovalPolicy::FullAuto, .. }
        ));
    }

    #[test]
    fn test_command_handlers_work() {
        assert!(commands::status::cmd_status().is_ok());
        let payload = r#"{"task":"test"}"#.to_string();
        assert!(commands::enqueue::cmd_enqueue(payload, 10).is_ok());
        assert!(commands::enqueue::cmd_enqueue("bad json".into(), 10).is_err());
    }

    #[test]
    fn test_approval_policy_default() {
        assert!(matches!(ApprovalPolicy::default(), ApprovalPolicy::Suggest));
    }
}
