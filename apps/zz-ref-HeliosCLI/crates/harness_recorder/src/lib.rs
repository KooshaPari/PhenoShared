//! KLA (Kommand Line Automation)
//!
//! A Playwright equivalent for beautiful CLI recordings, screenshots, and automation.
//! Create stunning visual documentation of terminal interactions with ease.
//!
//! # Status
//!
//! Newly absorbed crate (L5-200). Public API surface is intentionally forward-declared;
//! consumers will be wired once the harness orchestrator integration lands.

// Public API surface is forward-declared; callers will be wired by the harness
// orchestrator integration (tracked: L5-200). Dead-code lint is suppressed
// crate-wide until the first consumer lands.
#![allow(dead_code)]
#![allow(unused_imports)]

pub mod cli;
pub mod media;
pub mod pty;
pub mod script;

// Re-export main types for convenience
pub use media::{MediaConfig, MediaRecorder, OutputFormat, ThemeConfig};
pub use pty::{Terminal, TerminalController};
pub use script::{Script, ScriptLoader, ScriptStep, StepType, TerminalSettings};

/// Main KLA interface for programmatic usage
pub struct Kla {
    settings: TerminalSettings,
    output_format: OutputFormat,
    theme: String,
}

impl Kla {
    /// Create a new KLA instance with default settings
    pub fn new() -> Self {
        Self {
            settings: TerminalSettings::default(),
            output_format: OutputFormat::Gif,
            theme: "default".to_string(),
        }
    }

    /// Set terminal dimensions
    pub fn size(mut self, width: u16, height: u16) -> Self {
        self.settings.width = width;
        self.settings.height = height;
        self
    }

    /// Set shell
    pub fn shell<S: Into<String>>(mut self, shell: S) -> Self {
        self.settings.shell = shell.into();
        self
    }

    /// Set theme
    pub fn theme<S: Into<String>>(mut self, theme: S) -> Self {
        self.theme = theme.into();
        self
    }

    /// Set output format
    pub fn format(mut self, format: OutputFormat) -> Self {
        self.output_format = format;
        self
    }

    /// Execute a script and return the results
    pub async fn execute_script(&self, script: &Script) -> anyhow::Result<ExecutionResult> {
        let mut terminal = TerminalController::new(&self.settings)?;
        let media_recorder =
            MediaRecorder::new(self.output_format.clone(), &std::path::PathBuf::from("./output"))?
                .with_theme(&self.theme);

        let mut screenshots = Vec::new();
        let mut recordings = Vec::new();

        for step in &script.steps {
            match &step.step_type {
                StepType::Command { text, wait } => {
                    terminal.execute_command(text).await?;
                    if let Some(duration) = wait {
                        tokio::time::sleep(*duration).await;
                    }
                }
                StepType::Type { text, speed } => {
                    terminal.type_text(text, *speed).await?;
                }
                StepType::Screenshot { name } => {
                    let path = std::path::PathBuf::from(format!("{}.png", name));
                    media_recorder.take_screenshot(&terminal, &path).await?;
                    screenshots.push(path);
                }
                StepType::RecordGif { duration: _, name } => {
                    let path = std::path::PathBuf::from(format!("{}.gif", name));
                    recordings.push(path);
                }
            }
        }

        Ok(ExecutionResult { output: terminal.get_output(), screenshots, recordings })
    }

    /// Take a single screenshot of a command
    pub async fn screenshot(&self, command: &str) -> anyhow::Result<std::path::PathBuf> {
        let script = Script::single_command(command)?;
        let result = self.execute_script(&script).await?;

        // Return the first screenshot if any
        result
            .screenshots
            .into_iter()
            .next()
            .ok_or_else(|| anyhow::anyhow!("No screenshot was generated"))
    }
}

impl Default for Kla {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of executing a KLA script
#[derive(Debug)]
pub struct ExecutionResult {
    pub output: String,
    pub screenshots: Vec<std::path::PathBuf>,
    pub recordings: Vec<std::path::PathBuf>,
}

/// Convenience function for quick automation
pub async fn quick_screenshot(command: &str) -> anyhow::Result<std::path::PathBuf> {
    Kla::new().screenshot(command).await
}

/// Convenience function for executing a script file
pub async fn execute_script_file<P: AsRef<std::path::Path>>(
    path: P,
) -> anyhow::Result<ExecutionResult> {
    let script = ScriptLoader::load_from_file(path)?;
    Kla::new().execute_script(&script).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terminal_settings_default_has_expected_dimensions_and_theme() {
        let settings = TerminalSettings::default();

        assert_eq!(settings.width, 120);
        assert_eq!(settings.height, 30);
        assert_eq!(settings.theme, "default");
    }

    #[test]
    fn output_format_parses_known_values() {
        assert!(matches!(OutputFormat::from_string("png").unwrap(), OutputFormat::Png));
        assert!(matches!(OutputFormat::from_string("gif").unwrap(), OutputFormat::Gif));
        assert!(OutputFormat::from_string("webm").is_err());
    }

    #[test]
    fn test_kla_builder() {
        let kla = Kla::new().size(120, 30).shell("zsh").theme("dracula").format(OutputFormat::Png);

        assert_eq!(kla.settings.width, 120);
        assert_eq!(kla.settings.height, 30);
        assert_eq!(kla.settings.shell, "zsh");
        assert_eq!(kla.theme, "dracula");
    }

    #[tokio::test]
    async fn test_single_command_script() {
        let script = Script::single_command("echo 'Hello, World!'").unwrap();
        assert_eq!(script.steps.len(), 1);

        match &script.steps[0].step_type {
            StepType::Command { text, .. } => {
                assert_eq!(text, "echo 'Hello, World!'");
            }
            _ => panic!("Expected Command step"),
        }
    }
}
