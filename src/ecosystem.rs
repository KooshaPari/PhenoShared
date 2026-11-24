//! Parse the [`ECOSYSTEM_MAP.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/ECOSYSTEM_MAP.md)
//! markdown format into structured [`RepoEntry`] records.
//!
//! The ecosystem map contains several parseable table formats:
//!
//! - **Role Classification** (`| Role | Count | Repos |`) — comma-separated repo names per role.
//! - **Unknown Repos Triage** (`| Repo | Lang | Pushed | Proposed role | Notes |`).
//! - **Cluster tables** (`| Repo | Status | Verdict | ...`).
//! - **Dependency adjacency list** (plaintext `A -> B, C [note]`).
//!
//! `parse_ecosystem_map` merges data from all of these into a deduplicated
//! list of [`RepoEntry`] values keyed by repository name.

use std::collections::HashMap;

/// A single repository entry extracted from the ecosystem map.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RepoEntry {
    /// Repository name (e.g. `"phenotype-registry"`).
    pub name: String,
    /// Role classification (e.g. `"shared-lib"`, `"SDK"`, `"tooling"`).
    pub role: String,
    /// Primary programming language, when known.
    pub language: Option<String>,
    /// Lifecycle status (e.g. `"Active"`, `"Archived"`, `"CANONICAL"`).
    pub status: Option<String>,
    /// Free-form notes attached to the row.
    pub notes: Option<String>,
    /// Names of repositories this one depends on.
    pub dependencies: Vec<String>,
}

/// Errors that can occur while parsing an ecosystem map.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    /// The input contained no parseable content.
    EmptyInput,
    /// A markdown table row could not be understood.
    MalformedTable { line: usize, detail: String },
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ParseError::EmptyInput => write!(f, "input is empty"),
            ParseError::MalformedTable { line, detail } => {
                write!(f, "malformed table at line {line}: {detail}")
            }
        }
    }
}

impl std::error::Error for ParseError {}

// ── Public API ───────────────────────────────────────────────────────────────

/// Parse an `ECOSYSTEM_MAP.md` document and return a deduplicated list of
/// [`RepoEntry`] values.
///
/// The function is intentionally lenient: it skips lines it does not
/// recognise and never returns an error for partial input. The only
/// hard errors are [`ParseError::EmptyInput`] (nothing at all was
/// found) and [`ParseError::MalformedTable`] (a table row that *looks*
/// like it should be parseable but violates the expected column count).
///
/// # Examples
///
/// ```rust
/// use phenotype_registry::ecosystem::{parse_ecosystem_map, ParseError};
///
/// let md = r#"
/// ## 1. Role Classification (2 repos)
///
/// | Role | Count | Repos |
/// |------|-------|-------|
/// | **shared-lib** | 2 | alpha, beta |
/// "#;
///
/// let entries = parse_ecosystem_map(md).unwrap();
/// assert_eq!(entries.len(), 2);
/// assert_eq!(entries[0].name, "alpha");
/// assert_eq!(entries[0].role, "shared-lib");
/// ```
pub fn parse_ecosystem_map(input: &str) -> Result<Vec<RepoEntry>, ParseError> {
    if input.trim().is_empty() {
        return Err(ParseError::EmptyInput);
    }

    let lines: Vec<&str> = input.lines().collect();

    // Accumulators keyed by repo name.
    let mut repos: HashMap<String, RepoEntry> = HashMap::new();

    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];

        // ── 1. Role Classification table ──────────────────────────────────
        // Header: | Role | Count | Repos |
        // Rows:   | **shared-lib** | 23 | pheno, HexaKit, ... |
        if looks_like_role_classification_header(line) {
            i += 2; // skip header + separator
            while i < lines.len() && is_table_row(lines[i]) {
                parse_role_row(lines[i], i, &mut repos)?;
                i += 1;
            }
            continue;
        }

        // ── 2. Unknown Repos Triage table ─────────────────────────────────
        // Header: | Repo | Lang | Pushed | Proposed role | Notes |
        if looks_like_triage_header(line) {
            i += 2; // skip header + separator
            while i < lines.len() && is_table_row(lines[i]) {
                parse_triage_row(lines[i], i, &mut repos)?;
                i += 1;
            }
            continue;
        }

        // ── 3. Dependency adjacency list ──────────────────────────────────
        // Lines like: phenotype-infra -> (standalone IaC/spec, no code deps)
        if looks_like_dep_edge(line) {
            parse_dep_edge(line, &mut repos);
            i += 1;
            continue;
        }

        // ── 4. Cluster / generic Repo | Status | Verdict tables ───────────
        // Header: | Repo | Status | Verdict |
        // Also:    | Repo | Status | Verdict | Notes |
        if looks_like_cluster_header(line) {
            i += 2; // skip header + separator
            while i < lines.len() && is_table_row(lines[i]) {
                parse_cluster_row(lines[i], i, &mut repos)?;
                i += 1;
            }
            continue;
        }

        i += 1;
    }

    if repos.is_empty() {
        return Err(ParseError::EmptyInput);
    }

    let mut result: Vec<RepoEntry> = repos.into_values().collect();
    result.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(result)
}

