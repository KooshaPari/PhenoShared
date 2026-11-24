# legacy-scan

Rust CLI that enforces the Phenotype-org Scripting Language Hierarchy: flags
shell scripts exceeding the 5-line glue threshold, standalone Python/TS CLIs
that should be Rust, and deprecated library usage.

**Replaces (rubric source):**
- `repos/docs/governance/scripting_policy.md` (rubric lives here; this crate
  mechanizes the PR-review checks)

**Usage:** `legacy-scan --path <dir> [--shell-line-limit 5]`
