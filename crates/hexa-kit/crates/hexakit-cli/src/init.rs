use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use clap::Args;

use crate::registry::{validate_domain_flag, DomainRolesRegistry};
use crate::{boundary, lang, manifest};

const GITHUB_ORG_REPO: &str = "<REDACTED>/.github";

#[derive(Args, Debug, Clone)]
pub struct InitArgs {
    /// Target directory (defaults to current directory).
    #[arg(default_value = ".")]
    pub path: PathBuf,

    /// Domain role id from bundled registry/domain-roles.json.
    #[arg(long)]
    pub domain: String,

    /// Language tier for scaffold selection (default: rust).
    #[arg(long, default_value = "rust")]
    pub lang: String,

    /// Required for edge-tier languages per STACK_POLICY.
    #[arg(long)]
    pub justify: Option<String>,

    /// Comma-separated phenoSDK extras for phenosdk.manifest.toml.
    #[arg(long, value_delimiter = ',')]
    pub extras: Vec<String>,

    /// Skip TestingKit `.githooks/` placeholder stamp.
    #[arg(long)]
    pub no_hooks: bool,

    /// Skip CI workflow reference section in generated README.
    #[arg(long)]
    pub no_ci: bool,

    /// Print planned files without writing.
    #[arg(long)]
    pub dry_run: bool,

    /// Overwrite existing stamped files.
    #[arg(long)]
    pub force: bool,
}

pub fn run(args: InitArgs) -> Result<()> {
    lang::validate_lang_gate(&args.lang, args.justify.as_deref())?;

    let registry = DomainRolesRegistry::bundled()?;
    validate_domain_flag(&args.domain, &registry)?;
    let domain = registry.find(&args.domain)?.clone();

    let target = args.path.canonicalize().unwrap_or(args.path.clone());
    if !args.dry_run && !target.exists() {
        fs::create_dir_all(&target).with_context(|| format!("create {}", target.display()))?;
    }

    let mut planned: Vec<(PathBuf, String)> = Vec::new();

    planned.push((
        target.join("BOUNDARY.md"),
        boundary::render_boundary(&domain, &registry, &args.lang, args.justify.as_deref()),
    ));

    if !args.extras.is_empty() {
        planned.push((
            target.join("phenosdk.manifest.toml"),
            manifest::render_phenosdk_manifest(&args.extras),
        ));
    }

    if !args.no_hooks {
        planned.extend(stamp_githooks(&target)?);
    }

    if !args.no_ci {
        planned.push((
            target.join("README.md"),
            render_readme(&domain.repo, &args.domain),
        ));
    }

    if args.dry_run {
        for (path, content) in &planned {
            println!("would write {} ({} bytes)", path.display(), content.len());
        }
        return Ok(());
    }

    for (path, content) in planned {
        write_file(&path, &content, args.force)?;
        println!("wrote {}", path.display());
    }

    Ok(())
}

fn stamp_githooks(target: &Path) -> Result<Vec<(PathBuf, String)>> {
    let hooks_dir = target.join(".githooks");
    Ok(vec![
        (
            hooks_dir.join("README.md"),
            include_str!("../assets/githooks-README.md").to_string(),
        ),
        (
            hooks_dir.join("pre-commit"),
            include_str!("../assets/githooks-pre-commit").to_string(),
        ),
        (
            hooks_dir.join("pre-push"),
            include_str!("../assets/githooks-pre-push").to_string(),
        ),
    ])
}

