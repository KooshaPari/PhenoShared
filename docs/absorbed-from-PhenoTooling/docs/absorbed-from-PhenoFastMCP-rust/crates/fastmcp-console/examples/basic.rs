//! Basic fastmcp-console usage.
//!
//! Demonstrates banner rendering, rules, and simple output.

use fastmcp_console::banner::StartupBanner;
use fastmcp_console::console::FastMcpConsole;
use fastmcp_console::logging::RichLoggerBuilder;
use log::Level;

fn main() {
    // Optional: initialize rich logger (stderr only).
    let _ = RichLoggerBuilder::new()
        .level(Level::Info)
        .with_targets(true)
        .init();

    let console = FastMcpConsole::new();
    console.rule(Some("FastMCP Console"));

    let banner = StartupBanner::new("basic-demo", "0.1.0")
        .tools(2)
        .resources(1)
        .prompts(1)
        .transport("stdio")
        .description("Basic console example");
    banner.render(&console);

    console.print("Console initialized.");
    console.print("Tip: set FASTMCP_PLAIN=1 to force plain output.");
}
