#!/usr/bin/env bash
# pre_absorb_gate.sh - prove an absorb was additive, or fail loudly.
#
# WHY THIS EXISTS
# ---------------
# On 2026-11-23/24 this repository's tree was replaced by an absorb and had to be
# restored at least twice. The evidence is in git, not in opinion:
#
#   - the largest commit in history, 9f951e777 (72,993 files), is a REPAIR, 4.7x
#     larger than the biggest real absorb 66c413b73 (57,316 files)
#   - three restore/recover commits exist only to undo tree replacement
#   - six safety branches (preserve/, recover/, snapshot/orphan/) were made by hand
#   - cmd/dagrun needed four separate repair commits after its absorb
#
# The existing tooling (scripts/absorb_private_v2.py, scripts/verify_registry_tree.py)
# proves blob identity against a source. None of it notices that the DESTINATION lost
# thousands of pre-existing files, because that question is about the destination's
# own before/after, not about the source.
#
# An absorb is additive: it adds another repository's content to this one. A tree
# REPLACEMENT is the same operation with the destination's files thrown away. Both
# look like "a big commit full of new files". Only the before/after file count
# separates them, so that is what this gate measures.
#
# USAGE
#   scripts/pre_absorb_gate.sh --snapshot [--label TEXT] [--out-dir DIR]
#   scripts/pre_absorb_gate.sh --check [--snapshot-file F | --pre-ref REF]
#                                    [--post-ref REF] [--allow-removals N]
#                                    [--max-removed-percent P] [--require-preserve]
#
# --snapshot  Record HEAD (sha, tree, and a full `git ls-tree -r` manifest) to a
#             timestamped file set, and point `latest` at it. Run this BEFORE the
#             absorb, while the tree is still the good one.
# --check     Compare a pre-absorb manifest against a post-absorb tree and report
#             files added / REMOVED / modified. Fails when the removal count has the
#             shape of a tree replacement.
# --pre-ref   Build the pre side from a ref instead of a stored snapshot. This is the
#             form CI uses: base branch tree vs pull-request head tree.
#
# THRESHOLDS (default)
#   FAIL when removals > 50 files AND removals > 0.5% of the pre-absorb manifest.
#   The conjunction keeps small repos from tripping on a handful of legitimate
#   deletions, and makes a large repo's bulk delete impossible to land unnoticed.
#   --allow-removals N replaces both halves with one explicit absolute allowance:
#   pass only when removals <= N. The allowance is recorded in the report, so an
#   intentional bulk delete is declared rather than inferred.
#
# EXIT CODES (stable; CI and other lanes may branch on them)
#    0  PASS    removals within threshold
#    2  USAGE   bad flag, missing value, unreadable directory
#    3  REPO    not inside a git work tree
#    4  SNAP    snapshot missing, unreadable, or of an unknown shape
#    5  REF     a required ref does not resolve (--post-ref, or --pre-ref)
#    6  EMPTY   the pre-absorb manifest has zero entries; additivity cannot be proven
#   10  REPLACED removals exceed threshold: TREE REPLACEMENT SUSPECTED
#   13  PRESERVE --require-preserve was given and no preserve/ ref matches the pre HEAD
#
# READ-ONLY CONTRACT
#   This script never commits, resets, checks out, stages, fetches or pushes. It runs
#   only read-only git plumbing (rev-parse, ls-tree, for-each-ref, cat-file -e) and
#   GIT_OPTIONAL_LOCKS=0 keeps git from even refreshing the index. It writes only its
#   own report files, under the git common dir by default (`<git-common-dir>/pre-absorb`)
#   so it never pollutes the working tree or another lane's clean-tree assertions.
#
# KNOWN LIMITS (see docs/pre-absorb-gate.md)
#   - It measures the DESTINATION tree only. An absorb that both removes 40 files and
#     silently swaps 4,000 file bodies passes, because modification is reported, not
#     gated. Pair it with the blob-level proofs in scripts/verify_registry_tree.py.
#   - Renames read as one removal plus one addition, which is why the threshold is a
#     ratio and not zero.
#   - Submodule gitlinks are compared by commit sha; a moved submodule pointer counts
#     as one modified entry, not as the files inside it.
#   - It cannot see an absorb that is committed on top of a tree that was ALREADY
#     damaged before the snapshot was taken.
set -euo pipefail