// ── Table pattern detectors ──────────────────────────────────────────────────

fn is_table_row(line: &str) -> bool {
    let trimmed = line.trim();
    trimmed.starts_with('|') && trimmed.ends_with('|')
}

/// Heuristic: the role classification header contains "Role", "Count", and
/// "Repos" (case-insensitive, word-boundary-free).
fn looks_like_role_classification_header(line: &str) -> bool {
    let lower = line.to_lowercase();
    lower.contains("role") && lower.contains("count") && lower.contains("repos")
}

/// Heuristic: the triage header contains "Repo", "Lang", "Pushed", and
/// "Proposed role".
fn looks_like_triage_header(line: &str) -> bool {
    let lower = line.to_lowercase();
    lower.contains("repo") && lower.contains("lang") && lower.contains("pushed")
        && lower.contains("proposed role")
}

/// Heuristic: a cluster header is a table row that starts with "| Repo" and
/// contains "Status" and "Verdict" — but *not* "Count" (which would be the
/// role table) and not "Pushed" (which would be the triage table).
fn looks_like_cluster_header(line: &str) -> bool {
    let lower = line.to_lowercase();
    lower.contains("repo") && lower.contains("status") && lower.contains("verdict")
        && !lower.contains("count") && !lower.contains("pushed")
}

/// A dependency edge line: starts with a non-empty identifier, followed by `->`.
fn looks_like_dep_edge(line: &str) -> bool {
    let trimmed = line.trim();
    if trimmed.is_empty() || trimmed.starts_with('|') || trimmed.starts_with('#') {
        return false;
    }
    trimmed.contains("->")
}

// ── Row parsers ──────────────────────────────────────────────────────────────

/// Parse a role-classification row:
///
/// ```text
/// | **shared-lib** | 23 | pheno, HexaKit, phenoShared, ... |
/// ```
fn parse_role_row(
    line: &str,
    line_num: usize,
    repos: &mut HashMap<String, RepoEntry>,
) -> Result<(), ParseError> {
    let cells = split_table_row(line);
    if cells.len() < 3 {
        return Err(ParseError::MalformedTable {
            line: line_num + 1,
            detail: format!("expected 3+ columns, got {}", cells.len()),
        });
    }

    let role = strip_bold(cells[0].trim());
    let repo_cell = cells[2]; // third column is the repo list

    for raw_name in split_respecting_parens(repo_cell) {
        let name = strip_bold(raw_name.trim())
            .trim_matches(|c: char| c == '(' || c == ')' || c == '*' || c.is_whitespace())
            .to_string();

        // Skip obvious non-repo tokens (bare numbers, empty strings, inline notes)
        if name.is_empty() || name.chars().all(|c| c.is_numeric()) {
            continue;
        }

        // Strip inline parenthetical notes that may follow a name, e.g.
        // "phenotype-gfx (single canonical..." → "phenotype-gfx"
        let clean_name = strip_inline_note(&name);

        // Only insert if this is a plausible repo name (contains at least one
        // letter or hyphen).
        if clean_name.chars().any(|c| c.is_alphabetic()) {
            let entry = repos.entry(clean_name.clone()).or_insert_with(|| RepoEntry {
                name: clean_name,
                role: role.clone(),
                language: None,
                status: None,
                notes: None,
                dependencies: Vec::new(),
            });
            // If we already have an entry, just ensure the role is set.
            if entry.role.is_empty() {
                entry.role = role.clone();
            }
        }
    }

    Ok(())
}

/// Parse a triage row:
///
/// ```text
/// | `phenotype-pm-core` | TypeScript | 2026-06-23 | shared-lib | PM core SDK |
/// ```
fn parse_triage_row(
    line: &str,
    line_num: usize,
    repos: &mut HashMap<String, RepoEntry>,
) -> Result<(), ParseError> {
    let cells = split_table_row(line);
    if cells.len() < 4 {
        return Err(ParseError::MalformedTable {
            line: line_num + 1,
            detail: format!("expected 4+ columns, got {}", cells.len()),
        });
    }

    let name = clean_repo_name(cells[0].trim());
    if name.is_empty() {
        return Ok(());
    }

    let language = Some(cells[1].trim().to_string());
    let role = cells[3].trim().to_string();
    let notes = if cells.len() > 4 {
        Some(cells[4].trim().to_string())
    } else {
        None
    };

    let entry = repos.entry(name.clone()).or_insert_with(|| RepoEntry {
        name,
        role: role.clone(),
        language: language.clone(),
        status: None,
        notes: notes.clone(),
        dependencies: Vec::new(),
    });

    // Merge — fill in blanks.
    if entry.role.is_empty() {
        entry.role = role;
    }
    if entry.language.is_none() {
        entry.language = language;
    }
    if entry.notes.is_none() {
        entry.notes = notes;
    }

    Ok(())
}

