//! Agent/human detection example.
//!
//! Shows how environment variables affect DisplayContext detection.

use fastmcp_console::detection::{DisplayContext, is_agent_context, should_enable_rich};

fn main() {
    eprintln!("Detected context: {:?}", DisplayContext::detect());
    eprintln!("is_agent_context(): {}", is_agent_context());
    eprintln!("should_enable_rich(): {}", should_enable_rich());

    eprintln!("To force rich output: set FASTMCP_RICH=1");
    eprintln!("To force plain output: set FASTMCP_PLAIN=1 or NO_COLOR=1");
}
