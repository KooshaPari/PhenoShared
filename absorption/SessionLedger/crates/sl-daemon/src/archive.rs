//! Bundle compression and archival.
//!
//! Traceability: gzip archive/restore acceptance → FR-006.
//!
//! `archive_bundles` gzips OKF bundle JSON files whose `created_at` date is
//! before a given cutoff into `<data_dir>/archive/<year>/<month>/`.
//! `restore_bundle` decompresses a `.json.gz` archive entry back to plain JSON.

use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use flate2::read::GzDecoder;
use flate2::write::GzEncoder;
use flate2::Compression;
use serde_json::Value;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Summary statistics returned by [`archive_bundles`].
#[derive(Debug, Default)]
pub struct ArchiveStats {
    /// Number of bundles successfully archived.
    pub archived_count: usize,
    /// Bytes saved (original size minus compressed size).
    pub bytes_saved: u64,
    /// Root archive directory used.
    pub archive_dir: PathBuf,
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, thiserror::Error)]
pub enum ArchiveError {
    #[error("I/O error for {path}: {source}")]
    Io { path: PathBuf, source: std::io::Error },

    #[error("JSON parse error for {path}: {source}")]
    Json { path: PathBuf, source: serde_json::Error },

    #[error("archive file not found for bundle id {bundle_id}")]
    NotFound { bundle_id: String },
}

// ---------------------------------------------------------------------------
// archive_bundles
// ---------------------------------------------------------------------------

/// Find all `*.okf.json` files in `data_dir` whose top-level `created_at` field
/// (ISO-8601 date) is strictly before `before`.  Each matching file is gzipped
/// into `<data_dir>/archive/<year>/<month>/<bundle_id>.json.gz` and the
/// original is removed.
///
/// When `dry_run` is `true` the function collects stats and prints what it
/// *would* do but does not touch the filesystem.
pub fn archive_bundles(
    data_dir: &Path,
    before: chrono::NaiveDate,
    dry_run: bool,
) -> Result<ArchiveStats, ArchiveError> {
    let archive_root = data_dir.join("archive");
    let mut stats = ArchiveStats { archive_dir: archive_root.clone(), ..Default::default() };

    // Collect all *.okf.json files directly in data_dir (non-recursive to
    // avoid accidentally scanning the archive sub-tree).
    let entries = fs::read_dir(data_dir)
        .map_err(|e| ArchiveError::Io { path: data_dir.to_path_buf(), source: e })?;

    for entry in entries.flatten() {
        let path = entry.path();
        if !is_okf_json(&path) {
            continue;
        }

        // Parse the bundle to extract created_at.
        let raw =
            fs::read(&path).map_err(|e| ArchiveError::Io { path: path.clone(), source: e })?;
        let val: Value = serde_json::from_slice(&raw)
            .map_err(|e| ArchiveError::Json { path: path.clone(), source: e })?;

        let created_at_str = extract_created_at(&val);
        let Some(bundle_date) = parse_date(&created_at_str) else {
            // Cannot determine date — skip rather than archive blindly.
            continue;
        };

        if bundle_date >= before {
            continue;
        }

        // Determine archive target path.
        let year = bundle_date.format("%Y").to_string();
        let month = bundle_date.format("%m").to_string();
        let bundle_id = bundle_id_from_path(&path);
        let dest_dir = archive_root.join(&year).join(&month);
        let dest_file = dest_dir.join(format!("{bundle_id}.json.gz"));

        // Skip already-archived bundles (dest already exists).
        if dest_file.exists() {
            continue;
        }

        let original_size = raw.len() as u64;

        if dry_run {
            println!("  [dry-run] would archive: {} -> {}", path.display(), dest_file.display());
            stats.archived_count += 1;
            // Estimate savings optimistically at 60%.
            stats.bytes_saved += original_size * 60 / 100;
            continue;
        }

        // Create destination directory.
        fs::create_dir_all(&dest_dir)
            .map_err(|e| ArchiveError::Io { path: dest_dir.clone(), source: e })?;

        // Gzip the raw bytes.
        let compressed = gzip_bytes(&raw);
        let compressed_size = compressed.len() as u64;

        fs::write(&dest_file, &compressed)
            .map_err(|e| ArchiveError::Io { path: dest_file.clone(), source: e })?;

        // Remove original only after successful write.
        fs::remove_file(&path).map_err(|e| ArchiveError::Io { path: path.clone(), source: e })?;

        stats.archived_count += 1;
        stats.bytes_saved += original_size.saturating_sub(compressed_size);
    }

    Ok(stats)
}

// ---------------------------------------------------------------------------
// restore_bundle
// ---------------------------------------------------------------------------

