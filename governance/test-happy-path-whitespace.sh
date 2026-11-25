#!/bin/sh
# Test harness for happy-path-precommit.sh whitespace-only reflow suppression.
#
# THE DEFECT THIS COVERS
# A mechanical reformat (re-indentation, line join, line wrap) rewrites lines the
# author never touched. The diff shows those lines as removed and re-added, so
# the prose rules (R1-R7) read pre-existing prose as if it had just been written
# and the guard went red on a change that added no content at all. Every such
# finding matched origin/main once whitespace was normalised away, so the check
# had no true positives on that class - and a permanently-red gate trains people
# to ignore it.
#
# THE RULE UNDER TEST
# A hunk whose removed and added content are EQUAL after whitespace
# normalisation is a reflow, so no line in it is a freshly authored claim and
# the hunk is skipped. Per-hunk, not per-file: a file can hold a reflow in one
# region and a real deletion in another.
#
# WHAT MUST NOT CHANGE
# The suppression is scoped to hunks that differ only by whitespace. A hunk that
# removes or adds one non-whitespace character still runs the full rule set, so
# real content loss is still reported. Cases (b), (c) and (d) below exist to
# prove that and to prove the reflow exemption cannot be used as a bypass.
#
# This drives the PRODUCTION script end to end - it builds a throwaway git repo
# per case and asks the guard to judge the diff. It does not copy the rule
# engine, so it cannot drift from what CI runs.
#
# Each case gets its own repository on purpose: resetting a shared one would
# need `git reset --hard`, which this host's git wrapper refuses.
#
# Run: sh governance/test-happy-path-whitespace.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUARD="${SCRIPT_DIR}/happy-path-precommit.sh"
PASS=0
FAIL=0
CASE=0

if [ ! -f "${GUARD}" ]; then
	echo "ERROR: ${GUARD} not found" >&2
	exit 2
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT HUP INT TERM

# run_case <label> <expect: pass|fail> <subject> <base-content> <head-content>
#
# Content arguments are expanded with `printf %b`, so a literal \n inside them
# is the line break that separates lines. A single-quoted argument keeps the
# shell from touching the text the guard is meant to judge.
#
# The filename is always subject.txt: the guard's path-based exemptions must not
# be what makes a case pass.
run_case() {
	label="$1"
	expect="$2"
	subject="$3"
	base_text="$4"
	head_text="$5"
	CASE=$((CASE + 1))
	case_dir="${work}/case${CASE}"
	mkdir -p "${case_dir}"
	cd "${case_dir}" || exit 2

	git init -q .
	git config user.email guard-test@example.invalid
	git config user.name "guard test"
	printf '%b\n' "${base_text}" >"${subject}"
	git add "${subject}"
	# The ledger trailers are required by this host's git wrapper; harmless
	# where that wrapper is absent.
	git commit -qm "base" -m "tx-agent: jcode" -m "tx-validated: test"
	base_sha="$(git rev-parse HEAD)"

	printf '%b\n' "${head_text}" >"${subject}"
	git add "${subject}"
	git commit -qm "reformat" -m "tx-agent: jcode" -m "tx-validated: test"
	head_sha="$(git rev-parse HEAD)"

	out="$(HAPPY_PATH_FAIL_ON=block HAPPY_PATH_BASE="${base_sha}" HAPPY_PATH_HEAD="${head_sha}" sh "${GUARD}" 2>&1)"
	ec=$?

	# The messages are built first: a command substitution inside an argument
	# masks the inner command's return value (shellcheck SC2312).
	first_line="$(printf '%s' "${out}" | head -1)"
	two_lines="$(printf '%s' "${out}" | head -2 | tr '\n' ' ')"

	if [ "${expect}" = "pass" ] && [ "${ec}" -eq 0 ]; then
		echo "  PASS (${label}): no finding on a whitespace-only reflow" >&2
		PASS=$((PASS + 1))
	elif [ "${expect}" = "fail" ] && [ "${ec}" -ne 0 ]; then
		echo "  PASS (${label}): content loss still reported -- ${first_line}" >&2
		PASS=$((PASS + 1))
	else
		echo "  FAIL (${label}): expected ${expect}, exit ${ec}, output: ${two_lines}" >&2
		FAIL=$((FAIL + 1))
	fi
}

echo "whitespace-only reflow suppression" >&2

# (a) A whitespace-only reflow produces NO finding.
#
# The claim line is pre-existing prose that the reformat only re-indented. Before
# the fix each of these was a red guard; they are the false-positive class.
run_case "re-indentation is not a finding" pass subject.txt \
	'# the parser is fixed now' \
	'    # the parser is fixed now'

run_case "deep re-indentation is not a finding" pass subject.txt \
	'# the parser is fixed now' \
	'\t\t\t\t# the parser is fixed now'

# A wrapped or joined line keeps its words and only moves the spaces between
# them, so the two forms are equal under whitespace normalisation. The text is
# left unprefixed on purpose: duplicating a comment marker across the joined
# lines would remove a non-whitespace character and stop being a reflow.
run_case "line join is not a finding" pass subject.txt \
	'the parser is fixed\nnow' \
	'the parser is fixed now'

run_case "line wrap is not a finding" pass subject.txt \
	'the parser is fixed now' \
	'the parser is\nfixed now'

run_case "tab-to-space indentation is not a finding" pass subject.txt \
	'\t# verified against the sample data' \
	'        # verified against the sample data'

# A reflow that also changes trailing whitespace is still whitespace-only.
run_case "trailing whitespace shift is not a finding" pass subject.txt \
	'# the parser is fixed now' \
	'# the parser is fixed now   '

# (b) A real content deletion still produces a finding.
#
# The deletion makes the hunk NOT whitespace-only, so the reflow exemption does
# not apply and R1 judges the re-indented claim as it would any added line.
run_case "deletion beside a reflow still reports" fail subject.txt \
	'# the parser is fixed now\n# a line that will be deleted' \
	'    # the parser is fixed now'

# (c) A deletion that does not touch the claim is still reported by its own
# hunk, and a freshly added claim is still reported.
run_case "new claim is still reported" fail subject.txt \
	'# unrelated baseline content' \
	'# the parser is fixed now'

# (d) Per-hunk scope: a reflow in one region must not suppress a finding in a
# different region of the same file. Two claims, one reflowed, one newly added,
# separated by enough unchanged context to form two hunks.
run_case "reflow hunk does not suppress a separate new claim" fail subject.txt \
	'# the first parser is fixed now\nctx one\nctx two\nctx three\nctx four\nctx five\nctx six\nctx seven' \
	'    # the first parser is fixed now\nctx one\nctx two\nctx three\nctx four\nctx five\nctx six\nctx seven\n# the second parser is fixed now'

# (e) A hunk that deletes content and adds none produces no added line, so it
# cannot produce an R1 finding either way. This pins the exit code at 0 for a
# pure deletion rather than a false pass/fail by accident.
run_case "pure deletion stays clean" pass subject.txt \
	'keep one\nkeep two\n# a line that will be deleted' \
	'keep one\nkeep two'

echo "" >&2
echo "passed: ${PASS}, failed: ${FAIL}" >&2
if [ "${FAIL}" -gt 0 ]; then
	exit 1
fi
exit 0
