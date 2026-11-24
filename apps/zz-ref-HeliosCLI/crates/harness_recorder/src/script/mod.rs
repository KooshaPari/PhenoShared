use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::Duration;

pub mod loader;
pub mod types;

pub use loader::ScriptLoader;
// pub use types::*; // Not needed since types just re-exports from this module

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Script {
    pub name: String,
    pub settings: TerminalSettings,
    pub steps: Vec<ScriptStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TerminalSettings {
    #[serde(default = "default_width")]
    pub width: u16,

    #[serde(default = "default_height")]
    pub height: u16,

    #[serde(default = "default_shell")]
    pub shell: String,

    #[serde(default = "default_theme")]
    pub theme: String,

    #[serde(default)]
    pub working_dir: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScriptStep {
    #[serde(flatten)]
    pub step_type: StepType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum StepType {
    Command {
        text: String,
        #[serde(default, with = "duration_option")]
        wait: Option<Duration>,
    },
    Type {
        text: String,
        #[serde(default = "default_typing_speed", with = "duration_ms")]
        speed: Duration,
    },
    Screenshot {
        name: String,
    },
    RecordGif {
        #[serde(with = "duration_secs")]
        duration: Duration,
        name: String,
    },
}

impl Script {
    pub fn single_command(command: &str) -> Result<Self> {
        Ok(Script {
            name: format!("Single command: {}", command),
            settings: TerminalSettings::default(),
            steps: vec![ScriptStep {
                step_type: StepType::Command {
                    text: command.to_string(),
                    wait: Some(Duration::from_millis(500)),
                },
            }],
        })
    }
}

impl Default for TerminalSettings {
    fn default() -> Self {
        Self {
            width: default_width(),
            height: default_height(),
            shell: default_shell(),
            theme: default_theme(),
            working_dir: None,
        }
    }
}

// Default value functions
fn default_width() -> u16 {
    120
}
fn default_height() -> u16 {
    30
}
fn default_shell() -> String {
    std::env::var("SHELL").unwrap_or_else(|_| "/bin/bash".to_string())
}
fn default_theme() -> String {
    "default".to_string()
}
fn default_typing_speed() -> Duration {
    Duration::from_millis(50)
}

// Serde duration helpers
mod duration_option {
    use super::*;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(duration: &Option<Duration>, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        match duration {
            Some(d) => format!("{}ms", d.as_millis()).serialize(serializer),
            None => serializer.serialize_none(),
        }
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Option<Duration>, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s: Option<String> = Option::deserialize(deserializer)?;
        match s {
            Some(s) => Ok(Some(parse_duration(&s).map_err(serde::de::Error::custom)?)),
            None => Ok(None),
        }
    }
}

mod duration_ms {
    use super::*;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(duration: &Duration, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        format!("{}ms", duration.as_millis()).serialize(serializer)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Duration, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        parse_duration(&s).map_err(serde::de::Error::custom)
    }
}

mod duration_secs {
    use super::*;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(duration: &Duration, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        format!("{}s", duration.as_secs()).serialize(serializer)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Duration, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        parse_duration(&s).map_err(serde::de::Error::custom)
    }
}

fn parse_duration(s: &str) -> Result<Duration> {
    if s.ends_with("ms") {
        let ms: u64 = s.trim_end_matches("ms").parse().context("Invalid milliseconds value")?;
        Ok(Duration::from_millis(ms))
    } else if s.ends_with('s') {
        let secs: u64 = s.trim_end_matches('s').parse().context("Invalid seconds value")?;
        Ok(Duration::from_secs(secs))
    } else {
        Err(anyhow::anyhow!("Duration must end with 'ms' or 's'"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_duration_accepts_ms_and_seconds() {
        assert_eq!(parse_duration("250ms").unwrap(), Duration::from_millis(250));
        assert_eq!(parse_duration("2s").unwrap(), Duration::from_secs(2));
        assert!(parse_duration("bad").is_err());
    }

    #[test]
    fn single_command_script_uses_defaults() {
        let script = Script::single_command("echo hi").unwrap();
        assert_eq!(script.steps.len(), 1);
        assert_eq!(script.settings.width, 120);
    }
}
