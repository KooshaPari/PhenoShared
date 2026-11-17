use anyhow::{Context, Result};
use std::path::PathBuf;

use crate::media::{MediaRecorder, OutputFormat};
use crate::pty::TerminalController;
use crate::script::{Script, ScriptLoader};

pub async fn record_command(
    script_path: PathBuf,
    output_dir: PathBuf,
    format: String,
) -> Result<()> {
    println!("Recording {}", script_path.display());

    // Load script
    let script = ScriptLoader::load_from_file(&script_path)
        .with_context(|| format!("Failed to load script: {}", script_path.display()))?;

    // Parse output format
    let output_format = OutputFormat::from_string(&format)?;

    // Create output directory
    std::fs::create_dir_all(&output_dir)
        .with_context(|| format!("Failed to create output directory: {}", output_dir.display()))?;

    // Initialize terminal controller
    let mut terminal = TerminalController::new(&script.settings)?;

    // Initialize media recorder
    let mut recorder = MediaRecorder::new(output_format, &output_dir)?;

    // Execute script
    println!("Executing {} steps", script.steps.len());

    // Track produced artifacts so we can render a summary panel at the end.
    let mut artifacts: Vec<String> = Vec::new();

    for (i, step) in script.steps.iter().enumerate() {
        println!("Step {}/{}: {:?}", i + 1, script.steps.len(), step.step_type);

        match step.step_type {
            crate::script::StepType::Command { ref text, wait } => {
                terminal.execute_command(text).await?;
                if let Some(duration) = wait {
                    tokio::time::sleep(duration).await;
                }
            }
            crate::script::StepType::Type { ref text, speed } => {
                terminal.type_text(text, speed).await?;
            }
            crate::script::StepType::Screenshot { ref name } => {
                let screenshot_path = output_dir.join(format!("{}.png", name));
                recorder.take_screenshot(&terminal, &screenshot_path).await?;
                println!("Screenshot saved: {}", screenshot_path.display());
                artifacts.push(format!("📸 {}", screenshot_path.display()));
            }
            crate::script::StepType::RecordGif { duration, ref name } => {
                let gif_path = output_dir.join(format!("{}.gif", name));
                recorder.start_gif_recording(&terminal).await?;
                // Capture frames at 1-second intervals during the recording duration
                let frame_interval = std::time::Duration::from_secs(1);
                let mut elapsed = std::time::Duration::ZERO;
                while elapsed < duration {
                    tokio::time::sleep(frame_interval).await;
                    elapsed += frame_interval;
                    if elapsed < duration {
                        // Capture a frame from the current terminal state
                        if let Err(e) = recorder.capture_gif_frame(&terminal).await {
                            log::warn!("Failed to capture GIF frame: {}", e);
                        }
                    }
                }
                recorder.stop_gif_recording(&gif_path).await?;
                println!("GIF saved: {}", gif_path.display());
                artifacts.push(format!("🎞️ {}", gif_path.display()));
            }
        }
    }

    print_recording_summary(&output_dir, script.steps.len(), &artifacts);
    Ok(())
}

/// Render the end-of-run recording summary as a rich panel via the
/// Phenotype-org rck-core toolkit. Capability detection degrades the panel to
/// plain ASCII when piped, in CI, or on terminals without graphics support, so
/// the output stays pipe-safe.
fn print_recording_summary(output_dir: &std::path::Path, steps: usize, artifacts: &[String]) {
    use std::io::Write;

    let caps = rck_core::detect();

    let mut lines: Vec<String> = vec![
        "Done".to_string(),
        format!("steps    : {steps}"),
        format!("output   : {}", output_dir.display()),
    ];
    if artifacts.is_empty() {
        lines.push("artifacts: (none)".to_string());
    } else {
        lines.push("artifacts:".to_string());
        lines.extend(artifacts.iter().map(|a| format!("  {a}")));
    }
    let line_refs: Vec<&str> = lines.iter().map(String::as_str).collect();

    // Rounded (unicode) border on a real terminal; plain ASCII border when
    // piped or in CI so downstream consumers never see unicode box-drawing.
    let border =
        if caps.is_tty { rck_core::BorderStyle::Rounded } else { rck_core::BorderStyle::Ascii };

    let mut out = std::io::stdout().lock();
    // On any rendering failure, fall back to a plain status line so the command
    // never fails just because of presentation.
    if rck_core::emit_panel(&mut out, &caps, "kla record", &line_refs, border)
        .and_then(|()| out.flush())
        .is_err()
    {
        println!("✅ Done");
    }
}

pub async fn screenshot_command(command: String, output: PathBuf) -> Result<()> {
    println!("📸 {}", command);

    // Create a simple single-command script
    let script = Script::single_command(&command)?;

    // Initialize terminal
    let mut terminal = TerminalController::new(&script.settings)?;

    // Execute command
    terminal.execute_command(&command).await?;

    // Take screenshot
    let recorder =
        MediaRecorder::new(OutputFormat::Png, output.parent().unwrap_or(&PathBuf::from(".")))?;
    recorder.take_screenshot(&terminal, &output).await?;

    println!("Screenshot saved: {}", output.display());
    Ok(())
}