# Do not let git take the index lock just to stat files; this script is read-only.
export GIT_OPTIONAL_LOCKS=0

readonly PROG=${0##*/}
readonly DEFAULT_MAX_REMOVALS=50
readonly DEFAULT_MAX_REMOVED_PERCENT=0.5

readonly EXIT_PASS=0
readonly EXIT_USAGE=2
readonly EXIT_REPO=3
readonly EXIT_SNAP=4
readonly EXIT_REF=5
readonly EXIT_EMPTY=6
readonly EXIT_REPLACED=10
readonly EXIT_PRESERVE=13

die() {
	local code=$1
	shift
	printf '%s: error: %s\n' "${PROG}" "$*" >&2
	exit "${code}"
}

usage() {
	cat <<'EOF'
pre_absorb_gate.sh - prove an absorb was additive, or fail loudly.

  --snapshot                  record HEAD (sha, tree, manifest) before the absorb
  --check                     compare a pre-absorb manifest against a post-absorb tree

snapshot options
  --label TEXT                free-text note stored with the snapshot
  --out-dir DIR               where report files go
                              (default: <git-common-dir>/pre-absorb)

check options
  --snapshot-file FILE        pre-absorb manifest to use
  --pre-ref REF               build the pre side from REF instead of a snapshot
  --post-ref REF              tree to check (default: HEAD)
  --allow-removals N          explicit absolute removal allowance; disables the
                              default ">50 AND >0.5%" rule
  --max-removed-percent P     override the 0.5% half of the default rule
  --require-preserve          exit 13 if no preserve/<branch> ref matches the pre HEAD
                              (the script never creates one; creating it is remote-mutating)

common
  -h, --help                  this text

exit codes: 0 pass, 2 usage, 3 not a repo, 4 snapshot unusable, 5 ref missing,
            6 empty manifest, 10 tree replacement suspected, 13 preserve ref missing

Nothing in this script mutates git state. See docs/pre-absorb-gate.md.
EOF
}

MODE=
OUT_DIR=
LABEL=
SNAPSHOT_FILE=
PRE_REF=
POST_REF=HEAD
ALLOW_REMOVALS=
MAX_REMOVED_PERCENT=${DEFAULT_MAX_REMOVED_PERCENT}
REQUIRE_PRESERVE=0

need_value() {
	# $1 = flag name, $2 = remaining arg count, $3 = value
	[[ ${2:-0} -ge 1 ]] || die "${EXIT_USAGE}" "$1 requires a value"
	[[ -n ${3:-} ]] || die "${EXIT_USAGE}" "$1 requires a non-empty value"
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--snapshot) MODE=snapshot ;;
	--check) MODE=check ;;
	--label)
		need_value "$1" "$(($# - 1))" "${2-}"
		LABEL=$2
		shift
		;;
	--out-dir)
		need_value "$1" "$(($# - 1))" "${2-}"
		OUT_DIR=$2
		shift
		;;
	--snapshot-file)
		need_value "$1" "$(($# - 1))" "${2-}"
		SNAPSHOT_FILE=$2
		shift
		;;
	--pre-ref)
		need_value "$1" "$(($# - 1))" "${2-}"
		PRE_REF=$2
		shift
		;;
	--post-ref)
		need_value "$1" "$(($# - 1))" "${2-}"
		POST_REF=$2
		shift
		;;
	--allow-removals)
		need_value "$1" "$(($# - 1))" "${2-}"
		case "$2" in
		'' | *[!0-9]*) die "${EXIT_USAGE}" "--allow-removals wants a non-negative integer, got '$2'" ;;
		*) ;;
		esac
		ALLOW_REMOVALS=$2
		shift
		;;
	--max-removed-percent)
		need_value "$1" "$(($# - 1))" "${2-}"
		case "$2" in
		*[!0-9.]* | '') die "${EXIT_USAGE}" "--max-removed-percent wants a number, got '$2'" ;;
		*) ;;
		esac
		MAX_REMOVED_PERCENT=$2
		shift
		;;
	--require-preserve) REQUIRE_PRESERVE=1 ;;
	-h | --help)
		usage
		exit 0
		;;
	*) die "${EXIT_USAGE}" "unknown argument '$1' (try --help)" ;;
	esac
	shift
