//! Integration tests for [`phenotype_registry::ecosystem::parse_ecosystem_map`].

use phenotype_registry::ecosystem::{parse_ecosystem_map, ParseError};

// ── Minimal / edge-case inputs ───────────────────────────────────────────────

#[test]
fn empty_string_yields_empty_input_error() {
    assert_eq!(parse_ecosystem_map(""), Err(ParseError::EmptyInput));
}

#[test]
fn whitespace_only_yields_empty_input_error() {
    assert_eq!(
        parse_ecosystem_map("   \n  \n   "),
        Err(ParseError::EmptyInput)
    );
}

#[test]
fn prose_without_tables_yields_empty_input_error() {
    assert_eq!(
        parse_ecosystem_map("This is just a paragraph.\nNothing to parse here.\n"),
        Err(ParseError::EmptyInput)
    );
}

// ── Role Classification table ────────────────────────────────────────────────

#[test]
fn role_classification_single_row() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 2 | alpha, beta |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 2);

    let alpha = entries.iter().find(|e| e.name == "alpha").unwrap();
    assert_eq!(alpha.role, "shared-lib");

    let beta = entries.iter().find(|e| e.name == "beta").unwrap();
    assert_eq!(beta.role, "shared-lib");
}

#[test]
fn role_classification_bold_names_stripped() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **SDK** | 1 | **MyCrate** |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "MyCrate");
    assert_eq!(entries[0].role, "SDK");
}

#[test]
fn role_classification_multiple_rows() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 2 | pheno, HexaKit |
| **SDK** | 1 | AuthKit |
| **tooling** | 3 | AgilePlus, Conft, phenodevops |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 6);
    assert!(entries.iter().any(|e| e.name == "pheno" && e.role == "shared-lib"));
    assert!(entries.iter().any(|e| e.name == "AuthKit" && e.role == "SDK"));
    assert!(entries.iter().any(|e| e.name == "AgilePlus" && e.role == "tooling"));
}

#[test]
fn role_classification_parenthetical_notes_stripped() {
    // Some repos in the real map appear like: phenotype-gfx (single canonical...
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 1 | phenotype-gfx (single canonical graphics core, ADR-004) |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "phenotype-gfx");
}

// ── Unknown Repos Triage table ───────────────────────────────────────────────

#[test]
fn triage_table_parses_all_fields() {
    let md = "\
| Repo | Lang | Pushed | Proposed role | Notes |
|------|------|--------|---------------|-------|
| `phenotype-pm-core` | TypeScript | 2026-06-23 | shared-lib | PM core SDK |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);

    let e = &entries[0];
    assert_eq!(e.name, "phenotype-pm-core");
    assert_eq!(e.language.as_deref(), Some("TypeScript"));
    assert_eq!(e.role, "shared-lib");
    assert_eq!(e.notes.as_deref(), Some("PM core SDK"));
}

#[test]
fn triage_table_multiple_rows() {
    let md = "\
| Repo | Lang | Pushed | Proposed role | Notes |
|------|------|--------|---------------|-------|
| `repo-a` | Rust | 2026-06-23 | shared-lib | note A |
| `repo-b` | Python | 2026-06-22 | docs | note B |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 2);
    assert!(entries.iter().any(|e| e.name == "repo-a"));
    assert!(entries.iter().any(|e| e.name == "repo-b"));
}

// ── Cluster tables ───────────────────────────────────────────────────────────

#[test]
fn cluster_row_parses_status_and_language() {
    let md = "\
| Repo | Status | Verdict |
|------|--------|---------|
| **Agentora** | Active, Rust, hexagonal-arch | **CANONICAL** — full skill/tool/memory/event system |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "Agentora");
    assert_eq!(entries[0].language.as_deref(), Some("Rust"));
}

#[test]
fn cluster_table_not_confused_with_role_table() {
    // The role table has "Count" which should prevent it from matching as a cluster table.
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 2 | alpha, beta |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 2);
    assert!(entries.iter().all(|e| e.role == "shared-lib"));
}

// ── Dependency adjacency list ────────────────────────────────────────────────

#[test]
fn dep_edge_basic() {
    let md = "foo -> bar, baz\n";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].dependencies, vec!["bar", "baz"]);
}

#[test]
fn dep_edge_with_bracket_notes_stripped() {
    let md = "phenotype-registry -> PhenoSpecs, HexaKit [doc links]\n";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries[0].dependencies, vec!["PhenoSpecs", "HexaKit"]);
}

#[test]
fn dep_edge_standalone_paren_note_yields_no_deps() {
    let md = "phenotype-infra -> (standalone IaC/spec, no code deps)\n";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert!(entries[0].dependencies.is_empty());
}

#[test]
fn dep_edge_single_dep() {
    let md = "phenodocs -> phenoShared\n";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries[0].dependencies, vec!["phenoShared"]);
}

