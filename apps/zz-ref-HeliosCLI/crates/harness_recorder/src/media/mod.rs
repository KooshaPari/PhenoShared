use anyhow::Result;
use std::path::Path;

pub mod gif;
pub mod recorder;
pub mod screenshot;

pub use recorder::MediaRecorder;

#[derive(Debug, Clone)]
pub enum OutputFormat {
    Png,
    Gif,
    Mp4,
}

impl OutputFormat {
    pub fn from_string(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "png" => Ok(OutputFormat::Png),
            "gif" => Ok(OutputFormat::Gif),
            "mp4" => Ok(OutputFormat::Mp4),
            _ => {
                Err(anyhow::anyhow!("Unsupported format: {}. Supported formats: png, gif, mp4", s))
            }
        }
    }

    pub fn extension(&self) -> &str {
        match self {
            OutputFormat::Png => "png",
            OutputFormat::Gif => "gif",
            OutputFormat::Mp4 => "mp4",
        }
    }
}

pub trait MediaGenerator {
    fn create_output(&self, content: &str, output_path: &Path) -> Result<()>;
}

#[derive(Clone)]
pub struct MediaConfig {
    pub font_family: String,
    pub font_size: u16,
    pub line_height: f32,
    pub padding: u16,
    pub background_color: (u8, u8, u8),
    pub text_color: (u8, u8, u8),
    pub cursor_color: (u8, u8, u8),
}

impl Default for MediaConfig {
    fn default() -> Self {
        Self {
            font_family: "JetBrains Mono".to_string(),
            font_size: 14,
            line_height: 1.2,
            padding: 20,
            background_color: (40, 44, 52), // Dark background
            text_color: (171, 178, 191),    // Light text
            cursor_color: (97, 175, 239),   // Blue cursor
        }
    }
}

#[derive(Clone)]
pub struct ThemeConfig {
    pub name: String,
    pub background: (u8, u8, u8),
    pub foreground: (u8, u8, u8),
    pub cursor: (u8, u8, u8),
    pub selection: (u8, u8, u8),
    pub colors: Vec<(u8, u8, u8)>, // ANSI colors (16 colors)
}

impl ThemeConfig {
    pub fn default_theme() -> Self {
        Self {
            name: "Default".to_string(),
            background: (40, 44, 52),
            foreground: (171, 178, 191),
            cursor: (97, 175, 239),
            selection: (75, 81, 96),
            colors: vec![
                (40, 44, 52),    // Black
                (224, 108, 117), // Red
                (152, 195, 121), // Green
                (229, 192, 123), // Yellow
                (97, 175, 239),  // Blue
                (198, 120, 221), // Magenta
                (86, 182, 194),  // Cyan
                (171, 178, 191), // White
                (92, 99, 112),   // Bright Black
                (224, 108, 117), // Bright Red
                (152, 195, 121), // Bright Green
                (229, 192, 123), // Bright Yellow
                (97, 175, 239),  // Bright Blue
                (198, 120, 221), // Bright Magenta
                (86, 182, 194),  // Bright Cyan
                (255, 255, 255), // Bright White
            ],
        }
    }

    pub fn dracula_theme() -> Self {
        Self {
            name: "Dracula".to_string(),
            background: (40, 42, 54),
            foreground: (248, 248, 242),
            cursor: (248, 248, 242),
            selection: (68, 71, 90),
            colors: vec![
                (40, 42, 54),    // Black
                (255, 85, 85),   // Red
                (80, 250, 123),  // Green
                (241, 250, 140), // Yellow
                (139, 233, 253), // Blue
                (255, 121, 198), // Magenta
                (139, 233, 253), // Cyan
                (248, 248, 242), // White
                (98, 114, 164),  // Bright Black
                (255, 85, 85),   // Bright Red
                (80, 250, 123),  // Bright Green
                (241, 250, 140), // Bright Yellow
                (139, 233, 253), // Bright Blue
                (255, 121, 198), // Bright Magenta
                (139, 233, 253), // Bright Cyan
                (255, 255, 255), // Bright White
            ],
        }
    }

    pub fn from_name(name: &str) -> Self {
        match name.to_lowercase().as_str() {
            "dracula" => Self::dracula_theme(),
            _ => Self::default_theme(),
        }
    }
}