/// Parse a cluster row:
///
/// ```text
/// | **Agentora** | Active, Rust, hexagonal-arch | **CANONICAL** — full skill/tool/memory/event system |
/// ```
fn parse_cluster_row(
    line: &str,
    line_num: usize,
    repos: &mut HashMap<String, RepoEntry>,
) -> Result<(), ParseError> {
    let cells = split_table_row(line);
    if cells.len() < 3 {
        return Err(ParseError::MalformedTable {
            line: line_num + 1,
            detail: format!("expected 3+ columns, got {}", cells.len()),
        });
    }

    let name = clean_repo_name(cells[0].trim());
    if name.is_empty() {
        return Ok(());
    }

    let status_raw = cells[1].trim().to_string();
    let verdict_raw = strip_bold(cells[2].trim());

    // Split "Active, Rust, hexagonal-arch" → status="Active", language=Some("Rust")
    let (status, language) = split_status_language(&status_raw);

    let entry = repos.entry(name.clone()).or_insert_with(|| RepoEntry {
        name,
        role: String::new(),
        language: language.clone(),
        status: Some(status.clone()),
        notes: None,
        dependencies: Vec::new(),
    });

    if entry.status.is_none() {
        entry.status = Some(status);
    }
    if entry.language.is_none() {
        entry.language = language;
    }
    // Merge notes from verdict column (take first meaningful chunk).
    if entry.notes.is_none() && !verdict_raw.is_empty() {
        entry.notes = Some(verdict_raw);
    }

    Ok(())
}

