#!/bin/sh
# Test harness for happy-path-precommit.sh rule R1 (fixed-claim-without-user-conf).
#
# R1 fires on a CLAIM that something was finished: the words fixed, works,
# done, passing, verified, or a check mark, with no human-eye marker nearby.
#
# Two forms are not claims and must not fire:
#
#   * the shell loop terminator ("done", "done < <(cmd)") -- a keyword;
#   * a word inside a quoted string -- a value or a log message.
#
# This test drives the PRODUCTION script end to end: it builds a throwaway git
# repository per case, commits a line, and asks the guard to judge the diff.
# It does not copy the rule engine, so it cannot drift from what CI runs.
#
# Each case gets its own repository on purpose: resetting a shared one would
# need `git reset --hard`, which this host's git wrapper refuses.
#
# Run: sh governance/test-happy-path-claims.sh

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

# judge <label> <expect: pass|fail> <line-to-add>
judge() {
	label="$1"
	expect="$2"
	line="$3"
	CASE=$((CASE + 1))
	case_dir="${work}/case${CASE}"
	mkdir -p "${case_dir}"
	cd "${case_dir}" || exit 2

	git init -q .
	git config user.email guard-test@example.invalid
	git config user.name "guard test"
	printf 'placeholder\n' >subject.txt
	git add subject.txt
	# The ledger trailers are required by this host's git wrapper; harmless
	# where that wrapper is absent.
	git commit -qm "base" -m "tx-agent: jcode" -m "tx-validated: test"
	base_sha="$(git rev-parse HEAD)"

	printf '%s\n' "${line}" >>subject.txt
	git add subject.txt
	git commit -qm "add one line" -m "tx-agent: jcode" -m "tx-validated: test"
	head_sha="$(git rev-parse HEAD)"

	out="$(HAPPY_PATH_FAIL_ON=block HAPPY_PATH_BASE="${base_sha}" HAPPY_PATH_HEAD="${head_sha}" sh "${GUARD}" 2>&1)"
	ec=$?

	# The messages are built first: a command substitution inside an argument
	# masks the inner command's return value (shellcheck SC2312).
	first_line="$(printf '%s' "${out}" | head -1)"
	two_lines="$(printf '%s' "${out}" | head -2 | tr '\n' ' ')"

	if [ "${expect}" = "pass" ] && [ "${ec}" -eq 0 ]; then
		echo "  PASS (${label}): guard accepted it" >&2
		PASS=$((PASS + 1))
	elif [ "${expect}" = "fail" ] && [ "${ec}" -ne 0 ]; then
		echo "  PASS (${label}): guard rejected it -- ${first_line}" >&2
		PASS=$((PASS + 1))
	else
		echo "  FAIL (${label}): expected ${expect}, exit ${ec}, output: ${two_lines}" >&2
		FAIL=$((FAIL + 1))
	fi
}

echo "R1 claim detection" >&2

# A prose claim with no marker must still be rejected. This is the rule's
# whole point, so it is the first case.
judge "prose claim is rejected" fail "# the parser is fixed now"
judge "prose claim in a comment is rejected" fail "  # verified against the sample data"

# The shell loop terminator is a keyword, not a sentence.
judge "bare shell terminator is accepted" pass "	done"
judge "indented shell terminator is accepted" pass "    done"
judge "terminator with a redirection is accepted" pass "	done < <(gather_zombies)"
judge "terminator with a semicolon is accepted" pass "	done;"

# A trigger word inside a quoted string is a value or a log message.
# The line under test deliberately keeps a $ inside single quotes: that is
# the form the guard must accept.
# shellcheck disable=SC2016
judge "quoted log message is accepted" pass 'echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cron-tick done" >>"$LOG"'
judge "quoted value is accepted" pass '    "label": "done"'
judge "quoted word with a check mark is accepted" pass '    "label": "✔ Verify"'

# A claim OUTSIDE quotes on a line that also has a quoted string is still a
# claim.
judge "unquoted claim beside a quoted string is rejected" fail 'echo "starting"  # now done'

# A claim with a human-eye marker is accepted, as before.
judge "marker exempts a prose claim" pass "# user-confirmed: the parser is fixed now"

echo "" >&2
echo "passed: ${PASS}, failed: ${FAIL}" >&2
if [ "${FAIL}" -gt 0 ]; then
	exit 1
fi
exit 0
