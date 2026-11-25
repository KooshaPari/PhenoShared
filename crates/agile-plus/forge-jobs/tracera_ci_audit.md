REPO: E:/Dev/Tracera
TASK: Read-only CI audit of Tracera. DO NOT commit anything.

1. List all GitHub Actions workflow files: ls .github/workflows/
2. For each workflow, summarize: name, runs-on, key jobs, any obvious issues
3. Check if phenoShared sibling is needed (grep Cargo.toml for phenotype-error-core or phenotype-logging)
4. List all branches: git branch -a | head -20
5. Check what branches exist beyond main: git log --oneline -5 per branch if <5 branches total
6. Identify any Rust compile blockers: grep -rn "mod " crates/*/src/lib.rs | head -20 (check for missing file references)
7. Check cargo audit status: cat audit.toml 2>/dev/null || echo "NO audit.toml"
8. Write findings to: /tmp/tracera-ci-audit-2026-06-15.md

Report all findings.
