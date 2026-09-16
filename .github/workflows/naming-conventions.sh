#!/usr/bin/env bash
# .github/workflows/naming-conventions.sh
# Called by .github/workflows/naming-conventions.yml on every PR touching
# registry.yaml / disposition-index.json. Enforces the 3 approved naming
# patterns from operating-contract S13:
#   pheno-<word>          (lowercase, kebab)
#   Pheno<Word>           (PascalCase, single token)
#   phenotype-<word>      (lowercase, kebab, full prefix)
#
# Only flags repos that contain "pheno" (case-insensitive) but do NOT match
# any of the 3 approved patterns. Unrelated repos (e.g. Grapheon, OmniRoute)
# are ignored entirely.
set -euo pipefail

ORG="${ORG:-KooshaPari}"
APPROVED_PATTERNS=(
  '^pheno-[a-z][a-z0-9-]*$'           # pheno-short:  pheno-harness, pheno-tracing
  '^Pheno[A-Z][a-zA-Z0-9]*$'          # PhenoPascal:  PhenoCompose, PhenoContracts
  '^phenotype-[a-z][a-z0-9-]*$'       # phenotype-full: phenotype-router, phenotype-org-audits
)
FAIL_FAST="${FAIL_FAST:-false}"

fail_count=0
checked=0
skipped=0
total=0

while IFS=$'\t' read -r name archived; do
  total=$((total + 1))

  # Skip archived repos
  if [ "$archived" = "true" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  # Only check repos that contain "pheno" (case-insensitive)
  # This ignores unrelated repos like Grapheon, OmniRoute, etc.
  if ! echo "$name" | grep -qi 'pheno'; then
    skipped=$((skipped + 1))
    continue
  fi

  checked=$((checked + 1))

  # Check against approved patterns
  matched=0
  for p in "${APPROVED_PATTERNS[@]}"; do
    if [[ "$name" =~ $p ]]; then
      matched=1
      break
    fi
  done

  if [ "$matched" = "0" ]; then
    echo "::error file=naming::Repo '$name' contains 'pheno' but does not match any approved pattern"
    echo "  Approved: pheno-<word>, Pheno<Word>, phenotype-<word>"
    fail_count=$((fail_count + 1))
    if [ "$FAIL_FAST" = "true" ]; then
      exit 1
    fi
  fi
done < <(gh repo list "$ORG" --limit 400 --json name,isArchived \
            --template '{{range .}}{{.name}}{{"\t"}}{{.isArchived}}{{"\n"}}{{end}}')

echo "::notice::checked $checked phenotype-related repos ($skipped skipped), $fail_count violations"
exit $fail_count
