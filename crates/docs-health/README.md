# docs-health

Rust CLI that scans a repo for markdown compliance (vale + markdownlint) and
broken intra-repo links. Emits a structured JSON report.

**Replaces:**
- `repos/phenodocs/.airlock/lint.sh`
- `repos/phenodocs/scripts/check_docs_links.py`

**Usage:** `docs-health --path <dir>`
