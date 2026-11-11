//! `sl tag` — read and mutate the `tags` array in OKF bundle JSON files.
//!
//! All operations are pure JSON mutations; no compilation or network required.
//! The `tags` field is stored as a top-level `["tag1", "tag2"]` array in the
//! `.okf.json` file.  When the field is absent it is treated as empty and
//! created on first write.

use std::path::{Path, PathBuf};

/// Errors that can occur during tag operations.
#[derive(Debug, thiserror::Error)]
pub enum TagError {
    /// I/O failure reading or writing the bundle file.
    #[error("I/O error on {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },

    /// The file contents are not valid JSON.
    #[error("JSON parse error in {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },

    /// The file is valid JSON but not a JSON object (unexpected format).
    #[error("{path}: expected a JSON object at the top level")]
    NotAnObject { path: PathBuf },
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Read an OKF bundle JSON file and return the parsed `Value`.
fn read_bundle(path: &Path) -> Result<serde_json::Value, TagError> {
    let text = std::fs::read_to_string(path)
        .map_err(|source| TagError::Io { path: path.to_owned(), source })?;
    serde_json::from_str(&text).map_err(|source| TagError::Json { path: path.to_owned(), source })
}

/// Write a `serde_json::Value` back to `path` as pretty-printed JSON.
fn write_bundle(path: &Path, value: &serde_json::Value) -> Result<(), TagError> {
    let text = serde_json::to_string_pretty(value)
        .map_err(|source| TagError::Json { path: path.to_owned(), source })?;
    std::fs::write(path, text).map_err(|source| TagError::Io { path: path.to_owned(), source })
}

/// Extract the `tags` array from a JSON object as a `Vec<String>`.
/// Returns an empty vec when the key is absent.
pub fn tags_from_value(value: &serde_json::Value) -> Vec<String> {
    value
        .get("tags")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default()
}

/// Replace the `tags` array in a JSON object.  Errors when the value is not
/// an object.
pub fn set_tags_on_value(
    value: &mut serde_json::Value,
    tags: Vec<String>,
    path: &Path,
) -> Result<(), TagError> {
    let obj =
        value.as_object_mut().ok_or_else(|| TagError::NotAnObject { path: path.to_owned() })?;
    obj.insert(
        "tags".to_owned(),
        serde_json::Value::Array(tags.into_iter().map(serde_json::Value::String).collect()),
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Return the current tags on a bundle file.
pub fn list(bundle: &Path) -> Result<Vec<String>, TagError> {
    let value = read_bundle(bundle)?;
    Ok(tags_from_value(&value))
}

/// Append `new_tags` to the bundle's tag list (duplicates are skipped).
/// Returns the updated tag list.
pub fn add(bundle: &Path, new_tags: &[String]) -> Result<Vec<String>, TagError> {
    let mut value = read_bundle(bundle)?;
    let mut tags = tags_from_value(&value);
    for t in new_tags {
        if !tags.contains(t) {
            tags.push(t.clone());
        }
    }
    set_tags_on_value(&mut value, tags.clone(), bundle)?;
    write_bundle(bundle, &value)?;
    Ok(tags)
}

/// Remove `remove_tags` from the bundle's tag list.
/// Tags not present are silently ignored.
/// Returns the updated tag list.
pub fn remove(bundle: &Path, remove_tags: &[String]) -> Result<Vec<String>, TagError> {
    let mut value = read_bundle(bundle)?;
    let mut tags = tags_from_value(&value);
    tags.retain(|t| !remove_tags.contains(t));
    set_tags_on_value(&mut value, tags.clone(), bundle)?;
    write_bundle(bundle, &value)?;
    Ok(tags)
}

/// Scan every `*.okf.json` file under `dir` (recursively) and return paths
/// that contain `tag` in their `tags` array.
pub fn search_dir(dir: &Path, tag: &str) -> Result<Vec<PathBuf>, TagError> {
    let mut matches = Vec::new();
    visit_okf_files(dir, &mut |path| match read_bundle(&path) {
        Ok(value) => {
            if tags_from_value(&value).iter().any(|t| t == tag) {
                matches.push(path);
            }
        }
        Err(e) => {
            eprintln!("warning: skipping {}: {e}", path.display());
        }
    });
    Ok(matches)
}

/// Walk `dir` and call `cb` for every `*.okf.json` file found.
fn visit_okf_files(dir: &Path, cb: &mut impl FnMut(PathBuf)) {
    let Ok(entries) = std::fs::read_dir(dir) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            visit_okf_files(&path, cb);
        } else if path.extension().is_some_and(|e| e == "json")
            && path.file_name().is_some_and(|n| n.to_string_lossy().ends_with(".okf.json"))
        {
            cb(path);
        }
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    /// Write a minimal OKF-like JSON object to a temp file and return it.
    fn make_bundle(tags: &[&str]) -> NamedTempFile {
        let f = NamedTempFile::new().unwrap();
        let tags_json: serde_json::Value = serde_json::Value::Array(
            tags.iter().map(|t| serde_json::Value::String(t.to_string())).collect(),
        );
        let obj = serde_json::json!({
            "okf": "1.0",
            "source_id": "test-sess",
            "entities": [],
            "provenance": { "corpus": "test", "source_id": "test-sess" },
            "tags": tags_json
        });
        serde_json::to_writer_pretty(f.as_file(), &obj).unwrap();
        f
    }

    /// Make a bundle file without a `tags` field at all.
    fn make_bundle_no_tags() -> NamedTempFile {
        let f = NamedTempFile::new().unwrap();
        let obj = serde_json::json!({
            "okf": "1.0",
            "source_id": "no-tags-sess",
            "entities": [],
            "provenance": { "corpus": "test", "source_id": "no-tags-sess" }
        });
        serde_json::to_writer_pretty(f.as_file(), &obj).unwrap();
        f
    }

    // ------------------------------------------------------------------
    // list
    // ------------------------------------------------------------------

    #[test]
    fn list_returns_existing_tags() {
        let f = make_bundle(&["rust", "async"]);
        let tags = list(f.path()).unwrap();
        assert_eq!(tags, vec!["rust", "async"]);
    }

    #[test]
    fn list_returns_empty_when_no_tags_field() {
        let f = make_bundle_no_tags();
        let tags = list(f.path()).unwrap();
        assert!(tags.is_empty());
    }

    #[test]
    fn list_returns_empty_for_empty_array() {
        let f = make_bundle(&[]);
        let tags = list(f.path()).unwrap();
        assert!(tags.is_empty());
    }

    // ------------------------------------------------------------------
    // add
    // ------------------------------------------------------------------

    #[test]
    fn add_appends_new_tags() {
        let f = make_bundle(&["rust"]);
        let result = add(f.path(), &["async".to_string(), "tokio".to_string()]).unwrap();
        assert_eq!(result, vec!["rust", "async", "tokio"]);

        // Persisted on disk.
        let on_disk = list(f.path()).unwrap();
        assert_eq!(on_disk, vec!["rust", "async", "tokio"]);
    }

    #[test]
    fn add_skips_duplicates() {
        let f = make_bundle(&["rust"]);
        let result = add(f.path(), &["rust".to_string(), "async".to_string()]).unwrap();
        // "rust" should appear only once.
        assert_eq!(result, vec!["rust", "async"]);
    }

    #[test]
    fn add_to_bundle_with_no_tags_field() {
        let f = make_bundle_no_tags();
        let result = add(f.path(), &["new-tag".to_string()]).unwrap();
        assert_eq!(result, vec!["new-tag"]);
    }

    #[test]
    fn add_empty_slice_is_noop() {
        let f = make_bundle(&["existing"]);
        let result = add(f.path(), &[]).unwrap();
        assert_eq!(result, vec!["existing"]);
    }

    // ------------------------------------------------------------------
    // remove
    // ------------------------------------------------------------------

    #[test]
    fn remove_deletes_specified_tags() {
        let f = make_bundle(&["rust", "async", "tokio"]);
        let result = remove(f.path(), &["async".to_string()]).unwrap();
        assert_eq!(result, vec!["rust", "tokio"]);

        let on_disk = list(f.path()).unwrap();
        assert_eq!(on_disk, vec!["rust", "tokio"]);
    }

    #[test]
    fn remove_ignores_absent_tags() {
        let f = make_bundle(&["rust"]);
        let result = remove(f.path(), &["nonexistent".to_string()]).unwrap();
        assert_eq!(result, vec!["rust"]);
    }

    #[test]
    fn remove_all_tags_leaves_empty_array() {
        let f = make_bundle(&["only"]);
        let result = remove(f.path(), &["only".to_string()]).unwrap();
        assert!(result.is_empty());
    }

    // ------------------------------------------------------------------
    // tags_from_value / set_tags_on_value (pure helpers)
    // ------------------------------------------------------------------

    #[test]
    fn tags_from_value_ignores_non_string_entries() {
        let v = serde_json::json!({ "tags": ["good", 42, null, "also-good"] });
        let tags = tags_from_value(&v);
        assert_eq!(tags, vec!["good", "also-good"]);
    }

    #[test]
    fn set_tags_on_value_errors_on_non_object() {
        let mut v = serde_json::Value::Array(vec![]);
        let err = set_tags_on_value(&mut v, vec!["x".into()], Path::new("fake.json"));
        assert!(matches!(err, Err(TagError::NotAnObject { .. })));
    }

    // ------------------------------------------------------------------
    // search_dir
    // ------------------------------------------------------------------

    #[test]
    fn search_dir_finds_matching_bundles() {
        let dir = tempfile::tempdir().unwrap();
        // Write two .okf.json files and one plain .json file.
        let a_path = dir.path().join("a.okf.json");
        let b_path = dir.path().join("b.okf.json");
        let c_path = dir.path().join("c.json"); // should be ignored

        let a = serde_json::json!({"okf":"1.0","source_id":"a","entities":[],"provenance":{"corpus":"t","source_id":"a"},"tags":["alpha","shared"]});
        let b = serde_json::json!({"okf":"1.0","source_id":"b","entities":[],"provenance":{"corpus":"t","source_id":"b"},"tags":["shared"]});
        let c = serde_json::json!({"tags":["shared"]});

        std::fs::write(&a_path, serde_json::to_string_pretty(&a).unwrap()).unwrap();
        std::fs::write(&b_path, serde_json::to_string_pretty(&b).unwrap()).unwrap();
        std::fs::write(&c_path, serde_json::to_string_pretty(&c).unwrap()).unwrap();

        let mut found = search_dir(dir.path(), "shared").unwrap();
        found.sort();
        assert_eq!(found.len(), 2);
        assert!(found.contains(&a_path));
        assert!(found.contains(&b_path));
    }

    #[test]
    fn search_dir_returns_empty_when_no_match() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("only.okf.json");
        let v = serde_json::json!({"okf":"1.0","source_id":"x","entities":[],"provenance":{"corpus":"t","source_id":"x"},"tags":["other"]});
        std::fs::write(&p, serde_json::to_string_pretty(&v).unwrap()).unwrap();

        let found = search_dir(dir.path(), "missing").unwrap();
        assert!(found.is_empty());
    }
}
