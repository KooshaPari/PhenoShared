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

# ORG must be provided by the caller (naming-conventions.yml passes the repository
# owner). A literal fallback previously hid the fact that `gh repo list` was querying an
# owner that does not exist, so the gate reported zero violations while checking nothing.
ORG="${ORG:?ORG must be set - naming-conventions.yml passes github.repository_owner}"
APPROVED_PATTERNS=(
  '^pheno-[a-z][a-z0-9-]*$'           # pheno-short:  pheno-harness, pheno-tracing
  '^Pheno[A-Z][a-zA-Z0-9]*$'          # PhenoPascal:  PhenoCompose, PhenoContracts
  '^phenotype-[a-z][a-z0-9-]*$'       # phenotype-full: phenotype-router, phenotype-org-audits
)
FAIL_FAST="${FAIL_FAST:-false}"

# Repos that already existed when this gate was switched back on (2026-11-28). The gate
# had been a no-op since the 2026-09-16 sweep replaced the org name with `<REDACTED>`, so
# these four violations are legacy, not regressions. They are reported on every run and do
# not fail the build; anything NOT in this list does. Remove an entry once the repo is
# renamed or archived, and the gate will start enforcing it.
KNOWN_NONCONFORMING=(
  'PhenoVCS-rb-archive-20261106'
  'PhenoFastMCP-rb-archive-20261106'
  'phenoDesign-visual-production-v2'
  'phenoreg-browser-audit'
)

is_known() {
  local candidate="$1" known
  for known in "${KNOWN_NONCONFORMING[@]}"; do
    [ "$known" = "$candidate" ] && return 0
  done
  return 1
}

fail_count=0
known_count=0
stale_known=0
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
    if is_known "$name"; then
      echo "::notice file=naming::known legacy violation: '$name' (grandfathered, not failing)"
      known_count=$((known_count + 1))
      continue
    fi
    echo "::error file=naming::Repo '$name' contains 'pheno' but does not match any approved pattern"
    echo "  Approved: pheno-<word>, Pheno<Word>, phenotype-<word>"
    fail_count=$((fail_count + 1))
    if [ "$FAIL_FAST" = "true" ]; then
      exit 1
    fi
  fi
done < <(gh repo list "$ORG" --limit 400 --json name,isArchived \
            --template '{{range .}}{{.name}}{{"\t"}}{{.isArchived}}{{"\n"}}{{end}}')

if [ "$total" -eq 0 ]; then
  # A gate that inspected nothing must not report success: `gh repo list` failing on a
  # bad owner used to yield an empty list, fail_count=0, and a green check.
  echo "::error::gh repo list '$ORG' returned no repositories - refusing to pass a check that inspected nothing"
  exit 1
fi

# A grandfather entry that no longer violates is stale; say so rather than let it rot.
for known in "${KNOWN_NONCONFORMING[@]}"; do
  if ! gh repo view "$ORG/$known" --json name >/dev/null 2>&1; then
    echo "::notice file=naming::baseline entry '$known' no longer resolves - remove it from KNOWN_NONCONFORMING"
    stale_known=$((stale_known + 1))
  fi
done

echo "::notice::org $ORG: checked $checked phenotype-related repos ($skipped skipped), $fail_count violations, $known_count known legacy, $stale_known stale baseline entries"
exit $fail_count
