//! phenotype-manifest — Attestation manifest generator and validator
use clap::{Parser, Subcommand};
use std::path::PathBuf;

use phenotype_manifest::cli::{GenerateArgs, ShowArgs, VerifyArgs};
use phenotype_manifest::config::AppConfig;
use phenotype_manifest::crypto::{generate_keypair, save_keypair};
use phenotype_manifest::generate::generate_manifest;
use phenotype_manifest::manifest::Manifest;
use phenotype_manifest::pillar::Pillar;
use phenotype_manifest::schema::validate_manifest;
use phenotype_manifest::verify::verify_manifest_cmd as verify_manifest;

#[derive(Parser)]
#[command(name = "phenotype-manifest", version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
    #[arg(short, long, global = true)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    Generate(GenerateArgs),
    Verify(VerifyArgs),
    Show(ShowArgs),
    RunPillar {
        pillar: String,
        #[arg(short, long, default_value = "human")]
        format: String,
    },
    Init {
        #[arg(long)]
        key: Option<PathBuf>,
        #[arg(long)]
        generate_key: bool,
    },
}

fn main() -> anyhow::Result<()> {
    let cfg = AppConfig::load();
    let cli = Cli::parse();

    // Use config log_level unless --verbose is set
    if cli.verbose {
        tracing_subscriber::fmt().with_env_filter("debug").init();
    } else {
        tracing_subscriber::fmt()
            .with_env_filter(&cfg.log_level)
            .init();
    }

    match cli.command {
        Commands::Generate(args) => generate_manifest(args, &cfg),
        Commands::Verify(args) => verify_manifest(args, &cfg),
        Commands::Show(args) => show_manifest(args, &cfg),
        Commands::RunPillar { pillar, format } => run_pillar(&pillar, &format, &cfg),
        Commands::Init { key, generate_key } => init_repo(key, generate_key, &cfg),
    }
}

fn show_manifest(args: ShowArgs, cfg: &AppConfig) -> anyhow::Result<()> {
    let path = args.manifest.unwrap_or(cfg.manifest_path.clone());
    let content = std::fs::read_to_string(&path)?;
    let json: serde_json::Value = serde_json::from_str(&content)?;
    validate_manifest(&json, &cfg.schema_url).map_err(|errs| anyhow::anyhow!(errs.join("; ")))?;
    let manifest: Manifest = serde_json::from_value(json)?;
    if args.json {
        println!("{}", serde_json::to_string_pretty(&manifest)?);
    } else {
        println!("{}", manifest.format_human());
    }
    Ok(())
}

fn run_pillar(pillar: &str, format: &str, cfg: &AppConfig) -> anyhow::Result<()> {
    let pillar_enum = pillar.parse::<Pillar>()?;
    let result = pillar_enum.run_checks_with_config(cfg)?;
    if format == "json" {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else {
        println!(
            "Pillar {}: {} ({} ms)",
            pillar_enum,
            if result.passed { "PASS" } else { "FAIL" },
            result.duration_ms
        );
        for (name, check) in &result.checks {
            println!(
                "  {} {} ({} ms)",
                if check.passed { "[OK]" } else { "[FAIL]" },
                name,
                check.duration_ms
            );
        }
    }
    Ok(())
}

fn init_repo(key: Option<PathBuf>, generate_key: bool, cfg: &AppConfig) -> anyhow::Result<()> {
    use std::os::unix::fs::PermissionsExt;

    // Use provided key path or fall back to config default
    let key_path = key.unwrap_or_else(|| AppConfig::expand_home(&cfg.private_key_path));
    let key_path = AppConfig::expand_home(&key_path);

    if generate_key || !key_path.exists() {
        println!("Generating Ed25519 key at {}", key_path.display());
        let (signing_key, verifying_key) = generate_keypair();
        std::fs::create_dir_all(key_path.parent().unwrap())?;
        let pubkey_path = key_path.with_extension("pub");
        save_keypair(&signing_key, &verifying_key, &key_path, &pubkey_path)?;
        std::fs::set_permissions(&key_path, std::fs::Permissions::from_mode(0o600))?;
        println!(
            "Key pair generated: {} + {}",
            key_path.display(),
            pubkey_path.display()
        );
    }

    // Copy lefthook.yml from configurable template path
    let lefthook_template = AppConfig::expand_home(&cfg.lefthook_template);
    let lefthook_src = std::env::current_dir()?.join(&lefthook_template);
    let lefthook_dst = std::env::current_dir()?.join("lefthook.yml");
    if lefthook_src.exists() {
        std::fs::copy(&lefthook_src, &lefthook_dst)?;
        println!("Copied lefthook.yml from {}", lefthook_src.display());
    } else {
        println!(
            "lefthook template not found at {}; please copy manually",
            lefthook_src.display()
        );
    }

    println!("Next steps:");
    println!("   1. lefthook install");
    println!("   2. Add public key to .github/manifest.pubkey.pem");
    println!("   3. git push (will generate manifest)");
    Ok(())
}