done

[[ -n ${MODE} ]] || {
	usage >&2
	die "${EXIT_USAGE}" "one of --snapshot or --check is required"
}
if [[ ${MODE} == snapshot ]] && { [[ -n ${PRE_REF} ]] || [[ -n ${SNAPSHOT_FILE} ]]; }; then
	die "${EXIT_USAGE}" "--pre-ref/--snapshot-file only apply to --check"
fi

git rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
	die "${EXIT_REPO}" "${PWD} is not inside a git work tree"

REPO_ROOT=$(git rev-parse --show-toplevel)
COMMON_DIR=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null ||
	git rev-parse --git-common-dir)
case "${COMMON_DIR}" in
/*) ;;
*) COMMON_DIR=${REPO_ROOT}/${COMMON_DIR} ;;
esac
[[ -n ${OUT_DIR} ]] || OUT_DIR=${COMMON_DIR}/pre-absorb

STAMP=$(date -u +%Y%m%dT%H%M%SZ)

# write_manifest REF OUTFILE -> prints entry count, exits 5 when REF is unresolvable
write_manifest() {
	local ref=$1 out=$2
	if ! git rev-parse --verify --quiet "${ref}^{tree}" >/dev/null; then
		die "${EXIT_REF}" "ref '${ref}' does not resolve to a tree (unfetched base branch?)"
	fi
	# mode type sha<TAB>path. git C-quotes unusual paths, and a quoted path never
	# contains a literal tab, so splitting on the first tab is unambiguous.
	git ls-tree -r "${ref}" >"${out}"
	wc -l <"${out}" | tr -d ' '
}

# tree_of REF -> tree sha
tree_of() {
	git rev-parse --verify --quiet "$1^{tree}" || die "${EXIT_REF}" "ref '$1' does not resolve"
}

do_snapshot() {
	local head tree count base manifest names meta branch dirty
	head=$(git rev-parse HEAD) || die "${EXIT_REF}" "HEAD does not resolve"
	tree=$(tree_of HEAD)
	# Both values are for the report only; an unreadable name is reported, not fatal.
	branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || branch=unknown
	dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') || dirty=unknown
	base="pre-absorb-${STAMP}-${head:0:12}"
	mkdir -p "${OUT_DIR}" || die "${EXIT_USAGE}" "cannot create '${OUT_DIR}'"

	manifest=${OUT_DIR}/${base}.manifest
	names=${OUT_DIR}/${base}.names
	meta=${OUT_DIR}/${base}.meta

	count=$(write_manifest HEAD "${manifest}")
	git ls-tree -r --name-only HEAD >"${names}"

	if [[ ${count} -eq 0 ]]; then
		die "${EXIT_EMPTY}" "HEAD resolves to an empty tree; a snapshot of nothing cannot prove additivity"
	fi

	{
		printf 'format=pre-absorb-snapshot-v1\n'
		printf 'created_utc=%s\n' "${STAMP}"
		printf 'head_commit=%s\n' "${head}"
		printf 'head_tree=%s\n' "${tree}"
		printf 'branch=%s\n' "${branch}"
		printf 'entries=%s\n' "${count}"
		printf 'dirty_entries=%s\n' "${dirty}"
		printf 'label=%s\n' "${LABEL}"
		printf 'repo_root=%s\n' "${REPO_ROOT}"
		printf 'manifest=%s\n' "${manifest##*/}"
		printf 'names=%s\n' "${names##*/}"
	} >"${meta}"

	printf '%s\n' "${base}" >"${OUT_DIR}/latest"

	echo "snapshot recorded"
	echo "  head          ${head}"
	echo "  tree          ${tree}"
	echo "  branch        ${branch}"
	echo "  entries       ${count}"
	echo "  meta          ${meta}"
	echo "  manifest      ${manifest}"
	echo "  names         ${names}"
	echo "  latest        ${OUT_DIR}/latest"
	if [[ ${dirty} != 0 ]]; then
		echo "  WARN          working tree is dirty; the snapshot covers HEAD only, so"
		echo "                uncommitted work is not part of what this gate protects"
	fi
	echo "PRE_ABSORB_RESULT=SNAPSHOT"
	echo "PRE_ABSORB_FILES_PRE=${count}"
	echo "PRE_ABSORB_EXIT=${EXIT_PASS}"
	exit "${EXIT_PASS}"
}

