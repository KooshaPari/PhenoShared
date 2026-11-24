#[cfg(test)]
mod read_model_tests {
    use super::super::storage::{initialize, open, upsert_document, SourceDocument};
    use super::{list_collections, list_document_links, list_document_summaries};
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    static TEMP_ROOT_COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root() -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "researchledger-read-model-{}-{}",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos(),
            TEMP_ROOT_COUNTER.fetch_add(1, Ordering::Relaxed),
        ))
    }

    fn seed(root: &std::path::Path) {
        let paths = initialize(root).unwrap();
        let mut connection = open(&paths).unwrap();
        for (id, title, kind, tags, body) in [
            ("a", "Alpha", "article", "[rust, research]", "[Beta](https://example.com/b)"),
            ("b", "Beta", "article", "[research, graph]", "No links"),
        ] {
            upsert_document(&mut connection, root, &SourceDocument {
                id: id.into(), relative_path: format!("{id}.md"), title: title.into(),
                source_kind: kind.into(), source_uri: None,
                content: format!("---\ntype: Test Document\ntags: {tags}\n---\n\n{body}"),
                captured_at: "2026-07-20T00:00:00Z".into(),
            }).unwrap();
        }
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
    fn document_summaries_include_tags_and_are_stable() {
        let root = temp_root();
        seed(&root);
        let result = list_document_summaries(root.to_string_lossy().into_owned()).unwrap();
        assert_eq!(result.iter().map(|item| item.title.as_str()).collect::<Vec<_>>(), ["Alpha", "Beta"]);
        assert_eq!(result[0].tags, ["research", "rust"]);
    }

    #[test]
    fn collections_count_documents_by_source_and_tag() {
        let root = temp_root();
        seed(&root);
        let result = list_collections(root.to_string_lossy().into_owned()).unwrap();
        assert_eq!(result.iter().find(|item| item.name == "research").unwrap().document_count, 2);
        assert_eq!(result.iter().find(|item| item.name == "article").unwrap().kind, "sourceKind");
    }

    #[test]
    fn document_links_return_graph_edges_with_source_metadata() {
        let root = temp_root();
        seed(&root);
        let result = list_document_links(root.to_string_lossy().into_owned()).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].source_document_id, "a");
        assert_eq!(result[0].target_url, "https://example.com/b");
    }

    #[test]
    fn claims_return_stable_source_citations() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut connection = open(&paths).unwrap();
        upsert_document(
            &mut connection,
            &root,
            &SourceDocument {
                id: "claim-source".into(),
                relative_path: "claim.md".into(),
                title: "Claim source".into(),
                source_kind: "article".into(),
                source_uri: Some("https://example.com/claim".into()),
                content: "---\ntype: Test Document\n---\n\nA durable ledger is local and reviewable.".into(),
                captured_at: "2026-07-20T00:00:00Z".into(),
            },
        )
        .unwrap();
        let claims = super::list_document_claims(
            root.to_string_lossy().into_owned(),
            "claim-source".into(),
        )
        .unwrap();
        assert_eq!(claims.len(), 1);
        assert_eq!(claims[0].citation_id, "1");
        assert_eq!(claims[0].source_uri.as_deref(), Some("https://example.com/claim"));
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn rejects_claim_records_with_out_of_range_positions() {
        let root = temp_root();
        let paths = initialize(&root).unwrap();
        let mut connection = open(&paths).unwrap();
        upsert_document(
            &mut connection,
            &root,
            &SourceDocument {
                id: "claim-overflow".into(),
                relative_path: "claim-overflow.md".into(),
                title: "Overflow claim".into(),
                source_kind: "article".into(),
                source_uri: None,
                content: "---\ntype: Test Document\n---\n\nA durable ledger is local.".into(),
                captured_at: "2026-07-20T00:00:00Z".into(),
            },
        )
        .unwrap();
        connection
            .execute(
                "UPDATE claims SET ordinal = ?2 WHERE document_id = ?1",
                rusqlite::params!["claim-overflow", i64::from(u32::MAX) + 1],
            )
            .unwrap();

        let error = super::list_document_claims(
            root.to_string_lossy().into_owned(),
            "claim-overflow".into(),
        )
        .unwrap_err();

        assert!(error.contains("ordinal"));
        let _ = std::fs::remove_dir_all(root);
    }
}
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct DocumentSummary {
    pub id: String,
    pub path: String,
    pub title: String,
    pub source_kind: String,
    pub source_uri: Option<String>,
    pub captured_at: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct CollectionSummary {
    pub name: String,
    pub kind: String,
    pub document_count: u64,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct DocumentLink {
    pub source_document_id: String,
    pub source_title: String,
    pub target_url: String,
    pub relation: String,
    pub discovered_at: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ClaimRecord {
    pub document_id: String,
    pub ordinal: u32,
    pub claim: String,
    pub source_uri: Option<String>,
    pub citation_id: String,
    pub evidence_quote: String,
    pub span_start: u32,
    pub span_end: u32,
}

fn claim_u32(row: &rusqlite::Row<'_>, column: usize, field: &str) -> rusqlite::Result<u32> {
    let value = row.get::<_, i64>(column)?;
    u32::try_from(value).map_err(|_| {
        rusqlite::Error::InvalidParameterName(format!(
            "claim {field} must fit within an unsigned 32-bit integer"
        ))
    })
}

fn connection(vault_path: &str) -> Result<rusqlite::Connection, String> {
    let paths = storage::initialize(std::path::Path::new(vault_path)).map_err(|e| e.to_string())?;
    storage::open(&paths).map_err(|e| e.to_string())
}

fn tags(content: &str) -> Vec<String> {
    let Some(frontmatter) = content.strip_prefix("---\n").and_then(|value| value.split_once("\n---")) else { return Vec::new() };
    let Some(value) = frontmatter.0.lines().find_map(|line| line.strip_prefix("tags:")) else { return Vec::new() };
    let mut tags = value.trim().trim_start_matches('[').trim_end_matches(']').split(',')
        .map(|tag| tag.trim().trim_matches(['"', '\'']).to_string())
        .filter(|tag| !tag.is_empty()).collect::<Vec<_>>();
    tags.sort();
    tags
}

#[tauri::command]
pub fn list_document_summaries(vault_path: String) -> Result<Vec<DocumentSummary>, String> {
    let root = std::path::PathBuf::from(&vault_path);
    let db = connection(&vault_path)?;
    let mut statement = db.prepare("SELECT id, canonical_path, title, source_kind, source_uri, captured_at FROM documents ORDER BY title COLLATE NOCASE, id")
        .map_err(|e| e.to_string())?;
    let rows = statement.query_map([], |row| {
        let path: String = row.get(1)?;
        let content = std::fs::read_to_string(root.join(&path)).unwrap_or_default();
        Ok(DocumentSummary { id: row.get(0)?, path, title: row.get(2)?, source_kind: row.get(3)?, source_uri: row.get(4)?, captured_at: row.get(5)?, tags: tags(&content) })
    }).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_collections(vault_path: String) -> Result<Vec<CollectionSummary>, String> {
    let documents = list_document_summaries(vault_path)?;
    let mut counts = std::collections::BTreeMap::<(String, String), u64>::new();
    for document in documents {
        *counts.entry(("sourceKind".into(), document.source_kind)).or_default() += 1;
        for tag in document.tags { *counts.entry(("tag".into(), tag)).or_default() += 1; }
    }
    Ok(counts.into_iter().map(|((kind, name), document_count)| CollectionSummary { name, kind, document_count }).collect())
}

#[tauri::command]
pub fn list_document_links(vault_path: String) -> Result<Vec<DocumentLink>, String> {
    let db = connection(&vault_path)?;
    let mut statement = db.prepare("SELECT l.source_document_id, d.title, l.target_url, l.relation, l.discovered_at FROM document_links l JOIN documents d ON d.id=l.source_document_id ORDER BY l.source_document_id, l.target_url")
        .map_err(|e| e.to_string())?;
    let rows = statement.query_map([], |row| Ok(DocumentLink { source_document_id: row.get(0)?, source_title: row.get(1)?, target_url: row.get(2)?, relation: row.get(3)?, discovered_at: row.get(4)? }))
        .map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_document_claims(
    vault_path: String,
    document_id: String,
) -> Result<Vec<ClaimRecord>, String> {
    let db = connection(&vault_path)?;
    let mut statement = db
        .prepare(
            "SELECT document_id, ordinal, claim, source_uri, citation_id, evidence_quote, span_start, span_end FROM claims
             WHERE document_id = ?1 ORDER BY ordinal",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(rusqlite::params![document_id], |row| {
            Ok(ClaimRecord {
                document_id: row.get(0)?,
                ordinal: claim_u32(row, 1, "ordinal")?,
                claim: row.get(2)?,
                source_uri: row.get(3)?,
                citation_id: row.get(4)?,
                evidence_quote: row.get(5)?,
                span_start: claim_u32(row, 6, "span start")?,
                span_end: claim_u32(row, 7, "span end")?,
            })
        })
        .map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())
}
