use crate::script::Script;
use anyhow::{Context, Result};
use std::path::Path;

pub struct ScriptLoader;

impl ScriptLoader {
    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Script> {
        let path = path.as_ref();
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read script file: {}", path.display()))?;

        Self::load_from_string(&content)
            .with_context(|| format!("Failed to parse script file: {}", path.display()))
    }

    pub fn load_from_string(content: &str) -> Result<Script> {
        serde_yaml::from_str(content).context("Failed to parse YAML script")
    }

    pub fn save_to_file<P: AsRef<Path>>(script: &Script, path: P) -> Result<()> {
        let path = path.as_ref();
        let content =
            serde_yaml::to_string(script).context("Failed to serialize script to YAML")?;

        std::fs::write(path, content)
            .with_context(|| format!("Failed to write script file: {}", path.display()))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::script::{ScriptStep, StepType, TerminalSettings};
    use std::time::Duration;

    #[test]
    fn test_load_simple_script() {
        let yaml = r#"
name: "Test Script"
settings:
  width: 80
  height: 24
  shell: "bash"
  theme: "dracula"
steps:
  - type: command
    text: "echo hello"
    wait: "1s"
  - type: type
    text: "ls -la"
    speed: "100ms"
  - type: screenshot
    name: "test-shot"
"#;

        let script = ScriptLoader::load_from_string(yaml).unwrap();
        assert_eq!(script.name, "Test Script");
        assert_eq!(script.settings.width, 80);
        assert_eq!(script.steps.len(), 3);
    }

    #[test]
    fn test_roundtrip_serialization() {
        let script = Script {
            name: "Roundtrip Test".to_string(),
            settings: TerminalSettings {
                width: 120,
                height: 30,
                shell: "zsh".to_string(),
                theme: "default".to_string(),
                working_dir: None,
            },
            steps: vec![
                ScriptStep {
                    step_type: StepType::Command {
                        text: "pwd".to_string(),
                        wait: Some(Duration::from_millis(500)),
                    },
                },
                ScriptStep { step_type: StepType::Screenshot { name: "current-dir".to_string() } },
            ],
        };

        let yaml = serde_yaml::to_string(&script).unwrap();
        let loaded = ScriptLoader::load_from_string(&yaml).unwrap();

        assert_eq!(script.name, loaded.name);
        assert_eq!(script.steps.len(), loaded.steps.len());
    }
}
