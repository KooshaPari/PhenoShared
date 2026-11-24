use std::fs;
use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use clap::Args;

#[derive(Args, Debug, Clone)]
pub struct LintArgs {
    /// Repository root to lint (defaults to current directory).
    #[arg(default_value = ".")]
    pub path: PathBuf,
}

pub fn run(args: LintArgs) -> Result<()> {
    let root = args.path.canonicalize().unwrap_or(args.path);
    let boundary = root.join("BOUNDARY.md");
    let content =
        fs::read_to_string(&boundary).with_context(|| format!("read {}", boundary.display()))?;

    let required = ["## Owns", "## Does NOT own", "STACK_POLICY", "DOMAIN_ROLES"];
    for needle in required {
        if !content.contains(needle) {
            bail!("BOUNDARY.md missing required section or link: {needle}");
        }
    }

    println!("boundary lint OK: {}", boundary.display());
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::io::Write;

    use tempfile::tempdir;

    use super::*;

    #[test]
    fn lint_passes_valid_boundary() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("BOUNDARY.md");
        let mut f = fs::File::create(&path).unwrap();
        write!(
            f,
            "# Test\n\n## Owns\n- x\n\n## Does NOT own\n- y\n\n[STACK_POLICY](https://example/STACK_POLICY)\n[DOMAIN_ROLES](https://example/DOMAIN_ROLES)\n"
        )
        .unwrap();
        run(LintArgs {
            path: dir.path().to_path_buf(),
        })
        .unwrap();
    }
}
