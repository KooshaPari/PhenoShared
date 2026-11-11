use serde::Serialize;
mod chunking;
mod consent;
mod distill;
mod embeddings;
mod enrichment;
mod github;
mod hackernews;
mod okf;
mod provider_html;
mod rag;
mod reddit;
mod reference_fetch;
mod safe_paths;
mod storage;
mod x;

/// Paths are local machine preferences, not browser data. They are kept in
/// the Tauri app configuration directory so the webview never persists raw
/// filesystem locations in `localStorage`.
mod native_preferences {
    use serde::{Deserialize, Serialize};
    use std::path::{Component, Path};

    const FILE_NAME: &str = "local-preferences.json";

    #[derive(Clone, Debug, Default, Deserialize, PartialEq, Eq, Serialize)]
    #[serde(rename_all = "camelCase")]
    pub struct LocalPreferences {
        pub vault_path: Option<String>,
        pub hackernews_profile: Option<String>,
        pub reddit_profile: Option<String>,
        pub x_profile: Option<String>,
    }

    pub fn load(config_dir: &Path) -> Result<LocalPreferences, String> {
        let path = config_dir.join(FILE_NAME);
        if !path.exists() {
            return Ok(LocalPreferences::default());
        }
        let contents = std::fs::read_to_string(&path).map_err(|error| error.to_string())?;
        let preferences = serde_json::from_str(&contents)
            .map_err(|_| "local preferences could not be read".to_string())?;
        validate(preferences)
    }

    pub fn save(config_dir: &Path, preferences: LocalPreferences) -> Result<(), String> {
        let preferences = validate(preferences)?;
        std::fs::create_dir_all(config_dir).map_err(|error| error.to_string())?;
        let path = config_dir.join(FILE_NAME);
        let temporary_path = config_dir.join(format!(".{FILE_NAME}.tmp"));
        let contents = serde_json::to_vec(&preferences).map_err(|error| error.to_string())?;
        std::fs::write(&temporary_path, contents).map_err(|error| error.to_string())?;
        std::fs::rename(temporary_path, path).map_err(|error| error.to_string())
    }

    pub fn validate(mut preferences: LocalPreferences) -> Result<LocalPreferences, String> {
        preferences.vault_path = validate_path(preferences.vault_path, "vault")?;
        preferences.hackernews_profile =
            validate_path(preferences.hackernews_profile, "Hacker News profile")?;
        preferences.reddit_profile = validate_path(preferences.reddit_profile, "Reddit profile")?;
        preferences.x_profile = validate_path(preferences.x_profile, "X profile")?;
        Ok(preferences)
    }

    fn validate_path(value: Option<String>, label: &str) -> Result<Option<String>, String> {
        let Some(value) = value else {
            return Ok(None);
        };
        let value = value.trim();
        if value.is_empty() {
            return Ok(None);
        }
        if value.chars().any(|character| character.is_control()) {
            return Err(format!("{label} path must not contain control characters"));
        }
        let path = Path::new(value);
        if !path.is_absolute() {
            return Err(format!("{label} path must be absolute"));
        }
        if path
            .components()
            .any(|component| matches!(component, Component::ParentDir))
        {
            return Err(format!(
                "{label} path must not contain `..` traversal segments"
            ));
        }
        Ok(Some(value.to_string()))
    }
}

mod commands {
    include!("commands.rs");

    use super::consent;
    use super::{
        consent::{ConsentGrant, ConsentRegistry},
        distill,
        embeddings::{LocalCrossEncoder, OllamaEmbedder},
        github::GithubClient,
        hackernews, native_preferences, rag, reddit, reference_fetch, safe_paths, storage, x,
        VaultStatus,
    };
    use serde::{Deserialize, Serialize};
    use sha2::{Digest, Sha256};
    use tauri::Manager;

    #[derive(Debug, Serialize)]
    #[serde(rename_all = "camelCase")]
    pub struct ImportSummary {
        pub created: u64,
        pub updated: u64,
        pub unchanged: u64,
        pub failed: u64,
    }

    #[derive(Debug, Deserialize)]
    #[serde(rename_all = "camelCase")]
    pub struct ConsentGrantInput {
        pub vault_path: String,
        pub id: String,
        pub local_profile: String,
        pub provider: String,
        pub data_categories: Vec<String>,
        pub url_scope: String,
        pub expires_at: Option<String>,
        pub version: i64,
        pub granted_at: String,
    }

    #[derive(Debug, Deserialize)]
    #[serde(rename_all = "camelCase")]
    pub struct QueueReferenceFetchInput {
        pub vault_path: String,
        pub source_document_id: String,
        pub target_url: String,
        pub requested_at: String,
    }

    #[derive(Debug, Serialize, PartialEq, Eq)]
    #[serde(rename_all = "camelCase")]
    pub struct QueueReferenceFetchResult {
        pub source_document_id: String,
        pub target_url: String,
        pub queued: bool,
    }

    #[derive(Debug, Deserialize)]
    #[serde(rename_all = "camelCase")]
    pub struct StartReferenceCrawlInput {
        pub vault_path: String,
        pub source_document_id: String,
        pub max_depth: u32,
        pub max_documents: u32,
        pub requested_at: String,
    }

    #[derive(Debug, Serialize, PartialEq, Eq)]
    #[serde(rename_all = "camelCase")]
    pub struct StartReferenceCrawlResult {
        pub run_id: String,
        pub queued: u32,
        pub max_depth: u32,
        pub max_documents: u32,
    }

    #[tauri::command]
    pub fn load_local_preferences(
        app: tauri::AppHandle,
    ) -> Result<native_preferences::LocalPreferences, String> {
        let config_dir = app
            .path()
            .app_config_dir()
            .map_err(|error| error.to_string())?;
        native_preferences::load(&config_dir)
    }

    #[tauri::command]
    pub fn save_local_preferences(
        app: tauri::AppHandle,
        preferences: native_preferences::LocalPreferences,
    ) -> Result<(), String> {
        let config_dir = app
            .path()
            .app_config_dir()
            .map_err(|error| error.to_string())?;
        native_preferences::save(&config_dir, preferences)
    }

