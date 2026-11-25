//! `ptx wrap` — wraps an arbitrary subcommand invocation so the orchestration
//! layer can detect drift between the local binary and the pinned version
//! recorded in `PTX.lock`.

use crate::PtxError;

/// Canonical location of the lockfile relative to the workspace root.
pub const LOCKFILE_PATH: &str = "PTX.lock";

/// A single pinned dependency: (crate-name, expected-version-string).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PinnedCrate {
    /// Name of the pinned crate (matches the Cargo workspace member name).
    pub name: String,
    /// Exact version string the lockfile asserts is currently shipping.
    pub version: String,
}

/// In-memory representation of `PTX.lock`. Callers read this before
/// spawning a wrapped subcommand.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Lockfile {
    /// Ordered list of `[name, version]` pairs read from the lockfile.
    pub pinned: Vec<PinnedCrate>,
}

/// Read `PTX.lock` from `root`. Parse the simple key=value format.
/// Returns `Ok(Lockfile::default())` if the file is missing (treated as
/// "no constraints").
///
/// # Errors
/// - `PtxError::Io` when the file exists but cannot be read.
/// - `PtxError::Parse` for syntax errors (other than missing file).
pub fn read_lockfile(root: &std::path::Path) -> Result<Lockfile, PtxError> {
    let path = root.join(LOCKFILE_PATH);
    let body = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Lockfile::default()),
        Err(e) => {
            return Err(PtxError::Io {
                path: path.clone(),
                source: e,
            });
        }
    };
    let mut pinned = Vec::new();
    for (i, raw) in body.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut parts = line.splitn(2, '=');
        let name = parts
            .next()
            .ok_or_else(|| PtxError::Parse(format!("line {}: missing key", i + 1)))?
            .trim()
            .to_string();
        let version = parts
            .next()
            .ok_or_else(|| PtxError::Parse(format!("line {}: missing value", i + 1)))?
            .trim()
            .to_string();
        if name.is_empty() || version.is_empty() {
            return Err(PtxError::Parse(format!(
                "line {}: empty key or value",
                i + 1
            )));
        }
        pinned.push(PinnedCrate { name, version });
    }
    Ok(Lockfile { pinned })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_lockfile_is_empty_not_error() {
        let dir = tempdir();
        let lf = read_lockfile(dir.path()).expect("missing is Ok");
        assert!(lf.pinned.is_empty());
    }

    #[test]
    fn parses_key_value_lines() {
        let dir = tempdir();
        std::fs::write(
            dir.path().join(LOCKFILE_PATH),
            "# ptx lockfile\nphenotype-cli = 0.1.0\nphenotype-diff = 0.1.1\n\n",
        )
        .unwrap();
        let lf = read_lockfile(dir.path()).expect("parses");
        assert_eq!(lf.pinned.len(), 2);
        assert_eq!(lf.pinned[0].name, "phenotype-cli");
        assert_eq!(lf.pinned[1].version, "0.1.1");
    }

    #[test]
    fn malformed_line_returns_parse_error() {
        let dir = tempdir();
        std::fs::write(dir.path().join(LOCKFILE_PATH), "no-equals-sign\n").unwrap();
        assert!(matches!(read_lockfile(dir.path()), Err(PtxError::Parse(_))));
    }

    fn tempdir() -> tempfile::TempDir {
        tempfile::tempdir().expect("tempdir")
    }
}