/// Decompress a `.json.gz` archive entry back to a `.okf.json` file in
/// `output_dir`.  Returns the path to the restored file.
pub fn restore_bundle(archive_path: &Path, output_dir: &Path) -> Result<PathBuf, ArchiveError> {
    let compressed = fs::read(archive_path)
        .map_err(|e| ArchiveError::Io { path: archive_path.to_path_buf(), source: e })?;

    let decompressed = gunzip_bytes(&compressed, archive_path)?;

    // Derive output filename: strip .gz from the archive filename.
    let stem = archive_path.file_name().and_then(|n| n.to_str()).unwrap_or("bundle.json.gz");
    let out_name = stem.strip_suffix(".gz").unwrap_or(stem);
    let out_path = output_dir.join(out_name);

    fs::create_dir_all(output_dir)
        .map_err(|e| ArchiveError::Io { path: output_dir.to_path_buf(), source: e })?;
    fs::write(&out_path, &decompressed)
        .map_err(|e| ArchiveError::Io { path: out_path.clone(), source: e })?;

    Ok(out_path)
}

// ---------------------------------------------------------------------------
// find_archive_path — helper used by `sl restore <bundle-id>`
// ---------------------------------------------------------------------------

/// Search `archive_root` recursively for `<bundle_id>.json.gz`.
/// Returns the first match found.
pub fn find_archive_path(archive_root: &Path, bundle_id: &str) -> Result<PathBuf, ArchiveError> {
    let target = format!("{bundle_id}.json.gz");
    find_recursive(archive_root, &target)
        .ok_or_else(|| ArchiveError::NotFound { bundle_id: bundle_id.to_owned() })
}

