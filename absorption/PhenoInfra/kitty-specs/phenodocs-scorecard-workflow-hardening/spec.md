# phenodocs Scorecard workflow hardening

Remediate open OpenSSF Scorecard TokenPermissionsID code-scanning alerts by moving required GitHub token write scopes from top-level workflow permissions to job-level permissions and by removing unnecessary write scopes.

Scope is limited to phenodocs GitHub Actions workflow files, directly mapped Scorecard
dependency cleanup, and validation with actionlint or equivalent workflow checks.