pub async fn demo_command(script_path: PathBuf, interactive: bool) -> Result<()> {
    println!("🎭 {}", script_path.display());

    let script = ScriptLoader::load_from_file(&script_path)?;
    let mut terminal = TerminalController::new(&script.settings)?;

    for (i, step) in script.steps.iter().enumerate() {
        if interactive {
            println!("\n📋 Step {}/{}: {:?}", i + 1, script.steps.len(), step.step_type);
            println!("Press Enter to continue...");
            let mut input = String::new();
            std::io::stdin().read_line(&mut input)?;
        }

        match step.step_type {
            crate::script::StepType::Command { ref text, wait } => {
                terminal.execute_command(text).await?;
                if let Some(duration) = wait {
                    tokio::time::sleep(duration).await;
                }
            }
            crate::script::StepType::Type { ref text, speed } => {
                terminal.type_text(text, speed).await?;
            }
            _ => {} // Skip recording steps in demo mode
        }
    }

    println!("✅ Done");
    Ok(())
}

pub async fn convert_command(input: PathBuf, output: PathBuf) -> Result<()> {
    println!("🔄 {} → {}", input.display(), output.display());

    // Load the script from the input file — supports both .yaml and .json.
    let content = std::fs::read_to_string(&input)
        .with_context(|| format!("Failed to read input file: {}", input.display()))?;

    let script: crate::script::Script =
        if input.extension().is_some_and(|e| e == "json" || e.to_string_lossy() == "kla.json") {
            serde_json::from_str(&content)
                .with_context(|| format!("Failed to parse JSON script: {}", input.display()))?
        } else {
            // Default: treat as YAML
            serde_yaml::from_str(&content)
                .with_context(|| format!("Failed to parse YAML script: {}", input.display()))?
        };

    // Determine output format from the file extension.
    let out_ext =
        output.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default();

    let serialized = match out_ext.as_str() {
        "json" | "kla.json" => {
            serde_json::to_string_pretty(&script).context("Failed to serialize script to JSON")?
        }
        "yaml" | "kla.yaml" | "yml" => {
            serde_yaml::to_string(&script).context("Failed to serialize script to YAML")?
        }
        other => {
            anyhow::bail!(
                "Unsupported output format '.{}'. Supported: .json, .kla.json, .yaml, .kla.yaml, .yml",
                other
            );
        }
    };

    // Ensure parent directory exists.
    if let Some(parent) = output.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create output directory: {}", parent.display()))?;
    }

    std::fs::write(&output, serialized)
        .with_context(|| format!("Failed to write output file: {}", output.display()))?;

    println!("  Steps: {}", script.steps.len());
    println!("  Output: {}", output.display());
    println!("✅ Done");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn print_recording_summary_writes_ascii_when_not_tty() {
        let dir = std::path::Path::new("artifacts/test-output");
        print_recording_summary(dir, 2, &["demo.png".to_string()]);
    }

    #[tokio::test]
    async fn convert_yaml_to_json_roundtrips() {
        let dir = tempfile::tempdir().expect("tempdir");
        let input = dir.path().join("script.kla.yaml");
        let output = dir.path().join("script.kla.json");
        let yaml = r#"name: convert-test
settings:
  width: 80
  height: 24
  shell: sh
steps:
  - type: command
    text: echo hello
    wait: 500ms
"#;
        std::fs::write(&input, yaml).expect("write yaml input");
        convert_command(input, output.clone()).await.expect("convert");
        assert!(output.exists(), "output JSON should exist");
        let json_content = std::fs::read_to_string(&output).unwrap();
        let parsed: crate::script::Script = serde_json::from_str(&json_content).unwrap();
        assert_eq!(parsed.name, "convert-test");
        assert_eq!(parsed.steps.len(), 1);
    }

    #[tokio::test]
    async fn convert_json_to_yaml_roundtrips() {
        let dir = tempfile::tempdir().expect("tempdir");
        let input = dir.path().join("script.json");
        let output = dir.path().join("converted.yaml");
        let json_str = r#"{"name":"json-input","settings":{"width":100,"height":30,"shell":"bash","theme":"default"},"steps":[{"type":"command","text":"ls"}]}"#;
        std::fs::write(&input, json_str).expect("write json input");
        convert_command(input, output.clone()).await.expect("convert");
        assert!(output.exists(), "output YAML should exist");
        let yaml_content = std::fs::read_to_string(&output).unwrap();
        let parsed: crate::script::Script = serde_yaml::from_str(&yaml_content).unwrap();
        assert_eq!(parsed.name, "json-input");
        assert_eq!(parsed.steps.len(), 1);
    }

    #[tokio::test]
    async fn convert_unsupported_extension_fails() {
        let dir = tempfile::tempdir().expect("tempdir");
        let input = dir.path().join("script.kla.yaml");
        let output = dir.path().join("output.xml");
        let yaml = r#"name: test
settings:
  width: 80
  height: 24
  shell: sh
steps: []
"#;
        std::fs::write(&input, yaml).expect("write yaml");
        let result = convert_command(input, output).await;
        assert!(result.is_err(), "unsupported extension should fail");
    }

    #[tokio::test]
    async fn record_command_runs_minimal_script() {
        let dir = tempfile::tempdir().expect("tempdir");
        let script_path = dir.path().join("smoke.kla.yaml");
        #[cfg(windows)]
        let yaml = r#"
name: smoke
settings:
  width: 80
  height: 24
  shell: cmd.exe
steps:
  - type: command
    text: echo record-smoke
    wait: 500ms
"#;
        #[cfg(not(windows))]
        let yaml = r#"
name: smoke
settings:
  width: 80
  height: 24
  shell: sh
steps:
  - type: command
    text: echo record-smoke
    wait: 500ms
"#;
        std::fs::write(&script_path, yaml).expect("write script");
        let output_dir = dir.path().join("out");
        record_command(script_path, output_dir.clone(), "png".to_string()).await.expect("record");
        assert!(output_dir.is_dir());
    }
}