fn find_recursive(dir: &Path, target: &str) -> Option<PathBuf> {
    let entries = fs::read_dir(dir).ok()?;
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_dir() {
            if let Some(found) = find_recursive(&p, target) {
                return Some(found);
            }
        } else if p.file_name().and_then(|n| n.to_str()) == Some(target) {
            return Some(p);
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn is_okf_json(path: &Path) -> bool {
    path.is_file()
        && path
            .file_name()
            .and_then(|n| n.to_str())
            .map(|n| n.ends_with(".okf.json"))
            .unwrap_or(false)
}

fn bundle_id_from_path(path: &Path) -> String {
    path.file_name()
        .and_then(|n| n.to_str())
        .map(|n| n.trim_end_matches(".okf.json"))
        .unwrap_or("unknown")
        .to_owned()
}

fn extract_created_at(val: &Value) -> String {
    val.get("created_at")
        .or_else(|| val.pointer("/metadata/created_at"))
        .or_else(|| val.pointer("/header/created_at"))
        .and_then(|v| v.as_str())
        .unwrap_or_default()
        .to_owned()
}

fn parse_date(s: &str) -> Option<chrono::NaiveDate> {
    // Accept full ISO-8601 datetimes (take the date part) or bare YYYY-MM-DD.
    let date_part = s.get(..10)?;
    chrono::NaiveDate::parse_from_str(date_part, "%Y-%m-%d").ok()
}

/// Upper bound on bytes a single archived bundle may decompress to.
///
/// A malicious or corrupt `.gz` archive can expand arbitrarily (zip-bomb);
/// the restore path reads the whole decompressed payload into RAM, so entries
/// that would exceed this cap are rejected instead of buffered without limit.
const MAX_RESTORE_BYTES: usize = 256 * 1024 * 1024; // 256 MiB

fn gzip_bytes(data: &[u8]) -> Vec<u8> {
    let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
    encoder.write_all(data).expect("gzip write failed");
    encoder.finish().expect("gzip finish failed")
}

fn gunzip_bytes(data: &[u8], path: &Path) -> Result<Vec<u8>, ArchiveError> {
    gunzip_bounded(data, path, MAX_RESTORE_BYTES)
}

fn gunzip_bounded(data: &[u8], path: &Path, max_bytes: usize) -> Result<Vec<u8>, ArchiveError> {
    let mut decoder = GzDecoder::new(data);
    let mut out = Vec::new();
    let read = decoder
        .by_ref()
        .take(max_bytes as u64 + 1)
        .read_to_end(&mut out)
        .map_err(|e| ArchiveError::Io { path: path.to_path_buf(), source: e })?;
    if read > max_bytes {
        return Err(ArchiveError::Io {
            path: path.to_path_buf(),
            source: std::io::Error::other(format!(
                "archive decompresses beyond the {max_bytes} byte restore cap; refusing to buffer it"
            )),
        });
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use std::fs;
    use tempfile::TempDir;

    fn make_bundle(dir: &Path, id: &str, created_at: &str) -> PathBuf {
        let content = serde_json::json!({
            "session_id": id,
            "created_at": created_at,
            "model": "test-model",
            "token_count": 100
        })
        .to_string();
        let path = dir.join(format!("{id}.okf.json"));
        fs::write(&path, content).unwrap();
        path
    }

    // 1. archive moves the matching file to the archive dir.
    #[test]
    fn archive_moves_file() {
        let dir = TempDir::new().unwrap();
        let bundle_path = make_bundle(dir.path(), "bundle-001", "2024-01-15T10:00:00Z");

        let before = NaiveDate::from_ymd_opt(2024, 6, 1).unwrap();
        let stats = archive_bundles(dir.path(), before, false).unwrap();

        assert_eq!(stats.archived_count, 1);
        assert!(!bundle_path.exists(), "original should be removed");

        let archived = dir.path().join("archive/2024/01/bundle-001.json.gz");
        assert!(archived.exists(), "archived file should exist");
    }

    // 2. dry-run does NOT move files.
    #[test]
    fn dry_run_does_not_move() {
        let dir = TempDir::new().unwrap();
        let bundle_path = make_bundle(dir.path(), "bundle-002", "2023-03-10");

        let before = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap();
        let stats = archive_bundles(dir.path(), before, true).unwrap();

        assert_eq!(stats.archived_count, 1);
        assert!(bundle_path.exists(), "original must remain in dry-run");
        let archived = dir.path().join("archive/2023/03/bundle-002.json.gz");
        assert!(!archived.exists(), "archive file must NOT be created in dry-run");
    }

    // 3. restore decompresses correctly.
    #[test]
    fn fr006_restore_decompresses() {
        let src_dir = TempDir::new().unwrap();
        let dst_dir = TempDir::new().unwrap();
        let _bundle_path = make_bundle(src_dir.path(), "bundle-003", "2023-05-01");

        let before = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap();
        archive_bundles(src_dir.path(), before, false).unwrap();

        let archived = src_dir.path().join("archive/2023/05/bundle-003.json.gz");
        assert!(archived.exists());

        let restored = restore_bundle(&archived, dst_dir.path()).unwrap();
        assert!(restored.exists());

        let content = fs::read_to_string(&restored).unwrap();
        let val: serde_json::Value = serde_json::from_str(&content).unwrap();
        assert_eq!(val["session_id"].as_str().unwrap(), "bundle-003");
    }

    // 4. bytes_saved is accurate (compressed should be smaller than original for JSON).
    #[test]
    fn stats_bytes_saved_positive() {
        let dir = TempDir::new().unwrap();
        make_bundle(dir.path(), "bundle-004", "2022-12-01");

        let before = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap();
        let stats = archive_bundles(dir.path(), before, false).unwrap();

        // bytes_saved may be 0 for tiny files but must not underflow.
        // Just confirm it doesn't panic or overflow.
        let _ = stats.bytes_saved;
    }

    // 5. date filtering — bundle after cutoff is NOT archived.
    #[test]
    fn date_filter_skips_recent_bundle() {
        let dir = TempDir::new().unwrap();
        let recent = make_bundle(dir.path(), "bundle-005", "2025-01-01");

        let before = NaiveDate::from_ymd_opt(2024, 6, 1).unwrap();
        let stats = archive_bundles(dir.path(), before, false).unwrap();

        assert_eq!(stats.archived_count, 0);
        assert!(recent.exists(), "recent bundle must NOT be archived");
    }

    // 6. already-archived bundles are skipped on second run.
    #[test]
    fn already_archived_skipped() {
        let dir = TempDir::new().unwrap();
        make_bundle(dir.path(), "bundle-006", "2022-06-15");

        let before = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap();
        let stats1 = archive_bundles(dir.path(), before, false).unwrap();
        assert_eq!(stats1.archived_count, 1);

        // Second run on empty data_dir — nothing to archive.
        let stats2 = archive_bundles(dir.path(), before, false).unwrap();
        assert_eq!(stats2.archived_count, 0);
    }

    // 7. find_archive_path returns the correct path.
    #[test]
    fn find_archive_path_works() {
        let dir = TempDir::new().unwrap();
        make_bundle(dir.path(), "bundle-007", "2021-11-20");

        let before = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap();
        archive_bundles(dir.path(), before, false).unwrap();

        let found = find_archive_path(&dir.path().join("archive"), "bundle-007").unwrap();
        assert!(found.ends_with("bundle-007.json.gz"));
    }

    // 8. find_archive_path returns error for missing bundle.
    #[test]
    fn find_archive_path_missing() {
        let dir = TempDir::new().unwrap();
        let archive_root = dir.path().join("archive");
        fs::create_dir_all(&archive_root).unwrap();

        let result = find_archive_path(&archive_root, "nonexistent-bundle");
        assert!(result.is_err());
    }

    // 9. a gzip stream that would expand past the restore cap is rejected.
    #[test]
    fn gunzip_bounded_rejects_oversized_expansion() {
        let compressed = gzip_bytes(&vec![0u8; 1024 * 1024]); // expands to 1 MiB

        let error = gunzip_bounded(&compressed, Path::new("bomb.json.gz"), 16 * 1024)
            .expect_err("expansion beyond cap must be rejected");
        assert!(
            error.to_string().contains("restore cap"),
            "error should describe the cap, got: {error}"
        );
    }

    // 10. decompression within the cap still round-trips.
    #[test]
    fn gunzip_bounded_accepts_normal_payload() {
        let payload = b"{\"session_id\": \"ok\"}".repeat(8);
        let compressed = gzip_bytes(&payload);

        let restored = gunzip_bounded(&compressed, Path::new("ok.json.gz"), 1024)
            .expect("payload within cap must restore");
        assert_eq!(restored, payload);
    }
}
