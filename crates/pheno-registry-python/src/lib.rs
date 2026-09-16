use pyo3::prelude::*;

use phenotype_registry::ecosystem::{self, ParseError, RepoEntry};

/// A single repository entry extracted from the ecosystem map.
#[pyclass]
#[derive(Debug, Clone)]
struct RepoEntryPy {
    /// Repository name (e.g. `"phenotype-registry"`).
    #[pyo3(get)]
    name: String,
    /// Role classification (e.g. `"shared-lib"`, `"SDK"`, `"tooling"`).
    #[pyo3(get)]
    role: String,
    /// Primary programming language, when known.
    #[pyo3(get)]
    language: Option<String>,
    /// Lifecycle status (e.g. `"Active"`, `"Archived"`, `"CANONICAL"`).
    #[pyo3(get)]
    status: Option<String>,
    /// Free-form notes attached to the row.
    #[pyo3(get)]
    notes: Option<String>,
    /// Names of repositories this one depends on.
    #[pyo3(get)]
    dependencies: Vec<String>,
}

#[pymethods]
impl RepoEntryPy {
    /// Return a dictionary representation of the entry.
    fn to_dict(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("name", &self.name)?;
            dict.set_item("role", &self.role)?;
            dict.set_item("language", &self.language)?;
            dict.set_item("status", &self.status)?;
            dict.set_item("notes", &self.notes)?;
            dict.set_item("dependencies", &self.dependencies)?;
            Ok(dict.into())
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "RepoEntryPy(name={:?}, role={:?}, language={:?}, status={:?}, notes={:?}, dependencies={:?})",
            self.name, self.role, self.language, self.status, self.notes, self.dependencies
        )
    }

    fn __str__(&self) -> String {
        format!(
            "RepoEntry({name}, role={role})",
            name = self.name,
            role = self.role
        )
    }
}

impl From<RepoEntry> for RepoEntryPy {
    fn from(entry: RepoEntry) -> Self {
        RepoEntryPy {
            name: entry.name,
            role: entry.role,
            language: entry.language,
            status: entry.status,
            notes: entry.notes,
            dependencies: entry.dependencies,
        }
    }
}

/// Parse an ecosystem map markdown document and return a list of RepoEntryPy objects.
///
/// The function takes a markdown string and parses role classification tables,
/// triage tables, cluster tables, and dependency adjacency lists into a
/// deduplicated list of repository entries.
///
/// Raises:
///     ValueError: If the input is empty or contains malformed tables.
#[pyfunction]
fn parse_ecosystem_map_py(input: &str) -> PyResult<Vec<RepoEntryPy>> {
    match ecosystem::parse_ecosystem_map(input) {
        Ok(entries) => Ok(entries.into_iter().map(RepoEntryPy::from).collect()),
        Err(ParseError::EmptyInput) => {
            Err(pyo3::exceptions::PyValueError::new_err("input is empty"))
        }
        Err(ParseError::MalformedTable { line, detail }) => Err(
            pyo3::exceptions::PyValueError::new_err(format!(
                "malformed table at line {line}: {detail}"
            )),
        ),
    }
}

/// A Python module implemented in Rust for the phenotype-registry Python SDK.
#[pymodule]
fn pheno_registry_python(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<RepoEntryPy>()?;
    m.add_wrapped(wrap_pyfunction!(parse_ecosystem_map_py))?;
    Ok(())
}