/// Parse a dependency adjacency line:
///
/// ```text
/// phenotype-infra -> (standalone IaC/spec, no code deps)
/// phenotype-registry -> PhenoSpecs, HexaKit, PhenoHandbook [doc links]
/// ```
fn parse_dep_edge(line: &str, repos: &mut HashMap<String, RepoEntry>) {
    let trimmed = line.trim();
    let Some((src, rest)) = trimmed.split_once("->") else {
        return;
    };
    let src = clean_repo_name(src.trim());
    if src.is_empty() {
        return;
    }

    // If the entire remainder is a parenthetical note (e.g. "(standalone IaC/spec, no code deps)"),
    // there are no dependencies to extract.
    let rest_trimmed = rest.trim();
    let no_deps = rest_trimmed.starts_with('(')
        && rest_trimmed.contains(')')
        && rest_trimmed
            .chars()
            .filter(|c| *c == '(')
            .count()
            <= rest_trimmed
                .chars()
                .filter(|c| *c == ')')
                .count();
    if no_deps {
        repos.entry(src.clone()).or_insert_with(|| RepoEntry {
            name: src,
            role: String::new(),
            language: None,
            status: None,
            notes: None,
            dependencies: Vec::new(),
        });
        return;
    }

    let deps: Vec<String> = rest
        .split(',')
        .map(|d| {
            // Strip inline notes in brackets: `Foo [doc links]` → `Foo`
            let d = d.split('[').next().unwrap_or(d);
            // Strip parenthetical notes: `(standalone...)` → skip
            let d = d.trim();
            if d.starts_with('(') {
                String::new()
            } else {
                clean_repo_name(d)
            }
        })
        .filter(|d| !d.is_empty() && d.chars().any(|c| c.is_alphabetic()))
        .collect();

    let entry = repos.entry(src.clone()).or_insert_with(|| RepoEntry {
        name: src,
        role: String::new(),
        language: None,
        status: None,
        notes: None,
        dependencies: Vec::new(),
    });

    // Merge — add any new deps we don't already have.
    for dep in deps {
        if !entry.dependencies.contains(&dep) {
            entry.dependencies.push(dep);
        }
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/// Split a markdown table row into cell strings (excluding leading/trailing `|`).
fn split_table_row(line: &str) -> Vec<&str> {
    let trimmed = line.trim();
    let inner = trimmed
        .strip_prefix('|')
        .and_then(|s| s.strip_suffix('|'))
        .unwrap_or(trimmed);
    inner.split('|').collect()
}

/// Split a comma-separated string, but only on commas that are outside of
/// parenthetical groups. This prevents splitting on commas inside notes like
/// `phenotype-gfx (single canonical graphics core, ADR-004)`.
fn split_respecting_parens(s: &str) -> Vec<&str> {
    let mut result = Vec::new();
    let mut depth: usize = 0;
    let mut start = 0;
    for (i, ch) in s.char_indices() {
        match ch {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            ',' if depth == 0 => {
                result.push(&s[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    result.push(&s[start..]);
    result
}

/// Strip `**bold**` markdown markers and backticks from a string.
fn strip_bold(s: &str) -> String {
    s.replace("**", "").replace('`', "").trim().to_string()
}

/// Remove backticks and bold markers from a repo name cell.
fn clean_repo_name(s: &str) -> String {
    strip_bold(s)
}

/// Strip an inline parenthetical note that appears after a repo name.
///
/// `"phenotype-gfx (single canonical...)"` → `"phenotype-gfx"`
fn strip_inline_note(name: &str) -> String {
    match name.find('(') {
        Some(pos) => name[..pos].trim().to_string(),
        None => name.to_string(),
    }
}

/// Split a cluster status cell like `"Active, Rust, hexagonal-arch"` into
/// `(status, language)`.
fn split_status_language(raw: &str) -> (String, Option<String>) {
    let parts: Vec<&str> = raw.split(',').map(|s| s.trim()).collect();
    let status = parts[0].to_string();
    // Second token is often the language.
    let language = if parts.len() > 1 && is_likely_language(parts[1]) {
        Some(parts[1].to_string())
    } else {
        None
    };
    (status, language)
}

/// Very simple heuristic: a token is likely a programming language if it
/// matches common names.
fn is_likely_language(token: &str) -> bool {
    matches!(
        token,
        "Rust"
            | "TypeScript"
            | "JavaScript"
            | "Python"
            | "Go"
            | "C"
            | "C++"
            | "C#"
            | "Java"
            | "Kotlin"
            | "Swift"
            | "Zig"
            | "Mojo"
            | "Ruby"
            | "Scala"
            | "Haskell"
            | "PHP"
            | "Shell"
            | "Bash"
            | "TypeScript/JavaScript"
            | "ts"
            | "js"
            | "py"
            | "rs"
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_input_returns_error() {
        assert_eq!(parse_ecosystem_map(""), Err(ParseError::EmptyInput));
        assert_eq!(parse_ecosystem_map("  \n  \n  "), Err(ParseError::EmptyInput));
    }

    #[test]
    fn single_role_row() {
        let md = "| Role | Count | Repos |\n|------|-------|-------|\n| **shared-lib** | 2 | alpha, beta |\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].name, "alpha");
        assert_eq!(entries[0].role, "shared-lib");
        assert_eq!(entries[1].name, "beta");
    }

    #[test]
    fn role_row_with_bold_names() {
        let md = "| Role | Count | Repos |\n|------|-------|-------|\n| **SDK** | 1 | **MyCrate** |\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "MyCrate");
        assert_eq!(entries[0].role, "SDK");
    }

    #[test]
    fn triage_row() {
        let md = "| Repo | Lang | Pushed | Proposed role | Notes |\n|------|------|--------|---------------|-------|\n| `my-repo` | Rust | 2026-06-23 | shared-lib | some notes |\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "my-repo");
        assert_eq!(entries[0].role, "shared-lib");
        assert_eq!(entries[0].language.as_deref(), Some("Rust"));
    }

    #[test]
    fn cluster_row() {
        let md = "| Repo | Status | Verdict |\n|------|--------|---------|\n| **Agentora** | Active, Rust, hexagonal-arch | **CANONICAL** |\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "Agentora");
        assert_eq!(entries[0].language.as_deref(), Some("Rust"));
    }

    #[test]
    fn dep_edge_basic() {
        let md = "foo -> bar, baz\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "foo");
        assert_eq!(entries[0].dependencies, vec!["bar", "baz"]);
    }

    #[test]
    fn dep_edge_with_inline_notes() {
        let md = "phenotype-registry -> PhenoSpecs, HexaKit [doc links]\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].dependencies, vec!["PhenoSpecs", "HexaKit"]);
    }

    #[test]
    fn dep_edge_standalone_note() {
        let md = "phenotype-infra -> (standalone IaC/spec, no code deps)\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert!(entries[0].dependencies.is_empty());
    }

    #[test]
    fn merge_role_and_dep_edge() {
        let md = "| Role | Count | Repos |\n|------|-------|-------|\n| **shared-lib** | 1 | foo |\n\nfoo -> bar\n";
        let entries = parse_ecosystem_map(md).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "foo");
        assert_eq!(entries[0].role, "shared-lib");
        assert_eq!(entries[0].dependencies, vec!["bar"]);
    }
}