# resolve_snapshot -> sets PRE_MANIFEST and PRE_META (empty when built from --pre-ref)
resolve_snapshot() {
	local latest meta manifest
	if [[ -n ${SNAPSHOT_FILE} ]]; then
		[[ -f ${SNAPSHOT_FILE} ]] || die "${EXIT_SNAP}" "snapshot file '${SNAPSHOT_FILE}' does not exist"
		PRE_MANIFEST=${SNAPSHOT_FILE}
		PRE_META=
	else
		[[ -d ${OUT_DIR} ]] || die "${EXIT_SNAP}" "no snapshot directory '${OUT_DIR}'; run --snapshot before the absorb"
		latest=${OUT_DIR}/latest
		[[ -f ${latest} ]] || die "${EXIT_SNAP}" "no '${latest}' pointer; name a snapshot with --snapshot-file"
		meta=${OUT_DIR}/$(cat "${latest}").meta
		[[ -f ${meta} ]] || die "${EXIT_SNAP}" "'${latest}' points at a snapshot whose .meta is gone"
		manifest=$(sed -n 's/^manifest=//p' "${meta}")
		[[ -n ${manifest} ]] || die "${EXIT_SNAP}" "'${meta}' does not name a manifest"
		PRE_MANIFEST=${OUT_DIR}/${manifest}
		PRE_META=${meta}
	fi
	[[ -s ${PRE_MANIFEST} ]] || die "${EXIT_EMPTY}" "pre-absorb manifest '${PRE_MANIFEST}' is empty; additivity cannot be proven"
}

# report_preserve HEAD_COMMIT HEAD_TREE -> echoes matching ref, or nothing
report_preserve() {
	local want_commit=$1 want_tree=$2 ref sha ref_tree
	while IFS= read -r ref; do
		[[ -n ${ref} ]] || continue
		sha=$(git rev-parse --verify --quiet "${ref}" || true)
		[[ -n ${sha} ]] || continue
		if [[ ${sha} == "${want_commit}" ]]; then
			printf '%s (same commit)' "${ref}"
			return 0
		fi
		ref_tree=$(git rev-parse --verify --quiet "${ref}^{tree}" 2>/dev/null) || ref_tree=none
		if [[ ${ref_tree} == "${want_tree}" ]]; then
			printf '%s (same tree)' "${ref}"
			return 0
		fi
	done < <(git for-each-ref --format='%(refname)' \
		'refs/heads/preserve/*' 'refs/remotes/*/preserve/*' 2>/dev/null || true)
	return 0
}

