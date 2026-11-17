use anyhow::Result;
use vt100::Parser;

pub struct TerminalCapture {
    parser: Parser,
    history: Vec<String>,
}

impl TerminalCapture {
    pub fn new(width: u16, height: u16) -> Self {
        Self { parser: Parser::new(height, width, 0), history: Vec::new() }
    }

    pub fn process_output(&mut self, output: &str) -> Result<()> {
        self.parser.process(output.as_bytes());
        self.history.push(output.to_string());
        Ok(())
    }

    pub fn get_screen_contents(&self) -> String {
        self.parser.screen().contents()
    }

    pub fn get_formatted_contents(&self) -> Vec<String> {
        let screen = self.parser.screen();

        // Use the rows iterator method properly
        screen.rows(0, screen.size().0).map(|row| row.trim_end().to_string()).collect()
    }

    pub fn get_cursor_position(&self) -> (u16, u16) {
        let (row, col) = self.parser.screen().cursor_position();
        (col, row)
    }

    pub fn get_history(&self) -> &[String] {
        &self.history
    }

    pub fn clear_history(&mut self) {
        self.history.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_terminal_capture() {
        let mut capture = TerminalCapture::new(80, 24);

        capture.process_output("Hello, world!\n").unwrap();
        let contents = capture.get_screen_contents();

        assert!(contents.contains("Hello, world!"));
    }

    #[test]
    fn test_formatted_contents() {
        let mut capture = TerminalCapture::new(80, 24);

        capture.process_output("Line 1\nLine 2\n").unwrap();
        let lines = capture.get_formatted_contents();

        assert!(lines[0].contains("Line 1"));
        assert!(lines[1].contains("Line 2"));
    }
}
