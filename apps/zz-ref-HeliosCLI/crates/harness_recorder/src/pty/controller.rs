use anyhow::Result;
use std::time::Duration;

use super::Terminal;
use crate::script::TerminalSettings;

pub struct TerminalController {
    terminal: Terminal,
}

impl TerminalController {
    pub fn new(settings: &TerminalSettings) -> Result<Self> {
        let terminal = Terminal::new(settings)?;
        Ok(Self { terminal })
    }

    pub async fn execute_command(&mut self, command: &str) -> Result<()> {
        log::debug!("Executing command: {}", command);
        self.terminal.execute_command(command).await
    }

    pub async fn type_text(&mut self, text: &str, speed: Duration) -> Result<()> {
        log::debug!("Typing text: {} (speed: {:?})", text, speed);
        self.terminal.type_text(text, speed).await
    }

    pub fn get_output(&self) -> String {
        self.terminal.get_output()
    }

    pub fn get_size(&self) -> (u16, u16) {
        self.terminal.get_size()
    }

    pub async fn wait_for_output(&self, pattern: &str, timeout: Duration) -> Result<bool> {
        self.terminal.wait_for_output(pattern, timeout).await
    }

    pub fn clear_output_buffer(&self) {
        self.terminal.clear_buffer();
    }

    pub fn get_terminal_ref(&self) -> &Terminal {
        &self.terminal
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::script::TerminalSettings;

    fn test_settings() -> TerminalSettings {
        #[cfg(windows)]
        {
            TerminalSettings { shell: "cmd.exe".to_string(), ..Default::default() }
        }
        #[cfg(not(windows))]
        {
            TerminalSettings::default()
        }
    }

    #[tokio::test]
    async fn controller_initializes_and_exposes_terminal_api() {
        let controller = TerminalController::new(&test_settings()).expect("controller");
        let (width, height) = controller.get_size();
        assert!(width > 0 && height > 0);
        controller.clear_output_buffer();
        assert!(controller.get_output().is_empty());
        let _ = controller.get_terminal_ref();
    }

    #[tokio::test]
    async fn controller_executes_command_and_exposes_output() {
        let mut controller = TerminalController::new(&test_settings()).expect("controller");
        controller.execute_command("echo kla-controller-smoke").await.expect("execute");
        let found = controller
            .wait_for_output("kla-controller-smoke", Duration::from_secs(10))
            .await
            .expect("wait");
        assert!(found, "output: {}", controller.get_output());
    }
}
