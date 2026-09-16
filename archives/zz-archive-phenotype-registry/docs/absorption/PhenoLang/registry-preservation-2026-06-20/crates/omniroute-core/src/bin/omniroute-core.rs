//! Omniroute Core CLI
//!
//! Command-line interface for the OmniRoute LLM routing engine.

use anyhow::Result;
use clap::{Parser, Subcommand};
use omniroute_core::http::{start, AppState, ServerConfig, ServerState};
use omniroute_core::providers::LLMProvider;
use omniroute_core::router::Router;
use omniroute_core::types::{ChatRequest, EmbeddingInput, EmbeddingRequest, Message};
use std::sync::Arc;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[derive(Parser)]
#[command(
    name = "omniroute-core",
    about = "OmniRoute Core - Intelligent LLM request routing",
    version = "0.1.0"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Enable verbose logging
    #[arg(short, long)]
    verbose: bool,

    /// Enable JSON logging
    #[arg(short, long)]
    json: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the HTTP server
    Serve {
        /// Host to bind to
        #[arg(short, long, default_value = "127.0.0.1")]
        host: String,

        /// Port to bind to
        #[arg(short, long, default_value = "8080")]
        port: u16,

        /// Disable CORS
        #[arg(long)]
        no_cors: bool,
    },

    /// List available models from all providers
    Models,

    /// Send a test chat request
    Chat {
        /// Model to use
        #[arg(short, long, default_value = "mock-gpt-4")]
        model: String,

        /// Message to send
        #[arg(short, long)]
        message: String,
    },

    /// Run in demo mode with mock responses
    Demo,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize logging
    let log_level = if cli.verbose {
        Level::DEBUG
    } else {
        Level::INFO
    };

    let subscriber = FmtSubscriber::builder()
        .with_max_level(log_level)
        .with_target(true)
        .with_thread_ids(true)
        .with_file(true)
        .with_line_number(true);

    if cli.json {
        subscriber.json().init();
    } else {
        subscriber.init();
    }

    match cli.command {
        Commands::Serve {
            host,
            port,
            no_cors,
        } => {
            let addr = format!("{}:{}", host, port);
            info!("Starting OmniRoute server on {}", addr);

            // Build router with auto-registered providers
            let router = Router::new().auto_register().unwrap_or_else(|_| {
                // Fall back to mock if no API keys are set
                info!("No API keys found, using mock provider");
                Router::with_mock()
            });

            let config = ServerConfig {
                allow_cors: !no_cors,
                timeout_secs: 300,
            };

            let state: AppState = Arc::new(ServerState { router, config });

            start(&addr, state).await?;
        }
        Commands::Models => {
            list_models().await?;
        }
        Commands::Chat { model, message } => {
            send_chat(&model, &message).await?;
        }
        Commands::Demo => {
            run_demo().await?;
        }
    }

    Ok(())
}

async fn list_models() -> Result<()> {
    let router = Router::with_mock();

    info!("Available models:");

    let all_models = router.list_all_models().await?;

    for (provider_name, model_list) in all_models {
        println!("\nProvider: {}", provider_name);
        for model in model_list.data {
            let display = model.display_name.as_deref().unwrap_or(&model.id);
            println!("  - {} ({})", model.id, display);
        }
    }

    Ok(())
}

async fn send_chat(model: &str, message: &str) -> Result<()> {
    let provider = omniroute_core::providers::MockProvider::new();

    info!("Sending chat request to model: {}", model);

    let request = ChatRequest {
        model: model.to_string(),
        messages: vec![Message::user(message)],
        stream: false,
        temperature: None,
        max_tokens: None,
        top_p: None,
        frequency_penalty: None,
        presence_penalty: None,
        stop: None,
        tools: None,
        tool_choice: None,
        response_format: None,
        seed: None,
        user: None,
    };

    match provider.chat_completions(request).await {
        Ok(response) => {
            println!("\nResponse:");
            if let Some(choice) = response.choices.first() {
                println!("{}", choice.message.content);
            }
        }
        Err(e) => {
            anyhow::bail!("Chat request failed: {}", e);
        }
    }

    Ok(())
}

async fn run_demo() -> Result<()> {
    println!("╔══════════════════════════════════════════════╗");
    println!("║         OmniRoute Core Demo                 ║");
    println!("╠══════════════════════════════════════════════╣");
    println!("║  This demo shows the routing capabilities   ║");
    println!("║  of the OmniRoute Core engine.              ║");
    println!("╚══════════════════════════════════════════════╝");
    println!();

    let router = Router::with_mock();

    // Demo 1: List models
    println!("Demo 1: Listing available models...");
    let all_models = router.list_all_models().await?;
    for (provider_name, model_list) in all_models {
        println!("  Provider '{}': {} models", provider_name, model_list.data.len());
    }
    println!();

    // Demo 2: Send chat request
    println!("Demo 2: Sending chat request...");
    let provider = omniroute_core::providers::MockProvider::new();
    let request = ChatRequest {
        model: "mock-gpt-4".to_string(),
        messages: vec![Message::user("Hello, OmniRoute!")],
        stream: false,
        temperature: None,
        max_tokens: None,
        top_p: None,
        frequency_penalty: None,
        presence_penalty: None,
        stop: None,
        tools: None,
        tool_choice: None,
        response_format: None,
        seed: None,
        user: None,
    };

    let response = provider.chat_completions(request).await?;
    println!("  Response: {}", response.choices[0].message.content);
    println!();

    // Demo 3: Embeddings
    println!("Demo 3: Generating embeddings...");
    let request = EmbeddingRequest {
        model: "mock-embedding-model".to_string(),
        input: EmbeddingInput::String("Hello, world!".to_string()),
        encoding_format: None,
        dimensions: None,
        user: None,
    };

    let response = provider.embeddings(request).await?;
    println!(
        "  Generated {} dimensions",
        response.data[0].embedding.len()
    );
    println!();

    println!("Demo complete!");
    println!("\nFor more information, see the documentation.");

    Ok(())
}
