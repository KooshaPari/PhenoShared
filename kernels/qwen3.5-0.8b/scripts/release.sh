#!/usr/bin/env bash
# release.sh — version-tag-and-push helper for the Qwen3.5 0.8B kernel suite.
#
# Usage:
#   bash scripts/release.sh                  # auto-bump patch (v0.1.0 → v0.1.1)
#   bash scripts/release.sh v0.2.0           # explicit tag
#   bash scripts/release.sh --dry-run v0.2.0 # print what would happen
#
# Steps performed:
#   1. Run scripts/build_all.sh to confirm a clean build before tagging.
#   2. Read the current version out of arch.yaml (`arch.yaml:71` style),
#      or take it from the CLI argument.  If the CLI arg is missing,
#      auto-bump the patch component (v0.1.0 → v0.1.1).
#   3. Write the new version back into arch.yaml as a `version:` field at
#      the top of the file.  Idempotent: only rewrites if changed.
#   4. `git add -A && git commit -m "release: qwen3.5-0.8b-kernels $TAG"`
#      (skipped if --dry-run).
#   5. `git tag -a qwen3.5-0.8b-kernels-$TAG -m "<message>"`
#   6. `git push origin qwen3.5-0.8b-kernels-$TAG`
#   7. Print the next-step `gh release create …` command for the operator
#      to run interactively (so release notes / binaries can be reviewed).
#
# Pre-requisites:
#   * On the `main` branch with a clean working tree (we commit any
#     build-all output but warn about other dirty files).
#   * `gh` CLI authenticated, `origin` pointing at
#     git@github.com:<REDACTED>/pheno-harness.git.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${KERNEL_DIR}/../.." && pwd)"
ARCH_YAML="${KERNEL_DIR}/arch.yaml"

TAG_PREFIX="qwen3.5-0.8b-kernels"

log()  { printf "[release] %s\n" "$*" >&2; }
fail() { printf "[release] ERROR: %s\n" "$*" >&2; exit 1; }

DRY_RUN=0
CLI_TAG=""

# ---------------------------------------------------------------------------
# Argument parsing.
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            sed -n '2,20p' "$0"
            exit 0
            ;;
        v*)
            CLI_TAG="$1"
            shift
            ;;
        *)
            fail "unknown argument: $1 (use --help)"
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Resolve the target tag.
# ---------------------------------------------------------------------------

# Extract the current version from arch.yaml.  Accept both `version: v0.1.0`
# and `version: 0.1.0` styles, falling back to v0.1.0 if no version field
# is present (this matches the freshly-merged state of the repo).
current_version() {
    if [[ -f "${ARCH_YAML}" ]]; then
        local v
        v=$(grep -E '^[[:space:]]*version[[:space:]]*:' "${ARCH_YAML}" \
            | head -n1 \
            | sed -E 's/^[[:space:]]*version[[:space:]]*:[[:space:]]*"?v?([0-9]+\.[0-9]+\.[0-9]+)"?[[:space:]]*$/\1/' \
            || true)
        if [[ -n "${v}" ]]; then
            echo "v${v}"
            return
        fi
    fi
    echo "v0.1.0"
}

bump_patch() {
    local v="$1"
    local stripped="${v#v}"
    local major minor patch
    IFS='.' read -r major minor patch <<<"${stripped}"
    if [[ -z "${patch:-}" ]]; then
        fail "cannot bump non-semver tag: $v"
    fi
    echo "v${major}.${minor}.$((patch + 1))"
}

if [[ -n "${CLI_TAG}" ]]; then
    TARGET="${CLI_TAG}"
    # Normalize: accept "0.2.0" or "v0.2.0".
    [[ "${TARGET}" == v* ]] || TARGET="v${TARGET}"
else
    TARGET="$(bump_patch "$(current_version)")"
fi

log "target tag: ${TAG_PREFIX}-${TARGET}"

# ---------------------------------------------------------------------------
# Dry-run early-exit.
# ---------------------------------------------------------------------------

if [[ "${DRY_RUN}" == "1" ]]; then
    log "(dry-run) would run: scripts/build_all.sh"
    log "(dry-run) would write version: ${TARGET} into ${ARCH_YAML}"
    log "(dry-run) would commit + tag ${TAG_PREFIX}-${TARGET}"
    log "(dry-run) would push tag to origin"
    exit 0
fi

# ---------------------------------------------------------------------------
# Pre-flight: clean tree on main, build runs clean.
# ---------------------------------------------------------------------------