fn render_readme(repo_name: &str, domain_id: &str) -> String {
    format!(
        r#"# {repo_name}

Fleet repository bootstrapped with [`hexakit init`](https://github.com/<REDACTED>/HexaKit) (domain: `{domain_id}`).

See [`BOUNDARY.md`](./BOUNDARY.md) for domain ownership and stack policy.

## Git hooks

Hooks live under [`.githooks/`](./.githooks/). Install with:

```bash
git config core.hooksPath .githooks
```

Canonical hook bundles are published from [TestingKit](https://github.com/<REDACTED>/TestingKit). Replace placeholder scripts when wiring a production hook set.

## CI workflows

Do **not** copy org workflows wholesale. Reference reusable workflows and workflow templates from [{GITHUB_ORG_REPO}](https://github.com/{GITHUB_ORG_REPO}):

| Purpose | SSOT path in `{GITHUB_ORG_REPO}` |
| --- | --- |
| Rust CI (reusable) | [`.github/workflows/ci-rust.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/ci-rust.yml) |
| Go CI (reusable) | [`.github/workflows/ci-go.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/ci-go.yml) |
| Python CI (reusable) | [`.github/workflows/ci-python.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/ci-python.yml) |
| TypeScript CI (reusable) | [`.github/workflows/ci-typescript.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/ci-typescript.yml) |
| Generic CI entry | [`.github/workflows/ci.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/ci.yml) |
| Release | [`.github/workflows/release.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/release.yml) |
| Security scan | [`.github/workflows/security.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/security.yml) |
| Publish pipeline | [`.github/workflows/publish.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/.github/workflows/publish.yml) |

### Workflow templates (repo creation / starter)

Use GitHub workflow templates from [`workflow-templates/`](https://github.com/{GITHUB_ORG_REPO}/tree/main/workflow-templates):

- [`workflow-templates/rust-ci.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/rust-ci.yml)
- [`workflow-templates/go-ci.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/go-ci.yml)
- [`workflow-templates/python-ci.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/python-ci.yml)
- [`workflow-templates/typescript-ci.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/typescript-ci.yml)
- [`workflow-templates/security-scan.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/security-scan.yml)
- [`workflow-templates/release-pipeline.yml`](https://github.com/{GITHUB_ORG_REPO}/blob/main/workflow-templates/release-pipeline.yml)

Add thin caller workflows under `.github/workflows/` in this repo that `uses:` the reusable workflows above.
"#
    )
}

fn write_file(path: &Path, content: &str, force: bool) -> Result<()> {
    if path.exists() && !force {
        bail!(
            "{} already exists (use --force to overwrite)",
            path.display()
        );
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("create directory {}", parent.display()))?;
    }
    fs::write(path, content).with_context(|| format!("write {}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use super::*;

    #[test]
    fn init_writes_boundary_hooks_and_readme() {
        let dir = tempdir().unwrap();
        run(InitArgs {
            path: dir.path().to_path_buf(),
            domain: "testing".into(),
            lang: "rust".into(),
            justify: None,
            extras: vec![],
            no_hooks: false,
            no_ci: false,
            dry_run: false,
            force: false,
        })
        .unwrap();

        assert!(dir.path().join("BOUNDARY.md").exists());
        assert!(dir.path().join(".githooks/pre-commit").exists());
        assert!(dir.path().join("README.md").exists());
        let readme = fs::read_to_string(dir.path().join("README.md")).unwrap();
        assert!(readme.contains("<REDACTED>/.github"));
        assert!(readme.contains("workflow-templates/rust-ci.yml"));
    }

    #[test]
    fn init_requires_known_domain() {
        let dir = tempdir().unwrap();
        let err = run(InitArgs {
            path: dir.path().to_path_buf(),
            domain: "unknown".into(),
            lang: "rust".into(),
            justify: None,
            extras: vec![],
            no_hooks: true,
            no_ci: true,
            dry_run: true,
            force: false,
        })
        .unwrap_err();
        assert!(err.to_string().contains("unknown domain"));
    }

    #[test]
    fn init_refuses_overwrite_without_force() {
        let dir = tempdir().unwrap();
        let args = InitArgs {
            path: dir.path().to_path_buf(),
            domain: "testing".into(),
            lang: "rust".into(),
            justify: None,
            extras: vec![],
            no_hooks: true,
            no_ci: true,
            dry_run: false,
            force: false,
        };
        run(args.clone()).unwrap();
        assert!(run(args).is_err());
    }

    #[test]
    fn edge_lang_requires_justify_in_init() {
        let dir = tempfile::tempdir().unwrap();
        let err = run(InitArgs {
            path: dir.path().to_path_buf(),
            domain: "testing".into(),
            lang: "go".into(),
            justify: None,
            extras: vec![],
            no_hooks: true,
            no_ci: true,
            dry_run: true,
            force: false,
        })
        .unwrap_err();
        assert!(err.to_string().contains("--justify"));
    }

    #[test]
    fn extras_writes_phenosdk_manifest() {
        let dir = tempfile::tempdir().unwrap();
        run(InitArgs {
            path: dir.path().to_path_buf(),
            domain: "testing".into(),
            lang: "rust".into(),
            justify: None,
            extras: vec!["pheno-telemetry".into()],
            no_hooks: true,
            no_ci: true,
            dry_run: false,
            force: false,
        })
        .unwrap();
        assert!(dir.path().join("phenosdk.manifest.toml").exists());
    }
}
