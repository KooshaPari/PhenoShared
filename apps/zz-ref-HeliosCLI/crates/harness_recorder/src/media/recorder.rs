use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

use super::gif::GifGenerator;
use super::screenshot::ScreenshotGenerator;
use super::{MediaConfig, OutputFormat, ThemeConfig};
use crate::pty::TerminalController;

pub struct MediaRecorder {
    format: OutputFormat,
    output_dir: PathBuf,
    config: MediaConfig,
    theme: ThemeConfig,
    gif_generator: Option<GifGenerator>,
}

impl MediaRecorder {
    pub fn new(format: OutputFormat, output_dir: &Path) -> Result<Self> {
        std::fs::create_dir_all(output_dir).with_context(|| {
            format!("Failed to create output directory: {}", output_dir.display())
        })?;

        Ok(Self {
            format,
            output_dir: output_dir.to_path_buf(),
            config: MediaConfig::default(),
            theme: ThemeConfig::default_theme(),
            gif_generator: None,
        })
    }

    pub fn with_theme(mut self, theme_name: &str) -> Self {
        self.theme = ThemeConfig::from_name(theme_name);
        self
    }

    pub fn with_config(mut self, config: MediaConfig) -> Self {
        self.config = config;
        self
    }

    pub async fn take_screenshot(
        &self,
        terminal: &TerminalController,
        output_path: &Path,
    ) -> Result<()> {
        let screenshot_gen = ScreenshotGenerator::new(&self.config, &self.theme);
        let content = terminal.get_output();
        let (width, height) = terminal.get_size();

        screenshot_gen
            .generate(&content, width, height, output_path)
            .context("Failed to generate screenshot")?;

        Ok(())
    }

    pub async fn start_gif_recording(&mut self, terminal: &TerminalController) -> Result<()> {
        let (width, height) = terminal.get_size();
        self.gif_generator = Some(GifGenerator::new(&self.config, &self.theme, width, height)?);
        Ok(())
    }

    pub async fn capture_gif_frame(&mut self, terminal: &TerminalController) -> Result<()> {
        if let Some(ref mut gif_gen) = self.gif_generator {
            let content = terminal.get_output();
            let (width, height) = terminal.get_size();
            gif_gen.add_frame(&content, width, height)?;
        }
        Ok(())
    }

    pub async fn stop_gif_recording(&mut self, output_path: &Path) -> Result<()> {
        if let Some(gif_gen) = self.gif_generator.take() {
            gif_gen.save(output_path).context("Failed to save GIF")?;
        }
        Ok(())
    }

    pub fn get_output_path(&self, name: &str) -> PathBuf {
        self.output_dir.join(format!("{}.{}", name, self.format.extension()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_media_recorder_creation() {
        let temp_dir = TempDir::new().unwrap();
        let _recorder = MediaRecorder::new(OutputFormat::Png, temp_dir.path()).unwrap();

        assert!(temp_dir.path().exists());
    }

    #[test]
    fn test_output_path_generation() {
        let temp_dir = TempDir::new().unwrap();
        let recorder = MediaRecorder::new(OutputFormat::Gif, temp_dir.path()).unwrap();

        let path = recorder.get_output_path("test");
        assert_eq!(path.file_name().unwrap(), "test.gif");
    }
}
