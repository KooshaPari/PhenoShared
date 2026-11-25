//! BytePort tools CLI — transport, port, codec, and UI CLI bindings.
//!
//! This crate provides a command-line interface that exercises the
//! `byteport-transport` crate's abstractions: codec, port, transport,
//! upload, and UI. It serves as both a developer tool and a reference
//! consumer for the transport layer.

mod tracing_setup;

use byteport_transport::ports::codec::{Codec, WireCodecAdapter};
use byteport_transport::ports::terminal_ui::TerminalUiAdapter;
use byteport_transport::ports::transport::{Transport, WireTransportAdapter};
use byteport_transport::ports::ui::{MockUiAdapter, PromptMessage, UiPort, UiView};
use byteport_transport::{S3UploadTransport, UploadRequest, UploadTransport};
use clap::{Parser, Subcommand};

/// BytePort tools CLI — interact with the transport, codec, UI, and upload layers.
#[derive(Parser, Debug)]
#[command(name = "byteport-cli", version, about)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Codec operations: encode or decode hex data.
    Codec {
        #[command(subcommand)]
        action: CodecAction,
    },
    /// Transport operations: connect, send, receive through a wire transport.
    Transport {
        #[command(subcommand)]
        action: TransportAction,
    },
    /// UI operations: render a view or send a prompt.
    Ui {
        #[command(subcommand)]
        action: UiAction,
    },
    /// Upload operations: create an S3 upload instruction.
    Upload {
        /// Object key (path) for the upload.
        key: String,
        /// MIME content type.
        #[arg(long, default_value = "application/octet-stream")]
        content_type: String,
        /// Content length in bytes.
        #[arg(long, default_value_t = 0)]
        content_length: u64,
        /// S3-compatible endpoint.
        #[arg(long, default_value = "https://storage.example.test")]
        endpoint: String,
        /// S3 bucket name.
        #[arg(long, default_value = "byteport-uploads")]
        bucket: String,
        /// Optional key prefix.
        #[arg(long)]
        prefix: Option<String>,
    },
}

#[derive(Subcommand, Debug)]
enum CodecAction {
    /// Encode raw text to hex representation.
    Encode {
        /// Plain text to encode (e.g. "hello").
        data: String,
    },
    /// Decode hex back to raw text.
    Decode {
        /// Hex-encoded string (e.g. "68656c6c6f").
        hex: String,
    },
}

#[derive(Subcommand, Debug)]
enum TransportAction {
    /// Connect, send, and receive through an in-memory wire transport.
    Ping {
        /// Data to send.
        #[arg(default_value = "ping")]
        data: String,
    },
}

#[derive(Subcommand, Debug)]
enum UiAction {
    /// Render a view (Dashboard, DeviceList, TestResults, Settings).
    View {
        /// Name of the view to render.
        view: String,
    },
    /// Send a prompt and show the expected response kind.
    Prompt {
        /// Prompt kind: info, warning, error, confirm, choice, input.
        kind: String,
        /// Prompt title.
        title: String,
        /// Prompt body text.
        body: String,
    },
}

fn main() {
    let _shutdown = tracing_setup::ShutdownBanner;
    tracing_setup::log_startup_banner();
    let cli = Cli::parse();
    match cli.command {
        Command::Codec { action } => run_codec(action),
        Command::Transport { action } => run_transport(action),
        Command::Ui { action } => run_ui(action),
        Command::Upload {
            key,
            content_type,
            content_length,
            endpoint,
            bucket,
            prefix,
        } => run_upload(key, content_type, content_length, endpoint, bucket, prefix),
    }
}

fn run_codec(action: CodecAction) {
    let codec = WireCodecAdapter::new();
    match action {
        CodecAction::Encode { data } => {
            let encoded = codec.encode(data.as_bytes()).expect("encode should succeed");
            println!("{}", String::from_utf8_lossy(&encoded));
        }
        CodecAction::Decode { hex } => {
            let decoded = codec.decode(hex.as_bytes()).expect("decode should succeed");
            println!("{}", String::from_utf8_lossy(&decoded));
        }
    }
}

fn run_transport(action: TransportAction) {
    let mut transport = WireTransportAdapter::new();
    transport.connect("memory://pipe").expect("connect");
    match action {
        TransportAction::Ping { data } => {
            let sent = transport.send(data.as_bytes()).expect("send");
            println!("Sent {sent} bytes");
            let echoed = transport.take_tx();
            println!("Echo (tx buffer): {}", String::from_utf8_lossy(&echoed));
        }
    }
}

fn run_ui(action: UiAction) {
    match action {
        UiAction::View { view } => {
            let ui_view = match view.to_lowercase().as_str() {
                "dashboard" => UiView::Dashboard,
                "devicelist" | "device-list" | "devices" => UiView::DeviceList,
                "testresults" | "test-results" | "tests" => UiView::TestResults,
                "settings" => UiView::Settings,
                _ => {
                    eprintln!("Unknown view: {view}");
                    std::process::exit(1);
                }
            };
            let header = TerminalUiAdapter::render_view(&ui_view);
            println!("{header}");
        }
        UiAction::Prompt { kind, title, body } => {
            let msg = match kind.to_lowercase().as_str() {
                "info" => PromptMessage::info(title, body),
                "warning" => PromptMessage::warning(title, body),
                "error" => PromptMessage::error(title, body),
                "confirm" => PromptMessage::confirm(title, body),
                "choice" => PromptMessage::choice(title, body, vec!["yes".into(), "no".into()]),
                "input" => PromptMessage::input(title, body, None),
                _ => {
                    eprintln!("Unknown prompt kind: {kind}");
                    std::process::exit(1);
                }
            };
            let ui = MockUiAdapter::new();
            match ui.prompt(&msg) {
                Ok(resp) => println!("Prompt response: {resp:?}"),
                Err(e) => {
                    println!("Prompt result: {e} (cancelled expected for mock)")
                }
            }
        }
    }
}

fn run_upload(
    key: String,
    content_type: String,
    content_length: u64,
    endpoint: String,
    bucket: String,
    prefix: Option<String>,
) {
    let transport = S3UploadTransport::new(endpoint, bucket, prefix);
    let request = UploadRequest {
        object_key: key,
        content_type,
        content_length,
    };
    match transport.create_upload(&request) {
        Ok(instruction) => {
            println!("Upload method: {}", instruction.method);
            println!("Upload URL: {}", instruction.url);
            println!("Headers:");
            for (k, v) in &instruction.headers {
                println!("  {k}: {v}");
            }
        }
        Err(e) => {
            eprintln!("Upload error: {e}");
            std::process::exit(1);
        }
    }
}
