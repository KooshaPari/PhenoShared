use anyhow::{anyhow, Result};
use clap::Parser;
use regex::Regex;
use std::fs;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "commit-msg-check")]
#[command(about = "Validate commit message: conventional commits + DCO sign-off")]
struct Args {
    /// Path to commit message file (typically .git/COMMIT_EDITMSG)
    commit_msg_path: PathBuf,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let message = fs::read_to_string(&args.commit_msg_path)
        .map_err(|e| anyhow!("Failed to read commit message: {}", e))?;

    let message = message.trim();
    if message.is_empty() {
        return Err(anyhow!("Commit message is empty"));
    }

    // Check conventional commit format on first line
    let first_line = message.lines().next().unwrap_or("");
    validate_conventional_commit(first_line)?;

    // Check for DCO sign-off
    validate_dco_signoff(message)?;

    Ok(())
}

fn validate_conventional_commit(first_line: &str) -> Result<()> {
    // Pattern: <type>(<scope>): <description> or <type>: <description>
    // Allow merge commits to bypass
    if first_line.starts_with("Merge ") {
        return Ok(());
    }

    let re = Regex::new(r"^(feat|fix|docs|chore|test|refactor|perf|ci)(\([^)]+\))?: .+")
        .expect("regex is valid");

    if !re.is_match(first_line) {
        return Err(anyhow!(
            "Invalid conventional commit format.\n\
             Expected: <type>(<scope>): <description>\n\
             Types: feat, fix, docs, chore, test, refactor, perf, ci\n\
             Got: {}",
            first_line
        ));
    }

    Ok(())
}

fn validate_dco_signoff(message: &str) -> Result<()> {
    // Look for "Signed-off-by:" line with email
    let has_dco = message.lines().any(|line| {
        line.trim().starts_with("Signed-off-by:") && line.contains('<') && line.contains('>')
    });

    if !has_dco {
        return Err(anyhow!(
            "Missing DCO sign-off.\n\
             Add to your commit: Signed-off-by: Your Name <your.email@example.com>\n\
             Or use: git commit -s -m \"...\""
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── validate_conventional_commit ──────────────────────────────────────

    #[test]
    fn happy_feat_no_scope() {
        assert!(validate_conventional_commit("feat: add voxel LOD system").is_ok());
    }

    #[test]
    fn happy_fix_with_scope() {
        assert!(validate_conventional_commit("fix(render): correct frustum cull z-lift").is_ok());
    }

    #[test]
    fn happy_all_types() {
        for ty in &[
            "feat", "fix", "docs", "chore", "test", "refactor", "perf", "ci",
        ] {
            let line = format!("{}: some description", ty);
            assert!(
                validate_conventional_commit(&line).is_ok(),
                "type {} should pass",
                ty
            );
        }
    }

    #[test]
    fn merge_commit_bypasses_check() {
        assert!(validate_conventional_commit("Merge pull request #42 from org/branch").is_ok());
    }

    #[test]
    fn missing_colon_space_fails() {
        let err = validate_conventional_commit("feat add something").unwrap_err();
        assert!(err.to_string().contains("Invalid conventional commit"));
    }

    #[test]
    fn unknown_type_fails() {
        let err = validate_conventional_commit("update: something").unwrap_err();
        assert!(err.to_string().contains("Invalid conventional commit"));
    }

    #[test]
    fn empty_description_fails() {
        // "feat: " with no description after the space
        let err = validate_conventional_commit("feat: ").unwrap_err();
        assert!(err.to_string().contains("Invalid conventional commit"));
    }

    // ── validate_dco_signoff ──────────────────────────────────────────────

    #[test]
    fn happy_dco_present() {
        let msg = "feat: add thing\n\nSigned-off-by: Alice <alice@example.com>";
        assert!(validate_dco_signoff(msg).is_ok());
    }

    #[test]
    fn dco_missing_entirely_fails() {
        let msg = "feat: add thing\n\nSome body text.";
        let err = validate_dco_signoff(msg).unwrap_err();
        assert!(err.to_string().contains("Missing DCO sign-off"));
    }

    #[test]
    fn dco_without_angle_brackets_fails() {
        // "Signed-off-by: Alice alice@example.com" — no < >
        let msg = "feat: thing\n\nSigned-off-by: Alice alice@example.com";
        let err = validate_dco_signoff(msg).unwrap_err();
        assert!(err.to_string().contains("Missing DCO sign-off"));
    }

    #[test]
    fn dco_indented_is_accepted() {
        // Some tools emit with leading whitespace
        let msg = "feat: thing\n\n  Signed-off-by: Bob <bob@example.com>";
        assert!(validate_dco_signoff(msg).is_ok());
    }

    #[test]
    fn multiple_signoffs_accepted() {
        let msg = "feat: thing\n\nSigned-off-by: Alice <a@e.com>\nSigned-off-by: Bob <b@e.com>";
        assert!(validate_dco_signoff(msg).is_ok());
    }
}
