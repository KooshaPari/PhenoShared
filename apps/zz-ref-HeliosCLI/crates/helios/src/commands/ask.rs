// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `ask` subcommand handler.

use anyhow::{Context, Result};
use tracing::info;

/// Ask an AI question using an OpenAI-compatible API
pub async fn cmd_ask(
    prompt: String,
    url: Option<String>,
    api_key: Option<String>,
    model: Option<String>,
    system: Option<String>,
    chat: bool,
    stream: bool,
) -> Result<()> {
    use helios_ai::{AiClient, ChatSession, ProviderConfig};

    let base_url = url
        .or_else(|| std::env::var("HELIOS_AI_BASE_URL").ok())
        .unwrap_or_else(|| "http://localhost:11434/v1".into());

    let api_key_val =
        api_key.or_else(|| std::env::var("HELIOS_AI_API_KEY").ok()).unwrap_or_default();

    let model_val =
        model.or_else(|| std::env::var("HELIOS_AI_MODEL").ok()).unwrap_or_else(|| "gpt-4o".into());

    let config =
        ProviderConfig { base_url, api_key: api_key_val, model: model_val, timeout_secs: 120 };

    if chat {
        let mut session =
            ChatSession::new(config, system.as_deref()).context("Failed to create chat session")?;

        println!(
            "[helios] Chat mode (model: {}). Type 'exit' to quit, 'clear' to reset history.",
            session.client().config().model
        );

        let response = session.send(&prompt).await?;
        println!("\n{response}");

        let stdin = std::io::stdin();
        loop {
            print!("\n> ");
            std::io::Write::flush(&mut std::io::stdout()).ok();

            let mut input = String::new();
            if stdin.read_line(&mut input).is_err() || input.trim().is_empty() {
                break;
            }

            let input = input.trim().to_string();
            if input == "exit" || input == "quit" {
                println!("[helios] Chat ended. {} messages in history.", session.history().len());
                break;
            }
            if input == "clear" {
                session.clear();
                println!("[helios] History cleared.");
                continue;
            }

            match session.send(&input).await {
                Ok(response) => println!("\n{response}"),
                Err(e) => eprintln!("[helios] Error: {e}"),
            }
        }
        Ok(())
    } else if stream {
        let client = AiClient::new(config).context("Failed to create AI client")?;
        println!("[helios] Streaming from {}...", client.config().model);

        let messages = if let Some(sys) = system {
            vec![helios_ai::Message::system(sys), helios_ai::Message::user(&prompt)]
        } else {
            vec![helios_ai::Message::user(&prompt)]
        };

        let mut rx =
            client.stream_chat(&messages, None, None).await.context("Failed to start streaming")?;

        let mut full_response = String::new();
        while let Some(token) = rx.recv().await {
            print!("{token}");
            std::io::Write::flush(&mut std::io::stdout()).ok();
            full_response.push_str(&token);
        }
        println!();

        if !full_response.is_empty() {
            info!(tokens = full_response.len(), "Streaming complete");
        }
        Ok(())
    } else {
        let client = AiClient::new(config).context("Failed to create AI client")?;
        println!("[helios] Asking AI (model: {})...", client.config().model);

        let response = if let Some(sys) = system {
            client.complete_with_system(&sys, &prompt).await
        } else {
            client.complete(&prompt).await
        };

        match response {
            Ok(text) => {
                println!("\n{text}");
                Ok(())
            }
            Err(e) => {
                eprintln!("[helios] AI request failed: {e}");
                anyhow::bail!("AI request failed: {e}")
            }
        }
    }
}