    #[tauri::command]
    pub fn queue_reference_fetch(
        input: QueueReferenceFetchInput,
    ) -> Result<QueueReferenceFetchResult, String> {
        let root = std::path::PathBuf::from(&input.vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let source_exists: bool = connection
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM documents WHERE id = ?1)",
                rusqlite::params![input.source_document_id],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        if !source_exists {
            return Err("source document not found".into());
        }
        let target_url = consent::canonical_scope(&input.target_url);
        let link_exists: bool = connection
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM document_links WHERE source_document_id = ?1 AND target_url = ?2)",
                rusqlite::params![input.source_document_id, target_url],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        if !link_exists {
            return Err("reference link not found for source document".into());
        }
        let queued = storage::queue_reference_fetch(
            &connection,
            &input.source_document_id,
            &target_url,
            &input.requested_at,
        )
        .map_err(|error| error.to_string())?;
        Ok(QueueReferenceFetchResult {
            source_document_id: input.source_document_id,
            target_url,
            queued,
        })
    }

    /// Start a user-explicit bounded traversal from one persisted source.
    /// No links are scheduled unless the matching public-web consent is active.
    #[tauri::command]
    pub fn start_reference_crawl(
        input: StartReferenceCrawlInput,
    ) -> Result<StartReferenceCrawlResult, String> {
        let root = std::path::PathBuf::from(&input.vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let run_id = storage::create_reference_crawl_run(
            &connection,
            &input.source_document_id,
            input.max_depth,
            input.max_documents,
            &input.requested_at,
        )
        .map_err(|error| error.to_string())?;
        let targets = {
            let mut statement = connection
                .prepare(
                    "SELECT target_url FROM document_links WHERE source_document_id = ?1 ORDER BY target_url",
                )
                .map_err(|error| error.to_string())?;
            let rows = statement
                .query_map(rusqlite::params![input.source_document_id], |row| {
                    row.get::<_, String>(0)
                })
                .map_err(|error| error.to_string())?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|error| error.to_string())?
        };
        let mut queued = 0;
        for target in targets {
            if queued >= input.max_documents {
                break;
            }
            if storage::queue_reference_fetch_in_run(
                &connection,
                &input.source_document_id,
                &target,
                &run_id,
                Some(&input.source_document_id),
                1,
                &input.requested_at,
            )
            .map_err(|error| error.to_string())?
            {
                queued += 1;
            }
        }
        Ok(StartReferenceCrawlResult {
            run_id,
            queued,
            max_depth: input.max_depth,
            max_documents: input.max_documents,
        })
    }

    #[tauri::command]
    pub fn grant_consent(input: ConsentGrantInput) -> Result<(), String> {
        let root = std::path::PathBuf::from(&input.vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        ConsentRegistry::new(&connection)
            .grant(ConsentGrant {
                id: input.id,
                local_profile: input.local_profile,
                provider: input.provider,
                purpose: consent::REFERENCE_FETCH_PURPOSE.into(),
                data_categories: input.data_categories,
                url_scope: input.url_scope,
                expires_at: input.expires_at,
                version: input.version,
                granted_at: input.granted_at,
            })
            .map_err(|error| error.to_string())
    }

    #[tauri::command]
    pub fn revoke_consent(
        vault_path: String,
        id: String,
        revoked_at: String,
    ) -> Result<bool, String> {
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        ConsentRegistry::new(&connection)
            .revoke(&id, &revoked_at)
            .map_err(|error| error.to_string())
    }

    /// Build the Bun command used for browser capture.
    ///
    /// GUI-launched macOS applications do not reliably inherit the shell PATH,
    /// so prefer the user-configured path and the two standard Homebrew/Bun
    /// locations before falling back to PATH lookup. This keeps the packaged
    /// app on the repository's Bun runtime contract without requiring a shell
    /// or a globally installed Node/npm toolchain.
    fn bun_command() -> tokio::process::Command {
        let mut candidates = Vec::new();
        if let Some(path) = std::env::var_os("RESEARCHLEDGER_BUN_PATH") {
            candidates.push(std::path::PathBuf::from(path));
        }
        candidates.push(std::path::PathBuf::from("/opt/homebrew/bin/bun"));
        candidates.push(std::path::PathBuf::from("/usr/local/bin/bun"));
        if let Some(home) = std::env::var_os("HOME") {
            candidates.push(std::path::PathBuf::from(home).join(".bun/bin/bun"));
        }
        candidates
            .into_iter()
            .find(|candidate| candidate.is_file())
            .map(tokio::process::Command::new)
            .unwrap_or_else(|| tokio::process::Command::new("bun"))
    }

    fn gh_command() -> tokio::process::Command {
        let mut candidates = Vec::new();
        if let Some(path) = std::env::var_os("RESEARCHLEDGER_GH_PATH") {
            candidates.push(std::path::PathBuf::from(path));
        }
        candidates.push(std::path::PathBuf::from("/opt/homebrew/bin/gh"));
        candidates.push(std::path::PathBuf::from("/usr/local/bin/gh"));
        if let Some(home) = std::env::var_os("HOME") {
            candidates.push(std::path::PathBuf::from(home).join(".local/bin/gh"));
        }
        candidates
            .into_iter()
            .find(|candidate| candidate.is_file())
            .map(tokio::process::Command::new)
            .unwrap_or_else(|| tokio::process::Command::new("gh"))
    }

    pub(crate) fn parse_gh_token_output(success: bool, stdout: &[u8]) -> Result<String, String> {
        if !success {
            return Err("GitHub CLI is not authenticated. Run `gh auth login`, then retry.".into());
        }
        let token = String::from_utf8_lossy(stdout).trim().to_string();
        if token.is_empty() {
            return Err("GitHub CLI returned no token. Run `gh auth login`, then retry.".into());
        }
        Ok(token)
    }

    fn configure_playwright_command(app: &tauri::AppHandle, command: &mut tokio::process::Command) {
        if let Ok(resource_dir) = app.path().resource_dir() {
            command.current_dir(&resource_dir);
            let candidates = [
                resource_dir.join("node_modules/playwright/index.mjs"),
                resource_dir.join("node_modules/playwright"),
                resource_dir.join("node_modules/playwright-core"),
            ];
            for candidate in candidates {
                if candidate.exists() {
                    command.env("RESEARCHLEDGER_PLAYWRIGHT_MODULE", candidate);
                    break;
                }
            }
        }
    }

    fn external_capture_path(provider: &str) -> Result<std::path::PathBuf, String> {
        let root = if let Some(configured) = std::env::var_os("RESEARCHLEDGER_CAPTURE_ROOT") {
            let path = std::path::PathBuf::from(configured);
            if !path.is_absolute() {
                return Err("RESEARCHLEDGER_CAPTURE_ROOT must be an absolute path".into());
            }
            path
        } else {
            let home = std::env::var_os("HOME")
                .map(std::path::PathBuf::from)
                .ok_or_else(|| {
                    "HOME is unavailable; configure RESEARCHLEDGER_CAPTURE_ROOT".to_string()
                })?;
            home.join(".phenotype")
                .join("researchledger")
                .join("captures")
        };
        std::fs::create_dir_all(&root).map_err(|error| error.to_string())?;
        Ok(root.join(format!("{provider}-capture.json")))
    }

    #[tauri::command]
    pub fn get_vault_status(vault_path: Option<String>) -> Result<VaultStatus, String> {
        let Some(path) = vault_path.filter(|value| !value.trim().is_empty()) else {
            return Ok(VaultStatus {
                selected: false,
                path: None,
                document_count: 0,
            });
        };
        let root = std::path::PathBuf::from(&path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let document_count =
            storage::document_count(&connection).map_err(|error| error.to_string())?;
        Ok(VaultStatus {
            selected: true,
            path: Some(path),
            document_count,
        })
    }

    async fn import_github_with_credential(
        vault_path: String,
        credential: String,
    ) -> Result<ImportSummary, String> {
        if credential.trim().is_empty() {
            return Err("GitHub authentication is required".into());
        }
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let client = GithubClient::new(credential).map_err(|error| error.to_string())?;
        let repositories = client
            .list_starred()
            .await
            .map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for repository in repositories {
            let readme = match client
                .read_readme(&repository.owner.login, &repository.name)
                .await
            {
                Ok(value) => value.unwrap_or_else(|| "README unavailable.\n".into()),
                Err(_) => {
                    summary.failed += 1;
                    continue;
                }
            };
            let description = repository
                .description
                .as_deref()
                .unwrap_or("No description provided.")
                .replace('"', "'");
            let content = format!("---\ntype: GitHub Repository\nid: github:{}\ntitle: {}\ndescription: \"{}\"\nresource: {}\ntags: [github, repository]\ntimestamp: {}\nsource_kind: github\nsource_uri: {}\n---\n\n# {}\n\n{}\n\n## Repository\n\n{}\n\n# Citations\n\n[1] [{}]({})\n",
                repository.full_name, repository.name, description, repository.html_url, chrono::Utc::now().to_rfc3339(), repository.html_url, repository.name,
                description, readme, repository.name, repository.html_url);
            let document = storage::SourceDocument {
                id: format!("github:{}", repository.full_name),
                relative_path: format!(
                    "sources/github/{}--{}.md",
                    repository.owner.login, repository.name
                ),
                title: repository.name,
                source_kind: "github".into(),
                source_uri: Some(repository.html_url),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn import_github_from_gh(vault_path: String) -> Result<ImportSummary, String> {
        let output = gh_command()
            .args(["auth", "token", "--hostname", "github.com"])
            .output()
            .await
            .map_err(|_| {
                "GitHub CLI is unavailable. Install `gh` or configure RESEARCHLEDGER_GH_PATH."
                    .to_string()
            })?;
        let credential = parse_gh_token_output(output.status.success(), &output.stdout)?;
        import_github_with_credential(vault_path, credential).await
    }

    #[tauri::command]
    pub fn import_linkedin_manual(
        vault_path: String,
        permalink: String,
        content: String,
    ) -> Result<ImportSummary, String> {
        let permalink = permalink.trim();
        let content = content.trim();
        if !permalink.starts_with("https://www.linkedin.com/") {
            return Err("LinkedIn permalink must be an https://www.linkedin.com/ URL".into());
        }
        if content.is_empty() {
            return Err("LinkedIn content is required".into());
        }
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let id = format!("{:x}", Sha256::digest(permalink.as_bytes()));
        let document = storage::SourceDocument {
            id: format!("linkedin:{id}"),
            relative_path: format!("sources/linkedin/{id}.md"),
            title: "LinkedIn manual import".into(),
            source_kind: "linkedin".into(),
            source_uri: Some(permalink.to_string()),
            content: format!("---\ntype: LinkedIn Post\nid: linkedin:{id}\ntitle: LinkedIn manual import\ndescription: User-supplied LinkedIn permalink and content\nresource: {permalink}\ntags: [linkedin, manual]\ntimestamp: {}\nsource_kind: linkedin\nsource_uri: {permalink}\n---\n\n{content}\n\n# Citations\n\n[1] [LinkedIn post]({permalink})\n", chrono::Utc::now().to_rfc3339()),
            captured_at: chrono::Utc::now().to_rfc3339(),
        };
        match storage::upsert_document(&mut connection, &root, &document)
            .map_err(|error| error.to_string())?
        {
            storage::UpsertResult::Created => Ok(ImportSummary {
                created: 1,
                updated: 0,
                unchanged: 0,
                failed: 0,
            }),
            storage::UpsertResult::Updated => Ok(ImportSummary {
                created: 0,
                updated: 1,
                unchanged: 0,
                failed: 0,
            }),
            storage::UpsertResult::Unchanged => Ok(ImportSummary {
                created: 0,
                updated: 0,
                unchanged: 1,
                failed: 0,
            }),
        }
    }

    #[tauri::command]
    pub fn import_hackernews_html(
        vault_path: String,
        html_path: String,
    ) -> Result<ImportSummary, String> {
        let html = std::fs::read_to_string(&html_path).map_err(|error| error.to_string())?;
        let posts = hackernews::parse_saved_html(&html);
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let id = post.id.clone();
            let content = format!(
                "---\ntype: Hacker News Story\nid: hackernews:{id}\ntitle: {title}\ndescription: Captured HN saved story\nresource: {url}\ntags: [hackernews, saved]\ntimestamp: {timestamp}\nsource_kind: hackernews\nsource_uri: {url}\nauthor: {author}\n---\n\n{text}\n\n# Citations\n\n[1] [HN item {id}]({url})\n",
                id = id,
                title = post.title,
                url = post.url,
                timestamp = chrono::Utc::now().to_rfc3339(),
                author = post.author,
                text = post.text,
            );
            let document = storage::SourceDocument {
                id: format!("hackernews:{id}"),
                relative_path: format!("sources/hackernews/{id}.md"),
                title: post.title.clone(),
                source_kind: "hackernews".into(),
                source_uri: Some(post.url.clone()),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub fn import_hackernews_capture(
        vault_path: String,
        capture_path: String,
    ) -> Result<ImportSummary, String> {
        let json = std::fs::read_to_string(&capture_path).map_err(|error| error.to_string())?;
        let posts = hackernews::parse_capture_json(&json).map_err(|error| error.to_string())?;
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let id = post.id.clone();
            let document = storage::SourceDocument {
                id: format!("hackernews:{id}"),
                relative_path: format!("sources/hackernews/{id}.md"),
                title: post.title.clone(),
                source_kind: "hackernews".into(),
                source_uri: Some(post.url.clone()),
                content: format!(
                    "---\ntype: Hacker News Story\nid: hackernews:{id}\ntitle: {title}\ndescription: Captured HN saved story\nresource: {url}\ntags: [hackernews, saved]\ntimestamp: {timestamp}\nsource_kind: hackernews\nsource_uri: {url}\nauthor: {author}\n---\n\n{text}\n\n# Citations\n\n[1] [HN item {id}]({url})\n",
                    id = id,
                    title = post.title,
                    url = post.url,
                    timestamp = chrono::Utc::now().to_rfc3339(),
                    author = post.author,
                    text = post.text,
                ),
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn capture_hackernews_browser(
        app: tauri::AppHandle,
        vault_path: String,
        activity_url: Option<String>,
        profile_path: Option<String>,
    ) -> Result<ImportSummary, String> {
        if let Some(url) = activity_url
            .as_deref()
            .filter(|value| !value.trim().is_empty())
        {
            safe_paths::ensure_safe_provider_url(url, &["news.ycombinator.com"])
                .map_err(|error| error.to_string())?;
        }
        let output = external_capture_path("hackernews")?;
        let resource_script = app
            .path()
            .resource_dir()
            .map_err(|error| error.to_string())?
            .join("scripts/hackernews_capture.mjs");
        let script = if resource_script.exists() {
            resource_script
        } else {
            std::env::current_dir()
                .map_err(|error| error.to_string())?
                .join("scripts/hackernews_capture.mjs")
        };
        let mut command = bun_command();
        command.arg(script).arg("--output").arg(&output);
        configure_playwright_command(&app, &mut command);
        if let Some(profile) = profile_path.filter(|value| !value.trim().is_empty()) {
            let safe_profile = safe_paths::ensure_safe_command_arg(&profile, "profile")
                .map_err(|error| error.to_string())?;
            command.arg("--profile").arg(safe_profile);
        }
        if let Some(url) = activity_url.filter(|value| !value.trim().is_empty()) {
            command.arg("--url").arg(url);
        }
        let result = command.output().await.map_err(|error| error.to_string())?;
        if !result.status.success() {
            return Err(String::from_utf8_lossy(&result.stderr).trim().to_string());
        }
        import_hackernews_capture(vault_path, output.to_string_lossy().into_owned())
    }

    /// Slugify a captured URL into a filesystem-safe document id fragment.
    /// Strips the `https?://` scheme, then replaces `/`, `?`, and any
    /// remaining `:` characters with `-`. This guarantees the id never
    /// contains a path separator (which would otherwise let a malicious
    /// capture file escape the vault's per-source folder).
    fn slug_from_url(url: &str) -> String {
        let mut slug = url
            .trim_start_matches("https://")
            .trim_start_matches("http://")
            .replace(['/', '?', ':', '#'], "-");
        while slug.contains("--") {
            slug = slug.replace("--", "-");
        }
        slug = slug.trim_matches('-').to_string();
        if slug.is_empty() {
            return "post".into();
        }
        slug
    }

    fn render_reddit_markdown(post: &reddit::RedditSavedPost) -> String {
        let timestamp = chrono::Utc::now().to_rfc3339();
        let subreddit = post.subreddit.clone().unwrap_or_default();
        format!(
            "---\ntype: Reddit Post\nid: reddit:{slug}\ntitle: {title}\ndescription: Captured Reddit saved post\nresource: {url}\ntags: [reddit, saved]\ntimestamp: {timestamp}\nsource_kind: reddit\nsource_uri: {url}\nsubreddit: {subreddit}\n---\n\n{text}\n\n# Citations\n\n[1] [Reddit post]({url})\n",
            slug = slug_from_url(&post.url),
            title = post.title,
            url = post.url,
            timestamp = timestamp,
            text = post.text,
            subreddit = subreddit,
        )
    }

    fn render_x_markdown(post: &x::XSavedPost) -> String {
        let timestamp = chrono::Utc::now().to_rfc3339();
        format!(
            "---\ntype: X Bookmark\nid: x:{slug}\ntitle: X bookmark by {author}\ndescription: Captured X bookmark\nresource: {url}\ntags: [x, bookmark]\ntimestamp: {timestamp}\nsource_kind: x\nsource_uri: {url}\nauthor: {author}\n---\n\n{text}\n\n# Citations\n\n[1] [X post]({url})\n",
            slug = slug_from_url(&post.url),
            url = post.url,
            timestamp = timestamp,
            text = post.text,
            author = post.author,
        )
    }

    #[tauri::command]
    pub fn import_reddit_html(
        vault_path: String,
        html_path: String,
    ) -> Result<ImportSummary, String> {
        let html = std::fs::read_to_string(&html_path).map_err(|error| error.to_string())?;
        let posts = reddit::parse_saved_html(&html);
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let slug = slug_from_url(&post.url);
            let content = render_reddit_markdown(&post);
            let document = storage::SourceDocument {
                id: format!("reddit:{slug}"),
                relative_path: format!("sources/reddit/{slug}.md"),
                title: post.title.clone(),
                source_kind: "reddit".into(),
                source_uri: Some(post.url.clone()),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub fn import_reddit_capture(
        vault_path: String,
        capture_path: String,
    ) -> Result<ImportSummary, String> {
        let json = std::fs::read_to_string(&capture_path).map_err(|error| error.to_string())?;
        let posts = reddit::parse_capture_json(&json).map_err(|error| error.to_string())?;
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let slug = slug_from_url(&post.url);
            let content = render_reddit_markdown(&post);
            let document = storage::SourceDocument {
                id: format!("reddit:{slug}"),
                relative_path: format!("sources/reddit/{slug}.md"),
                title: post.title.clone(),
                source_kind: "reddit".into(),
                source_uri: Some(post.url.clone()),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn capture_reddit_browser(
        app: tauri::AppHandle,
        vault_path: String,
        activity_url: Option<String>,
        profile_path: Option<String>,
    ) -> Result<ImportSummary, String> {
        // Validate the URL is on the Reddit allow-list before shelling out so a
        // crafted activity_url can't redirect the user's authenticated profile
        // to a different host.
        if let Some(url) = activity_url
            .as_deref()
            .filter(|value| !value.trim().is_empty())
        {
            safe_paths::ensure_safe_provider_url(
                url,
                &["reddit.com", "www.reddit.com", "old.reddit.com"],
            )
            .map_err(|error| error.to_string())?;
        }
        let output = external_capture_path("reddit")?;
        let resource_script = app
            .path()
            .resource_dir()
            .map_err(|error| error.to_string())?
            .join("scripts/reddit_capture.mjs");
        let script = if resource_script.exists() {
            resource_script
        } else {
            std::env::current_dir()
                .map_err(|error| error.to_string())?
                .join("scripts/reddit_capture.mjs")
        };
        let mut command = bun_command();
        command.arg(script).arg("--output").arg(&output);
        configure_playwright_command(&app, &mut command);
        if let Some(profile) = profile_path
            .as_deref()
            .filter(|value| !value.trim().is_empty())
        {
            let safe_profile = safe_paths::ensure_safe_command_arg(profile, "profile")
                .map_err(|error| error.to_string())?;
            command.arg("--profile").arg(safe_profile);
        }
        if let Some(url) = activity_url.filter(|value| !value.trim().is_empty()) {
            command.arg("--url").arg(url);
        }
        let result = command.output().await.map_err(|error| error.to_string())?;
        if !result.status.success() {
            return Err(String::from_utf8_lossy(&result.stderr).trim().to_string());
        }
        import_reddit_capture(vault_path, output.to_string_lossy().into_owned())
    }

    #[tauri::command]
    pub fn import_x_html(vault_path: String, html_path: String) -> Result<ImportSummary, String> {
        let html = std::fs::read_to_string(&html_path).map_err(|error| error.to_string())?;
        let posts = x::parse_bookmarks_html(&html);
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let slug = slug_from_url(&post.url);
            let content = render_x_markdown(&post);
            let document = storage::SourceDocument {
                id: format!("x:{slug}"),
                relative_path: format!("sources/x/{slug}.md"),
                title: format!("X bookmark by {}", post.author),
                source_kind: "x".into(),
                source_uri: Some(post.url.clone()),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub fn import_x_capture(
        vault_path: String,
        capture_path: String,
    ) -> Result<ImportSummary, String> {
        let json = std::fs::read_to_string(&capture_path).map_err(|error| error.to_string())?;
        let posts = x::parse_capture_json(&json).map_err(|error| error.to_string())?;
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for post in posts {
            let slug = slug_from_url(&post.url);
            let content = render_x_markdown(&post);
            let document = storage::SourceDocument {
                id: format!("x:{slug}"),
                relative_path: format!("sources/x/{slug}.md"),
                title: format!("X bookmark by {}", post.author),
                source_kind: "x".into(),
                source_uri: Some(post.url.clone()),
                content,
                captured_at: chrono::Utc::now().to_rfc3339(),
            };
            match storage::upsert_document(&mut connection, &root, &document)
                .map_err(|error| error.to_string())?
            {
                storage::UpsertResult::Created => summary.created += 1,
                storage::UpsertResult::Updated => summary.updated += 1,
                storage::UpsertResult::Unchanged => summary.unchanged += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn capture_x_browser(
        app: tauri::AppHandle,
        vault_path: String,
        activity_url: Option<String>,
        profile_path: Option<String>,
    ) -> Result<ImportSummary, String> {
        if let Some(url) = activity_url
            .as_deref()
            .filter(|value| !value.trim().is_empty())
        {
            safe_paths::ensure_safe_provider_url(url, &["x.com", "twitter.com"])
                .map_err(|error| error.to_string())?;
        }
        let output = external_capture_path("x")?;
        let resource_script = app
            .path()
            .resource_dir()
            .map_err(|error| error.to_string())?
            .join("scripts/x_capture.mjs");
        let script = if resource_script.exists() {
            resource_script
        } else {
            std::env::current_dir()
                .map_err(|error| error.to_string())?
                .join("scripts/x_capture.mjs")
        };
        let mut command = bun_command();
        command.arg(script).arg("--output").arg(&output);
        configure_playwright_command(&app, &mut command);
        if let Some(profile) = profile_path
            .as_deref()
            .filter(|value| !value.trim().is_empty())
        {
            let safe_profile = safe_paths::ensure_safe_command_arg(profile, "profile")
                .map_err(|error| error.to_string())?;
            command.arg("--profile").arg(safe_profile);
        }
        if let Some(url) = activity_url.filter(|value| !value.trim().is_empty()) {
            command.arg("--url").arg(url);
        }
        let result = command.output().await.map_err(|error| error.to_string())?;
        if !result.status.success() {
            return Err(String::from_utf8_lossy(&result.stderr).trim().to_string());
        }
        import_x_capture(vault_path, output.to_string_lossy().into_owned())
    }

    #[tauri::command]
    pub fn search_documents(
        vault_path: String,
        query: String,
        limit: Option<u32>,
    ) -> Result<Vec<storage::SearchResult>, String> {
        let paths = storage::initialize(std::path::Path::new(&vault_path))
            .map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        storage::search(&connection, &query, limit.unwrap_or(20).min(100))
            .map_err(|error| error.to_string())
    }

    #[tauri::command]
    pub fn export_obsidian(vault_path: String, destination: String) -> Result<u64, String> {
        storage::export_markdown(
            std::path::Path::new(&vault_path),
            std::path::Path::new(&destination),
        )
        .map_err(|error| error.to_string())
    }

    #[tauri::command]
    pub async fn retrieve_context(
        vault_path: String,
        query: String,
        limit: Option<u32>,
    ) -> Result<rag::RetrievalContext, String> {
        let paths = storage::initialize(std::path::Path::new(&vault_path))
            .map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let limit = limit.unwrap_or(8).min(50);
        let lexical =
            storage::search(&connection, &query, limit).map_err(|error| error.to_string())?;
        let vector_hits = match OllamaEmbedder::new("embeddinggemma")
            .embed_batch(std::slice::from_ref(&query))
            .await
        {
            Ok(vectors) => vectors
                .into_iter()
                .next()
                .map(|vector| {
                    storage::search_vectors(&connection, &vector, "embeddinggemma", "v1", limit)
                        .unwrap_or_default()
                })
                .unwrap_or_default(),
            Err(_) => Vec::new(),
        };
        let vector_hits = vector_hits
            .into_iter()
            .map(|(result, score)| rag::VectorHit {
                document_id: result.document_id.clone(),
                score,
                result: Some(result),
            })
            .collect();
        let fused = rag::fuse_ranked(lexical, vector_hits, limit as usize);
        let reranked = match LocalCrossEncoder::from_environment() {
            Ok(Some(reranker)) => {
                let documents = fused
                    .iter()
                    .map(|result| format!("{}\n{}", result.title, result.snippet))
                    .collect::<Vec<_>>();
                reranker
                    .rerank(&query, &documents)
                    .await
                    .map(|scores| rag::rerank_with_cross_encoder(fused.clone(), scores))
                    .unwrap_or_else(|_| rag::rerank(&query, fused))
            }
            Ok(None) | Err(_) => rag::rerank(&query, fused),
        };
        Ok(rag::build_context(&query, reranked))
    }

    #[tauri::command]
    pub fn distill_document(
        vault_path: String,
        document_id: String,
    ) -> Result<ImportSummary, String> {
        let root = std::path::PathBuf::from(vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let source = storage::load_document(&connection, &root, &document_id)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "source document not found".to_string())?;
        let distilled = storage::SourceDocument {
            id: format!("distillation:{document_id}"),
            relative_path: format!(
                "knowledge/{}--distilled.md",
                document_id.replace([':', '/'], "--")
            ),
            title: format!("{} — deterministic distillation", source.title),
            source_kind: "distillation".into(),
            source_uri: source.source_uri.clone(),
            content: distill::render_deterministic(&source),
            captured_at: chrono::Utc::now().to_rfc3339(),
        };
        let result = storage::upsert_document(&mut connection, &root, &distilled)
            .map_err(|error| error.to_string())?;
        connection.execute(
            "UPDATE enrichment_jobs SET status='completed', updated_at=?2, error=NULL WHERE document_id=?1",
            rusqlite::params![document_id, distilled.captured_at],
        ).map_err(|error| error.to_string())?;
        Ok(ImportSummary {
            created: u64::from(result == storage::UpsertResult::Created),
            updated: u64::from(result == storage::UpsertResult::Updated),
            unchanged: u64::from(result == storage::UpsertResult::Unchanged),
            failed: 0,
        })
    }

    #[tauri::command]
    pub fn process_pending_enrichment(
        vault_path: String,
        limit: Option<u32>,
    ) -> Result<ImportSummary, String> {
        let root = std::path::PathBuf::from(&vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let ids = storage::pending_enrichment_ids(&connection, limit.unwrap_or(25).min(100))
            .map_err(|error| error.to_string())?;
        drop(connection);
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for id in ids {
            match distill_document(vault_path.clone(), id) {
                Ok(result) => {
                    summary.created += result.created;
                    summary.updated += result.updated;
                    summary.unchanged += result.unchanged;
                }
                Err(_) => summary.failed += 1,
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn fetch_pending_references(
        vault_path: String,
        limit: Option<u32>,
    ) -> Result<ImportSummary, String> {
        let root = std::path::PathBuf::from(&vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let connection = storage::open(&paths).map_err(|error| error.to_string())?;
        let jobs = storage::pending_reference_jobs_with_metadata(
            &connection,
            limit.unwrap_or(10).min(25),
            &chrono::Utc::now().to_rfc3339(),
        )
        .map_err(|error| error.to_string())?;
        drop(connection);
        let mut domain_budget = reference_fetch::DomainConcurrency::new(2);
        let mut summary = ImportSummary {
            created: 0,
            updated: 0,
            unchanged: 0,
            failed: 0,
        };
        for metadata in jobs {
            let job = metadata.job.clone();
            if !domain_budget.try_acquire(&job.target_url) {
                continue;
            }
            let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
            let connection = storage::open(&paths).map_err(|error| error.to_string())?;
            let claimed = storage::claim_reference_fetch_if_consented(
                &connection,
                &job,
                &chrono::Utc::now().to_rfc3339(),
            )
            .map_err(|error| error.to_string())?;
            drop(connection);
            if !claimed {
                domain_budget.release(&job.target_url);
                continue;
            }

            let fetched_result = reference_fetch::fetch_with_retry(&job.target_url).await;
            domain_budget.release(&job.target_url);
            match fetched_result {
                Ok(fetched) => {
                    let result = reference_fetch::write_artifact(&root, &fetched);
                    match result {
                        Ok(_) => {
                            let reference_document = storage::SourceDocument {
                                id: format!("reference:{}", fetched.content_hash),
                                relative_path: format!(
                                    "sources/references/{}.md",
                                    fetched.content_hash
                                ),
                                title: format!("Fetched reference: {}", job.target_url),
                                source_kind: "reference".into(),
                                source_uri: Some(job.target_url.clone()),
                                content: reference_fetch::render_markdown(
                                    &job.target_url,
                                    &fetched,
                                ),
                                captured_at: chrono::Utc::now().to_rfc3339(),
                            };
                            let paths =
                                storage::initialize(&root).map_err(|error| error.to_string())?;
                            let mut connection =
                                storage::open(&paths).map_err(|error| error.to_string())?;
                            let upsert_result = match storage::upsert_document(
                                &mut connection,
                                &root,
                                &reference_document,
                            ) {
                                Ok(result) => result,
                                Err(error) => {
                                    storage::record_reference_fetch(
                                        &connection,
                                        &job,
                                        &storage::ReferenceFetchUpdate {
                                            status: "failed",
                                            artifact_path: None,
                                            content_type: None,
                                            http_status: None,
                                            byte_count: None,
                                            content_hash: None,
                                            fetched_at: Some(&chrono::Utc::now().to_rfc3339()),
                                            error: Some(&error.to_string()),
                                        },
                                    )
                                    .map_err(|error| error.to_string())?;
                                    summary.failed += 1;
                                    continue;
                                }
                            };
                            match upsert_result {
                                storage::UpsertResult::Created => summary.created += 1,
                                storage::UpsertResult::Updated => summary.updated += 1,
                                storage::UpsertResult::Unchanged => summary.unchanged += 1,
                            }
                            storage::record_reference_fetch(
                                &connection,
                                &job,
                                &storage::ReferenceFetchUpdate {
                                    status: "done",
                                    artifact_path: Some(&fetched.artifact_path),
                                    content_type: Some(&fetched.content_type),
                                    http_status: Some(fetched.http_status),
                                    byte_count: Some(fetched.byte_count),
                                    content_hash: Some(&fetched.content_hash),
                                    fetched_at: Some(&chrono::Utc::now().to_rfc3339()),
                                    error: None,
                                },
                            )
                            .map_err(|error| error.to_string())?;
                            if let Some(run_id) = metadata.run_id.as_deref() {
                                storage::enqueue_reference_children(
                                    &connection,
                                    run_id,
                                    &reference_document.id,
                                    metadata.depth,
                                    &chrono::Utc::now().to_rfc3339(),
                                )
                                .map_err(|error| error.to_string())?;
                            }
                        }
                        Err(error) => {
                            let paths =
                                storage::initialize(&root).map_err(|error| error.to_string())?;
                            let connection =
                                storage::open(&paths).map_err(|error| error.to_string())?;
                            storage::record_reference_fetch(
                                &connection,
                                &job,
                                &storage::ReferenceFetchUpdate {
                                    status: "failed",
                                    artifact_path: None,
                                    content_type: None,
                                    http_status: None,
                                    byte_count: None,
                                    content_hash: None,
                                    fetched_at: Some(&chrono::Utc::now().to_rfc3339()),
                                    error: Some(&error.to_string()),
                                },
                            )
                            .map_err(|error| error.to_string())?;
                            summary.failed += 1;
                        }
                    }
                }
                Err(error) => {
                    let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
                    let connection = storage::open(&paths).map_err(|error| error.to_string())?;
                    storage::record_reference_fetch(
                        &connection,
                        &job,
                        &storage::ReferenceFetchUpdate {
                            status: "failed",
                            artifact_path: None,
                            content_type: None,
                            http_status: None,
                            byte_count: None,
                            content_hash: None,
                            fetched_at: Some(&chrono::Utc::now().to_rfc3339()),
                            error: Some(&error.to_string()),
                        },
                    )
                    .map_err(|error| error.to_string())?;
                    summary.failed += 1;
                }
            }
        }
        Ok(summary)
    }

    #[tauri::command]
    pub async fn embed_document(
        vault_path: String,
        document_id: String,
        model: Option<String>,
    ) -> Result<usize, String> {
        let root = std::path::PathBuf::from(&vault_path);
        let paths = storage::initialize(&root).map_err(|error| error.to_string())?;
        let mut connection = storage::open(&paths).map_err(|error| error.to_string())?;
        storage::load_document(&connection, &root, &document_id)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| "source document not found".to_string())?;
        let model = model.unwrap_or_else(|| "embeddinggemma".into());
        let chunks = {
            let mut statement = connection
                .prepare("SELECT id, text FROM chunks WHERE document_id=?1 ORDER BY ordinal")
                .map_err(|error| error.to_string())?;
            let rows = statement
                .query_map(rusqlite::params![document_id], |row| {
                    Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
                })
                .map_err(|error| error.to_string())?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|error| error.to_string())?
        };
        if chunks.is_empty() {
            return Err("source document has no chunks".into());
        }
        let texts = chunks
            .iter()
            .map(|(_, text)| text.clone())
            .collect::<Vec<_>>();
        let vectors = OllamaEmbedder::new(model.clone())
            .embed_batch(&texts)
            .await?;
        if vectors.len() != chunks.len() {
            return Err("embedding service returned an incomplete batch".into());
        }
        let transaction = connection
            .transaction()
            .map_err(|error| error.to_string())?;
        for ((chunk_id, text), vector) in chunks.iter().zip(vectors.iter()) {
            let input_hash = format!("{:x}", Sha256::digest(text.as_bytes()));
            transaction
                .execute(
                    "INSERT INTO chunk_embeddings (chunk_id, model, embedding_version, input_hash, dimensions, vector_json, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7) ON CONFLICT(chunk_id) DO UPDATE SET model=excluded.model, embedding_version=excluded.embedding_version, input_hash=excluded.input_hash, dimensions=excluded.dimensions, vector_json=excluded.vector_json, created_at=excluded.created_at",
                    rusqlite::params![
                        chunk_id,
                        model,
                        "v1",
                        input_hash,
                        vector.len(),
                        serde_json::to_string(vector).map_err(|error| error.to_string())?,
                        chrono::Utc::now().to_rfc3339()
                    ],
                )
                .map_err(|error| error.to_string())?;
        }
        transaction.commit().map_err(|error| error.to_string())?;
        Ok(vectors.len())
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultStatus {
    pub selected: bool,
    pub path: Option<String>,
    pub document_count: u64,
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            commands::load_local_preferences,
            commands::save_local_preferences,
            commands::get_vault_status,
            commands::grant_consent,
            commands::revoke_consent,
            commands::queue_reference_fetch,
            commands::start_reference_crawl,
            commands::import_github_from_gh,
            commands::import_linkedin_manual,
            commands::import_hackernews_html,
            commands::import_hackernews_capture,
            commands::capture_hackernews_browser,
            commands::import_reddit_html,
            commands::import_reddit_capture,
            commands::capture_reddit_browser,
            commands::import_x_html,
            commands::import_x_capture,
            commands::capture_x_browser,
            commands::search_documents,
            commands::list_document_summaries,
            commands::list_collections,
            commands::list_document_links,
            commands::list_document_claims,
            commands::export_obsidian,
            commands::retrieve_context,
            commands::distill_document,
            commands::process_pending_enrichment,
            commands::fetch_pending_references,
            commands::embed_document
        ])
        .run(tauri::generate_context!())
        .expect("error while running ResearchLedger");
}

#[cfg(test)]
mod tests {
    use super::commands;
    use super::consent::{ConsentGrant, ConsentRegistry};
    use super::native_preferences::{self, LocalPreferences};
    use super::storage::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    static TEMP_ROOT_COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root() -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "researchledger-{}-{}",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
            TEMP_ROOT_COUNTER.fetch_add(1, Ordering::Relaxed),
        ))
    }

    #[test]
    fn temp_roots_are_unique_under_parallel_creation() {
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(64));
        let handles = (0..64)
            .map(|_| {
                let barrier = std::sync::Arc::clone(&barrier);
                std::thread::spawn(move || {
                    barrier.wait();
                    temp_root()
                })
            })
            .collect::<Vec<_>>();
        let roots = handles
            .into_iter()
            .map(|handle| handle.join().unwrap())
            .collect::<Vec<_>>();
        let unique = roots.iter().collect::<std::collections::BTreeSet<_>>();

        assert_eq!(unique.len(), roots.len());
    }

    #[test]
    fn initializes_and_upserts_idempotently() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        let document = SourceDocument {
            id: "github:octo/hello".into(),
            relative_path: "sources/github/octo--hello.md".into(),
            title: "hello".into(),
            source_kind: "github".into(),
            source_uri: Some("https://github.com/octo/hello".into()),
            content: "---\ntype: GitHub Repository\n---\n\n# hello\n".into(),
            captured_at: "2026-07-20T00:00:00Z".into(),
        };
        assert_eq!(
            upsert_document(&mut db, &root, &document).unwrap(),
            UpsertResult::Created
        );
        let created_quote: String = db
            .query_row(
                "SELECT quote FROM provenance WHERE document_id = ?1",
                [&document.id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(created_quote, "hello");
        assert_eq!(
            upsert_document(&mut db, &root, &document).unwrap(),
            UpsertResult::Unchanged
        );
        assert_eq!(document_count(&db).unwrap(), 1);
        let provenance: (String, String, String) = db
            .query_row(
                "SELECT source_uri, locator, quote FROM provenance WHERE document_id = ?1",
                [&document.id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();
        assert_eq!(provenance.0, "https://github.com/octo/hello");
        assert_eq!(provenance.1, document.relative_path);
        assert_eq!(provenance.2, "hello");
        let results = search(&db, "hello", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].document_id, "github:octo/hello");
        assert!(root.join("sources/github/octo--hello.md").exists());
        let export = temp_root();
        assert_eq!(export_markdown(&root, &export).unwrap(), 1);
        assert!(export.join("sources/github/octo--hello.md").exists());
        let _ = std::fs::remove_dir_all(root);
        let _ = std::fs::remove_dir_all(export);
    }

    #[test]
    fn upsert_indexes_heading_aware_chunks() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        let document = SourceDocument {
            id: "article:chunked".into(),
            relative_path: "sources/article/chunked.md".into(),
            title: "Chunked article".into(),
            source_kind: "article".into(),
            source_uri: Some("https://example.com/chunked".into()),
            content: format!(
                "---\ntype: Test Document\n---\n\n# Intro\n{}\n\n# Next\nsecond",
                "a".repeat(1_300)
            ),
            captured_at: "2026-07-20T00:00:00Z".into(),
        };
        upsert_document(&mut db, &root, &document).unwrap();
        let chunks: Vec<(i64, i64, Option<String>, String)> = db
            .prepare("SELECT id, ordinal, heading_path, text FROM chunks WHERE document_id = ?1 ORDER BY ordinal")
            .unwrap()
            .query_map([&document.id], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
            })
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert!(chunks.len() >= 2);
        assert!(chunks
            .iter()
            .any(|(_, _, heading, _)| heading.as_deref() == Some("Intro")));
        assert!(chunks.iter().all(|(_, _, _, text)| text.len() <= 1_200));
        let first_chunk_id = chunks[0].0;
        db.execute(
            "INSERT INTO chunk_embeddings(chunk_id, model, dimensions, vector_json, created_at) VALUES(?1, 'test', 1, '[1.0]', 'now')",
            [first_chunk_id],
        )
        .unwrap();
        let updated = SourceDocument {
            content: "---\ntype: Test Document\n---\n\nshort".into(),
            ..document.clone()
        };
        upsert_document(&mut db, &root, &updated).unwrap();
        let stale_vectors: i64 = db
            .query_row(
                "SELECT COUNT(*) FROM chunk_embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = ?1)",
                [&document.id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(stale_vectors, 0);
        db.execute(
            "DELETE FROM chunk_fts WHERE rowid IN (SELECT id FROM chunks WHERE document_id = ?1)",
            [&updated.id],
        )
        .unwrap();
        db.execute("DELETE FROM chunks WHERE document_id = ?1", [&updated.id])
            .unwrap();
        upsert_document(&mut db, &root, &updated).unwrap();
        let restored_chunks: i64 = db
            .query_row(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?1",
                [&updated.id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(restored_chunks, 1);
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn markdown_writer_rejects_paths_outside_vault() {
        let root = temp_root();
        std::fs::create_dir_all(&root).unwrap();
        let outside = root.parent().unwrap().join("outside.md");
        let _ = std::fs::remove_file(&outside);
        let result = write_markdown_atomic(&root, "../outside.md", "blocked");
        assert_eq!(
            result.unwrap_err().kind(),
            std::io::ErrorKind::PermissionDenied
        );
        assert!(!outside.exists());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn load_document_rejects_database_path_traversal() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let db = open(&paths).unwrap();
        db.execute(
            "INSERT INTO documents(id, canonical_path, title, source_kind, content_hash, captured_at, updated_at) VALUES('unsafe', '../outside.md', 'Unsafe', 'test', 'hash', 'now', 'now')",
            [],
        )
        .unwrap();
        assert!(load_document(&db, &root, "unsafe").is_err());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn documents_do_not_create_implicit_reference_jobs() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        for (id, kind, path) in [
            ("source", "article", "sources/article.md"),
            ("fetched", "reference", "sources/references/fetched.md"),
            ("note", "distillation", "knowledge/note.md"),
        ] {
            upsert_document(
                &mut db,
                &root,
                &SourceDocument {
                    id: id.into(),
                    relative_path: path.into(),
                    title: id.into(),
                    source_kind: kind.into(),
                    source_uri: Some(format!("https://example.com/{id}")),
                    content: format!(
                        "---\ntype: Test Document\n---\n\nSee https://example.com/{id}-link."
                    ),
                    captured_at: "2026-07-20T00:00:00Z".into(),
                },
            )
            .unwrap();
        }

        let jobs = pending_reference_jobs(&db, 10).unwrap();
        assert!(jobs.is_empty());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn source_without_active_consent_queues_no_reference_jobs() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        upsert_document(
            &mut db,
            &root,
            &SourceDocument {
                id: "unconsented".into(),
                relative_path: "sources/unconsented.md".into(),
                title: "Unconsented source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/source".into()),
                content: "---\ntype: Test Document\n---\n\nSee https://example.com/reference."
                    .into(),
                captured_at: "2026-08-10T00:00:00Z".into(),
            },
        )
        .unwrap();

        assert!(pending_reference_jobs(&db, 10).unwrap().is_empty());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn explicit_exact_consent_queues_reference_job() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        upsert_document(
            &mut db,
            &root,
            &SourceDocument {
                id: "source".into(),
                relative_path: "sources/source.md".into(),
                title: "Source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/source".into()),
                content: "---\ntype: Test Document\n---\n\nSource".into(),
                captured_at: "2026-08-10T00:00:00Z".into(),
            },
        )
        .unwrap();
        let registry = ConsentRegistry::new(&db);
        registry
            .grant(ConsentGrant {
                id: "consent-1".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/reference/".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/reference",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());
        assert_eq!(pending_reference_jobs(&db, 10).unwrap().len(), 1);
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn pending_reference_jobs_skips_revoked_rows_before_applying_limit() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        upsert_document(
            &mut db,
            &root,
            &SourceDocument {
                id: "source".into(),
                relative_path: "sources/source.md".into(),
                title: "Source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/source".into()),
                content: "---\ntype: Test Document\n---\n\nSource".into(),
                captured_at: "2026-08-10T00:00:00Z".into(),
            },
        )
        .unwrap();
        let registry = ConsentRegistry::new(&db);

        registry
            .grant(ConsentGrant {
                id: "revoked-consent".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/revoked".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/revoked",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());
        assert!(registry
            .revoke("revoked-consent", "2026-08-10T01:30:00Z")
            .unwrap());

        registry
            .grant(ConsentGrant {
                id: "active-consent".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/allowed".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/allowed",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());
        registry
            .grant(ConsentGrant {
                id: "second-active-consent".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/second-allowed".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/second-allowed",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());

        assert_eq!(
            pending_reference_jobs_at(&db, 2, "2026-08-10T02:00:00Z").unwrap(),
            vec![
                ReferenceJob {
                    source_document_id: "source".into(),
                    target_url: "https://example.com/allowed".into(),
                },
                ReferenceJob {
                    source_document_id: "source".into(),
                    target_url: "https://example.com/second-allowed".into(),
                },
            ]
        );
        assert!(pending_reference_jobs_at(&db, 0, "2026-08-10T02:00:00Z")
            .unwrap()
            .is_empty());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn revoked_consent_removes_already_queued_reference_from_dequeue() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        upsert_document(
            &mut db,
            &root,
            &SourceDocument {
                id: "source".into(),
                relative_path: "sources/source.md".into(),
                title: "Source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/source".into()),
                content: "---\ntype: Test Document\n---\n\nSource".into(),
                captured_at: "2026-08-10T00:00:00Z".into(),
            },
        )
        .unwrap();
        ConsentRegistry::new(&db)
            .grant(ConsentGrant {
                id: "consent-1".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/reference".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/reference",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());
        assert_eq!(
            pending_reference_jobs_at(&db, 10, "2026-08-10T01:00:00Z")
                .unwrap()
                .len(),
            1
        );
        assert!(ConsentRegistry::new(&db)
            .revoke("consent-1", "2026-08-10T01:30:00Z")
            .unwrap());
        assert!(pending_reference_jobs_at(&db, 10, "2026-08-10T02:00:00Z")
            .unwrap()
            .is_empty());
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn revoked_consent_blocks_reference_job_before_fetch_claim() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut db = open(&paths).unwrap();
        upsert_document(
            &mut db,
            &root,
            &SourceDocument {
                id: "source".into(),
                relative_path: "sources/source.md".into(),
                title: "Source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/source".into()),
                content: "---\ntype: Test Document\n---\n\nSource".into(),
                captured_at: "2026-08-10T00:00:00Z".into(),
            },
        )
        .unwrap();
        let registry = ConsentRegistry::new(&db);
        registry
            .grant(ConsentGrant {
                id: "consent-1".into(),
                local_profile: "default".into(),
                provider: "manual".into(),
                purpose: "reference_fetch".into(),
                data_categories: vec!["public_web".into()],
                url_scope: "https://example.com/reference".into(),
                expires_at: None,
                version: 1,
                granted_at: "2026-08-10T00:00:00Z".into(),
            })
            .unwrap();
        assert!(queue_reference_fetch(
            &db,
            "source",
            "https://example.com/reference",
            "2026-08-10T01:00:00Z",
        )
        .unwrap());
        let job = pending_reference_jobs_at(&db, 1, "2026-08-10T01:00:00Z")
            .unwrap()
            .pop()
            .unwrap();
        assert!(registry
            .revoke("consent-1", "2026-08-10T01:30:00Z")
            .unwrap());

        assert!(!claim_reference_fetch_if_consented(&db, &job, "2026-08-10T02:00:00Z",).unwrap());
        assert_eq!(
            db.query_row(
                "SELECT status FROM reference_fetches WHERE source_document_id = ?1 AND target_url = ?2",
                rusqlite::params![job.source_document_id, job.target_url],
                |row| row.get::<_, String>(0),
            )
            .unwrap(),
            "blocked"
        );
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn queue_reference_command_rejects_unknown_source_before_consent_lookup() {
        let root = temp_root();
        let result = commands::queue_reference_fetch(commands::QueueReferenceFetchInput {
            vault_path: root.to_string_lossy().into_owned(),
            source_document_id: "missing".into(),
            target_url: "https://example.com/reference".into(),
            requested_at: "2026-08-10T01:00:00Z".into(),
        });
        assert_eq!(result, Err("source document not found".into()));
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn gh_token_output_is_trimmed_without_exposing_failure_output() {
        assert_eq!(
            commands::parse_gh_token_output(true, b"  ghp_test-token\n"),
            Ok("ghp_test-token".into())
        );
        assert!(commands::parse_gh_token_output(false, b"secret-token").is_err());
        assert!(commands::parse_gh_token_output(true, b"\n").is_err());
    }

    #[test]
    fn native_preferences_persist_valid_paths_and_reject_unsafe_ones() {
        let root = temp_root();
        let preferences = LocalPreferences {
            vault_path: Some("/tmp/research-vault".into()),
            hackernews_profile: Some("/tmp/hackernews-profile".into()),
            reddit_profile: None,
            x_profile: Some("/tmp/x-profile".into()),
        };

        native_preferences::save(&root, preferences.clone()).unwrap();
        assert_eq!(native_preferences::load(&root).unwrap(), preferences);
        assert!(native_preferences::validate(LocalPreferences {
            vault_path: Some("../escaped-vault".into()),
            ..LocalPreferences::default()
        })
        .is_err());
        assert!(native_preferences::validate(LocalPreferences {
            x_profile: Some("/tmp/profile\nwith-control-character".into()),
            ..LocalPreferences::default()
        })
        .is_err());
        let _ = std::fs::remove_dir_all(root);
    }
}
