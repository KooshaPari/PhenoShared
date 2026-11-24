//! Custom theme styling example.
//!
//! Demonstrates using a local theme instance to drive custom styles.

use fastmcp_console::console::FastMcpConsole;
use fastmcp_console::theme::FastMcpTheme;
use rich_rust::prelude::{Color, Style};

fn main() {
    let console = FastMcpConsole::new();

    // Create a local theme and customize a color.
    let theme = FastMcpTheme {
        primary: Color::from_rgb(255, 120, 0),
        ..FastMcpTheme::default()
    };

    let headline = Style::new().bold().color(theme.primary);
    console.print_styled("Custom theme preview", headline);

    // You can also mix custom styles with the default console theme.
    let accent = Style::new().color(Color::from_rgb(0, 180, 160));
    console.print_styled("Secondary accent text", accent);
}