// ── Merging across sections ──────────────────────────────────────────────────

#[test]
fn merge_role_and_dep_edge() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 1 | foo |

foo -> bar
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "foo");
    assert_eq!(entries[0].role, "shared-lib");
    assert_eq!(entries[0].dependencies, vec!["bar"]);
}

#[test]
fn merge_triage_and_cluster_data() {
    let md = "\
| Repo | Lang | Pushed | Proposed role | Notes |
|------|------|--------|---------------|-------|
| `my-repo` | TypeScript | 2026-06-23 | shared-lib | initial |

| Repo | Status | Verdict |
|------|--------|---------|
| **my-repo** | Active, TypeScript | **CANONICAL** |
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);

    let e = &entries[0];
    assert_eq!(e.name, "my-repo");
    assert_eq!(e.language.as_deref(), Some("TypeScript"));
    assert_eq!(e.role, "shared-lib");
}

#[test]
fn merge_role_and_cluster_and_deps() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 1 | MyRepo |

| Repo | Status | Verdict |
|------|--------|---------|
| **MyRepo** | Active, Rust | **CANONICAL** |

MyRepo -> OtherRepo
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "MyRepo");
    assert_eq!(entries[0].role, "shared-lib");
    assert_eq!(entries[0].language.as_deref(), Some("Rust"));
    assert_eq!(entries[0].dependencies, vec!["OtherRepo"]);
}

// ── Deduplication ────────────────────────────────────────────────────────────

#[test]
fn same_repo_across_sections_deduplicates() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **tooling** | 1 | shared-utils |

| Repo | Status | Verdict |
|------|--------|---------|
| **shared-utils** | Active, Rust | **AFFIRM** |

shared-utils -> dep-a, dep-b
";
    let entries = parse_ecosystem_map(md).unwrap();
    assert_eq!(entries.len(), 1);
    let e = &entries[0];
    assert_eq!(e.name, "shared-utils");
    assert_eq!(e.role, "tooling");
    assert_eq!(e.dependencies, vec!["dep-a", "dep-b"]);
}

// ── Output is sorted by name ─────────────────────────────────────────────────

#[test]
fn output_is_sorted_by_name() {
    let md = "\
| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 3 | charlie, alpha, bravo |
";
    let entries = parse_ecosystem_map(md).unwrap();
    let names: Vec<&str> = entries.iter().map(|e| e.name.as_str()).collect();
    assert_eq!(names, vec!["alpha", "bravo", "charlie"]);
}

// ── Comprehensive real-world-like test ───────────────────────────────────────

#[test]
fn parse_realistic_ecosystem_snippet() {
    let md = r#"# Ecosystem Map

## 1. Role Classification (3 repos)

| Role | Count | Repos |
|------|-------|-------|
| **shared-lib** | 2 | phenotype-core, phenotype-utils |
| **tooling** | 1 | phenotype-lint |

| Repo | Lang | Pushed | Proposed role | Notes |
|------|------|--------|---------------|-------|
| `phenotype-new` | Go | 2026-06-23 | agent-runtime | new agent lib |

## 2. Dependency Edges

```text
phenotype-core -> phenotype-utils
phenotype-lint -> phenotype-core, phenotype-utils
```

## 3. Duplication Clusters

### Cluster A

| Repo | Status | Verdict |
|------|--------|---------|
| **phenotype-core** | Active, Rust | **CANONICAL** |
| **phenotype-utils** | Active, Rust | **CANONICAL** |
"#;

    let entries = parse_ecosystem_map(md).unwrap();

    // Should have 3 unique repos from role table + 1 from triage = 4 total.
    assert_eq!(entries.len(), 4);

    let core = entries.iter().find(|e| e.name == "phenotype-core").unwrap();
    assert_eq!(core.role, "shared-lib");
    assert_eq!(core.language.as_deref(), Some("Rust"));
    assert_eq!(core.dependencies, vec!["phenotype-utils"]);

    let lint = entries.iter().find(|e| e.name == "phenotype-lint").unwrap();
    assert_eq!(lint.role, "tooling");
    assert_eq!(lint.dependencies, vec!["phenotype-core", "phenotype-utils"]);

    let new = entries.iter().find(|e| e.name == "phenotype-new").unwrap();
    assert_eq!(new.role, "agent-runtime");
    assert_eq!(new.language.as_deref(), Some("Go"));
}

// ── Error display ────────────────────────────────────────────────────────────

#[test]
fn parse_error_display() {
    let err = ParseError::MalformedTable {
        line: 5,
        detail: "expected 3 columns".to_string(),
    };
    assert_eq!(format!("{err}"), "malformed table at line 5: expected 3 columns");

    let err = ParseError::EmptyInput;
    assert_eq!(format!("{err}"), "input is empty");
}