cd "${REPO_ROOT}"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${current_branch}" != "main" ]]; then
    log "warning: you are on branch '${current_branch}', not 'main'."
    log "         tag-and-push will still work but consider switching to main first."
fi

if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    log "working tree is dirty — release.sh will only commit version-line changes."
    git status --porcelain
fi

# ---------------------------------------------------------------------------
# Step 1 — build (best-effort; kernel-only artefacts are gitignored, so
# this does not dirty the tree beyond arch.yaml + build_all output).
# ---------------------------------------------------------------------------

log "step 1/4 — running scripts/build_all.sh"
bash "${KERNEL_DIR}/scripts/build_all.sh"

# ---------------------------------------------------------------------------
# Step 2 — write the new version into arch.yaml (idempotent).
# ---------------------------------------------------------------------------

log "step 2/4 — updating arch.yaml version to ${TARGET}"

python3 - "${ARCH_YAML}" "${TARGET}" <<'PY'
import re, sys
path, tag = sys.argv[1], sys.argv[2]
# tag is "v0.2.0"; strip the leading "v" for storage.
stored = tag.lstrip("v")
text = open(path).read()
new_version_line = f'version: "v{stored}"  # managed by scripts/release.sh'
m = re.search(r'^(\s*)version\s*:\s*"?v?[\d.]+"?\s*(#.*)?$', text, re.MULTILINE)
if m is None:
    # Insert at top after the first comment block / blank line.
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip() == "" and i > 0:
            insert_at = i + 1
            break
    lines.insert(insert_at, new_version_line)
    text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
elif m.group(0).strip() != new_version_line.split("  #")[0].strip():
    text = text[:m.start()] + new_version_line + text[m.end():]
# else: already correct, no rewrite.
open(path, "w").write(text)
print(f"  arch.yaml version: {stored}", flush=True)
PY

# ---------------------------------------------------------------------------
# Step 3 — commit + tag.
# ---------------------------------------------------------------------------

log "step 3/4 — committing version bump and tagging"
git add "${ARCH_YAML}"
git commit -m "release: qwen3.5-0.8b-kernels ${TARGET}" || \
    log "  (no commit needed — version was already ${TARGET})"

git tag -a "${TAG_PREFIX}-${TARGET}" \
    -m "Qwen3.5 0.8B kernel suite — ${TARGET}

Generated by scripts/release.sh.  See:
  * arch.yaml                       — single source of truth
  * kernels/qwen3.5-0.8b/docs/      — README, PERFORMANCE, CONTRIBUTING
  * .github/workflows/kernels.yml   — CI pipeline
"

# ---------------------------------------------------------------------------
# Step 4 — push the tag (not the branch — branch pushes are operator-driven).
# ---------------------------------------------------------------------------

log "step 4/4 — pushing tag to origin"
git push origin "${TAG_PREFIX}-${TARGET}"

# ---------------------------------------------------------------------------
# Next steps.
# ---------------------------------------------------------------------------

cat <<NEXT

[release] DONE — tag ${TAG_PREFIX}-${TARGET} is now on origin.

Next steps (operator-run, interactive):

    # 1. Verify the tag landed on GitHub.
    git ls-remote --tags origin | grep "${TAG_PREFIX}-${TARGET}"

    # 2. Create a GitHub Release.  Attach the kernels.metallib and
    #    libpheno_qwen.dylib artifacts uploaded by the CI run for the
    #    commit that the tag points at:
    gh release create "${TAG_PREFIX}-${TARGET}" \\
        --title "qwen3.5-0.8b-kernels ${TARGET}" \\
        --notes-file - <<'NOTES'
## Qwen3.5 0.8B kernel suite — ${TARGET}

Apple-Silicon-only release of the hand-tuned Metal MSL + polyglot host
bindings for \`Qwen/Qwen3.5-0.8B\`.

### Artifacts
- \`kernels.metallib\` (this CI run)
- \`libpheno_qwen.dylib\` (this CI run)

### Reproducing locally
\`\`\`bash
git checkout ${TAG_PREFIX}-${TARGET}
bash kernels/qwen3.5-0.8b/scripts/build_all.sh
\`\`\`

### Validating
\`\`\`bash
python3 -m pytest tests/ -v
python3 kernels/qwen3.5-0.8b/python/validate.py --quick
\`\`\`
NOTES

NEXT

exit 0