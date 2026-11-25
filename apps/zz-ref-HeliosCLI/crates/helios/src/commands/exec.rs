// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `exec` subcommand handler.

use anyhow::{Context, Result};
use clap::ValueEnum;

/// Approval policy for the agent exec loop.
#[derive(Debug, Clone, ValueEnum, Default, PartialEq, Eq)]
pub enum ApprovalPolicy {
    #[default]
    Suggest,
    AutoEdit,
    FullAuto,
}

/// Default system prompt for the agent loop.
const AGENT_SYSTEM_PROMPT: &str = concat!(
    "You are Helios, an AI-powered software engineering assistant.\n",
    "You help users with programming tasks, file operations, and\n",
    "software development processes. Be concise and actionable.\n",
    "\n",
    "Available tools:\n",
    "- read_file(path): Read a file's contents.\n",
    "- write_file(path, content): Write content to a file.\n",
    "- edit_file(path, search, replace, replace_all): Search-and-replace in a file.\n",
    "\n",
    "When you need to edit files, describe the exact tool calls you would make.\n",
    "Future versions will execute them automatically.",
);

/// Execute an agent loop: send a prompt to the AI, parse and print the response.
#[allow(clippy::too_many_arguments)]
pub async fn cmd_exec(
    prompt: String,
    url: Option<String>,
    api_key: Option<String>,
    model: Option<String>,
    approval: ApprovalPolicy,
    max_iterations: u32,
    budget: f64,
    cost_per_input_tokens: f64,
    cost_per_output_tokens: f64,
) -> Result<()> {
    use helios_ai::{AiClient, CostTracker, ProviderConfig};

    let base_url = url
        .or_else(|| std::env::var("HELIOS_AI_BASE_URL").ok())
        .unwrap_or_else(|| "http://localhost:11434/v1".into());

    let api_key_val =
        api_key.or_else(|| std::env::var("HELIOS_AI_API_KEY").ok()).unwrap_or_default();

    let model_val =
        model.or_else(|| std::env::var("HELIOS_AI_MODEL").ok()).unwrap_or_else(|| "gpt-4o".into());

    let config =
        ProviderConfig { base_url, api_key: api_key_val, model: model_val, timeout_secs: 120 };

    let client = AiClient::new(config).context("Failed to create AI client for exec")?;
    let mut cost_tracker = CostTracker::new(cost_per_input_tokens, cost_per_output_tokens, budget);

    let approval_desc = match approval {
        ApprovalPolicy::Suggest => {
            "You are in SUGGEST mode. Describe what you would do, but DO NOT \
             execute any commands or write any files. Just present the plan."
        }
        ApprovalPolicy::AutoEdit => {
            "You are in AUTO-EDIT mode. You may propose file edits. File edits \
             will be applied automatically. Do NOT propose shell commands."
        }
        ApprovalPolicy::FullAuto => {
            "You are in FULL-AUTO mode. Execute all actions including file edits \
             and shell commands without hesitation."
        }
    };

    let system_prompt = format!("{AGENT_SYSTEM_PROMPT}\n\nApproval policy: {approval_desc}");

    println!("[helios:exec] Sending task to {}...", client.config().model);
    println!("[helios:exec] Approval: {:?}, Max iterations: {}", approval, max_iterations);
    println!(
        "[helios:exec] Budget: ${:.2}, Input: ${}/tok, Output: ${}/tok",
        budget, cost_per_input_tokens, cost_per_output_tokens
    );
    println!("[helios:exec] Prompt: {}", prompt);

    let mut current_prompt = prompt;

    for iteration in 1..=max_iterations {
        println!("\n--- Iteration {iteration}/{max_iterations} ---\n");

        let response = client
            .complete_with_system(&system_prompt, &current_prompt)
            .await
            .context("AI request failed during exec")?;

        println!("{response}");

        let input_estimate = system_prompt.len() as u64 / 4 + current_prompt.len() as u64 / 4;
        let output_estimate = response.len() as u64 / 4;
        cost_tracker.record_usage(input_estimate, output_estimate);
        println!("[helios:exec] {}", cost_tracker.usage_summary());

        if cost_tracker.is_over_budget() {
            println!("\n[helios:exec] Budget exceeded (${:.2}). Stopping agent loop.", budget);
            break;
        }

        if approval == ApprovalPolicy::Suggest {
            println!("\n[suggest mode] Plan displayed. No actions taken.");
            break;
        }

        if !response.contains("read_file")
            && !response.contains("write_file")
            && !response.contains("edit_file")
        {
            println!("\n--- No tool calls detected. Agent loop complete. ---");
            break;
        }

        current_prompt = "The previous response contained tool call descriptions. \n\
             In future versions these will be executed automatically. \n\
             For now, respond with the final result."
            .to_string();
    }

    println!("\n[helios:exec] Session complete. {}", cost_tracker.usage_summary());

    Ok(())
}