do_check() {
	local pre_manifest post_manifest pre_meta pre_commit pre_tree post_commit post_tree
	local report removed_list pre_total post_total added removed modified dirs
	local verdict=pass reason='' threshold_desc='' preserve_ref='' slug

	mkdir -p "${OUT_DIR}" || die "${EXIT_USAGE}" "cannot create '${OUT_DIR}'"

	if [[ -n ${PRE_REF} ]]; then
		slug=$(printf '%s' "${PRE_REF}" | tr -c 'A-Za-z0-9._-' '_')
		pre_manifest=${OUT_DIR}/check-${STAMP}-pre-${slug}.manifest
		write_manifest "${PRE_REF}" "${pre_manifest}" >/dev/null
		pre_commit=$(git rev-parse --verify --quiet "${PRE_REF}" || echo "")
		pre_tree=$(tree_of "${PRE_REF}")
		pre_meta=
	else
		resolve_snapshot
		pre_manifest=${PRE_MANIFEST}
		pre_meta=${PRE_META}
		pre_commit=''
		pre_tree=''
		if [[ -n ${pre_meta} ]] && [[ -f ${pre_meta} ]]; then
			pre_commit=$(sed -n 's/^head_commit=//p' "${pre_meta}")
			pre_tree=$(sed -n 's/^head_tree=//p' "${pre_meta}")
		fi
	fi

	[[ -s ${pre_manifest} ]] || die "${EXIT_EMPTY}" "pre-absorb manifest '${pre_manifest}' is empty"

	post_commit=$(git rev-parse --verify --quiet "${POST_REF}" || echo "")
	[[ -n ${post_commit} ]] || die "${EXIT_REF}" "--post-ref '${POST_REF}' does not resolve"
	post_tree=$(tree_of "${POST_REF}")

	post_manifest=${OUT_DIR}/check-${STAMP}-post-${post_commit:0:12}.manifest
	write_manifest "${POST_REF}" "${post_manifest}" >/dev/null

	local base="check-${STAMP}-${post_commit:0:12}"
	report=${OUT_DIR}/${base}.report
	removed_list=${OUT_DIR}/${base}.removed

	# One pass over both manifests: pre entries on the left, post on the right.
	# The removed list is created empty first, because awk only opens it when it has
	# something to write and a missing file would break the per-directory rollup.
	: >"${removed_list}"
	counts=$(awk -F'\t' -v out="${removed_list}" '
    NR == FNR { pre[$2] = $1; np++; next }
    { post[$2] = $1; nq++ }
    END {
      for (p in post) {
        if (p in pre) { if (pre[p] != post[p]) mod++ } else add++
      }
      for (p in pre) {
        if (!(p in post)) { rem++; print p > out }
      }
      close(out)
      printf "%d %d %d %d %d", np + 0, nq + 0, add + 0, rem + 0, mod + 0
    }' "${pre_manifest}" "${post_manifest}")
	[[ -n ${counts} ]] || die "${EXIT_SNAP}" "manifest comparison produced no counts"
	read -r pre_total post_total added removed modified <<<"${counts}"

	# Where the files went missing from: the actionable half of "which lane replaced
	# the tree". Rolled up by top-level path, then by second-level path for anything
	# deeper, because an absorb's damage concentrates under its own subtree
	# (absorption/<repo>/...) while a whole-tree replacement takes every top-level dir.
	# sed -n '1,Np', not `head`: head closes the pipe early, sort dies of EPIPE and
	# `set -o pipefail` would turn a clean run into an exit before the verdict.
	rollup() {
		local depth=$1
		awk -F/ -v d="${depth}" '{
      if (NF <= d) { print $0 }
      else { out = $1; for (i = 2; i <= d; i++) out = out "/" $i; print out }
    }' "${removed_list}" | sort | uniq -c | sort -rn | sed -n '1,8p' | sed 's/^ *//'
	}
	dirs=$(rollup 1)
	dirs2=$(awk -F/ 'NF > 2 { print $1 "/" $2 }' "${removed_list}" | sort | uniq -c |
		sort -rn | sed -n '1,8p' | sed 's/^ *//')

	log() {
		printf '%s\n' "$*" >>"${report}"
		printf '%s\n' "$*"
	}

	: >"${report}"
	log "# pre-absorb gate report"
	log ""
	log "created_utc    ${STAMP}"
	log "repo           ${REPO_ROOT}"
	log "pre_source     ${pre_meta:-ref:${PRE_REF:-unknown}}"
	log "pre_commit     ${pre_commit:-unknown}"
	log "pre_tree       ${pre_tree:-unknown}"
	log "post_ref       ${POST_REF}"
	log "post_commit    ${post_commit}"
	log "post_tree      ${post_tree}"
	log ""
	log "files_pre      ${pre_total}"
	log "files_post     ${post_total}"
	log "added          ${added}"
	log "REMOVED        ${removed}"
	log "modified       ${modified}"
	log ""

	if [[ -n ${ALLOW_REMOVALS} ]]; then
		threshold_desc="explicit allowance (--allow-removals ${ALLOW_REMOVALS})"
		if [[ ${removed} -gt ${ALLOW_REMOVALS} ]]; then verdict=fail; fi
	else
		threshold_desc="fail if removals > ${DEFAULT_MAX_REMOVALS} AND > ${MAX_REMOVED_PERCENT}% of ${pre_total} (=$(
			awk -v t="${pre_total}" -v p="${MAX_REMOVED_PERCENT}" 'BEGIN { printf "%.2f", t * p / 100 }'
		) files)"
		if awk -v r="${removed}" -v t="${pre_total}" -v p="${MAX_REMOVED_PERCENT}" \
			-v abs="${DEFAULT_MAX_REMOVALS}" 'BEGIN { exit !(r > abs && r * 100 > p * t) }'; then
			verdict=fail
		fi
	fi

	log "threshold      ${threshold_desc}"
	log ""
	log "removed_paths  ${removed_list}"
	if [[ -n ${dirs} ]]; then
		log ""
		log "removed by top-level path (count, path):"
		while IFS= read -r line; do
			log "  ${line}"
		done <<<"${dirs}"
	fi
	if [[ -n ${dirs2} ]]; then
		log ""
		log "removed by second-level path (count, path):"
		while IFS= read -r line; do
			log "  ${line}"
		done <<<"${dirs2}"
	fi
	# Modifications are reported, not gated: an absorb may legitimately rewrite bodies
	# (formatting, version pins). Say so out loud so a silent mass rewrite is visible
	# in the same report a reviewer already reads.
	if [[ ${modified} -gt 0 ]] && awk -v m="${modified}" -v t="${pre_total}" 'BEGIN { exit !(m * 100 > t * 30) }'; then
		log ""
		log "NOTE           ${modified} of ${pre_total} pre-existing entries changed body/sha"
		log "NOTE           (>30%). Removals are gated here; body swaps are not. Prove those"
		log "NOTE           with scripts/verify_registry_tree.py against the source repo."
	fi
	log ""

	# Requirement 6: report, never create. Creating a preserve branch mutates refs
	# and, to be useful, would have to be pushed - that is a remote-mutating action.
	preserve_ref=$(report_preserve "${pre_commit:-}" "${pre_tree:-}")
	if [[ -n ${preserve_ref} ]]; then
		log "preserve_ref   ${preserve_ref}"
	else
		log "preserve_ref   NONE"
		log "ADVICE         no preserve/<branch> ref matches the pre-absorb commit or tree."
		log "ADVICE         Before any absorb, snapshot the current head so a replacement"
		log "ADVICE         is recoverable in one checkout, not by hand:"
		if [[ -n ${pre_commit:-} ]]; then
			log "ADVICE           git branch preserve/main-before-absorb ${pre_commit}"
			log "ADVICE           git push origin preserve/main-before-absorb"
		else
			log "ADVICE           git branch preserve/main-before-absorb <pre-absorb head>"
		fi
		log "ADVICE         This gate will not do that for you: it never mutates refs."
	fi

	if [[ ${verdict} == pass ]]; then
		log ""
		log "PRE_ABSORB_RESULT=PASS"
		log "PRE_ABSORB_FILES_PRE=${pre_total}"
		log "PRE_ABSORB_FILES_POST=${post_total}"
		log "PRE_ABSORB_ADDED=${added}"
		log "PRE_ABSORB_REMOVED=${removed}"
		log "PRE_ABSORB_MODIFIED=${modified}"
		log "PRE_ABSORB_EXIT=${EXIT_PASS}"
		echo "report         ${report}"
	else
		if [[ -n ${ALLOW_REMOVALS} ]]; then
			reason="removals (${removed}) exceed the explicit allowance (${ALLOW_REMOVALS})"
		else
			reason="removals (${removed}) exceed ${DEFAULT_MAX_REMOVALS} files and ${MAX_REMOVED_PERCENT}% of ${pre_total}"
		fi
		log ""
		log "PRE_ABSORB_RESULT=FAIL"
		log "PRE_ABSORB_FILES_PRE=${pre_total}"
		log "PRE_ABSORB_FILES_POST=${post_total}"
		log "PRE_ABSORB_ADDED=${added}"
		log "PRE_ABSORB_REMOVED=${removed}"
		log "PRE_ABSORB_MODIFIED=${modified}"
		log "PRE_ABSORB_EXIT=${EXIT_REPLACED}"
		echo "report         ${report}"
		{
			echo
			echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
			echo "TREE REPLACEMENT SUSPECTED"
			echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
			echo "An absorb is additive. This one deleted ${removed} pre-existing files"
			echo "(${added} added, ${modified} modified, ${post_total} present afterwards)."
			echo "That is the signature of the 2026-11-23/24 incident, where the tree was"
			echo "replaced and needed three restore commits plus six hand-made safety"
			echo "branches to undo."
			echo
			echo "  pre-absorb head: ${pre_commit:-unknown}"
			echo "  post commit:     ${post_commit}"
			echo "  removed list:    ${removed_list}"
			echo "  full report:     ${report}"
			echo
			echo "Do not merge this. Either restore the deleted paths from"
			echo "  git checkout ${pre_commit:-<pre-absorb head>} -- ."
			echo "or, if the deletion is genuinely intended, re-run declaring it:"
			echo "  ${PROG} --check --pre-ref <pre-absorb ref> --post-ref ${POST_REF} --allow-removals ${removed}"
			echo "and say why in the commit message."
			echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
		} >>"${report}"
		cat >&2 <<EOF

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
TREE REPLACEMENT SUSPECTED
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
${reason}
  pre-absorb head: ${pre_commit:-unknown}
  post commit:     ${post_commit}
  files_pre:       ${pre_total}
  files_post:      ${post_total}
  added:           ${added}
  REMOVED:         ${removed}
  modified:        ${modified}

removed paths:  ${removed_list}
full report:    ${report}

An absorb only adds. Restore with:
  git checkout ${pre_commit:-<pre-absorb head>} -- .
or declare the deletion explicitly:
  ${PROG} --check --pre-ref <pre-absorb ref> --post-ref ${POST_REF} --allow-removals ${removed}
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

EOF
		exit "${EXIT_REPLACED}"
	fi

	if [[ ${REQUIRE_PRESERVE} == 1 ]] && [[ -z ${preserve_ref} ]]; then
		die "${EXIT_PRESERVE}" "--require-preserve: no preserve/ ref matches the pre-absorb head; create one first"
	fi
	exit "${EXIT_PASS}"
}

case "${MODE}" in
snapshot) do_snapshot ;;
check) do_check ;;
*) die "${EXIT_USAGE}" "unknown mode '${MODE}'" ;;
esac
