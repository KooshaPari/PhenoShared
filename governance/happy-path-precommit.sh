#!/bin/sh
# Phenotype org governance - happy-path-collapse guard. See docs/governance/happy-path-checklist.md for the rules.

set -eu

HAPPY_PATH_FAIL_ON="${HAPPY_PATH_FAIL_ON:-block}"
HAPPY_PATH_DISABLE="${HAPPY_PATH_DISABLE:-}"
HAPPY_PATH_BIG_CONSTANT_ALLOW="${HAPPY_PATH_BIG_CONSTANT_ALLOW:-}"
# Regex (POSIX ERE) exempting well-known, root-cause-derived constants from R3.
# Default: voxelScaleMultiplier (canonical WSM3D fix). Override per-repo via env.
HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX="${HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX:-(?i)voxelscalemultiplier}"

mode=$(printf '%s' "$HAPPY_PATH_FAIL_ON" | tr 'A-Z' 'a-z')
if [ "$mode" = "off" ]; then
	exit 0
fi

if [ -n "${HAPPY_PATH_HEAD:-}" ] && [ -z "${HAPPY_PATH_BASE:-}" ]; then
	echo "error: HAPPY_PATH_HEAD requires HAPPY_PATH_BASE" >&2
	exit 2
fi

tmp_diff="$(mktemp)"
trap 'rm -f "$tmp_diff"' EXIT HUP INT TERM
if [ -n "${HAPPY_PATH_BASE:-}" ]; then
	# GitHub sends an all-zero `before` SHA when a push creates the ref. A
	# root diff covers the complete new commit without resolving that SHA.
	if [ "$HAPPY_PATH_BASE" = "0000000000000000000000000000000000000000" ]; then
		git diff-tree --root --no-commit-id --no-renames --no-color --unified=3 -r \
			"${HAPPY_PATH_HEAD:-HEAD}" -- >"$tmp_diff"
	else
		git diff --no-renames --no-color --unified=3 \
			"$HAPPY_PATH_BASE" "${HAPPY_PATH_HEAD:-HEAD}" -- >"$tmp_diff"
	fi
else
	git diff --cached --no-renames --no-color --unified=3 >"$tmp_diff"
fi

if [ ! -s "$tmp_diff" ]; then
	rm -f "$tmp_diff"
	exit 0
fi

awk -v disable="$HAPPY_PATH_DISABLE" \
	-v allow="$HAPPY_PATH_BIG_CONSTANT_ALLOW" \
	-v big_allow_re="$HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX" \
	-v mode="$mode" '
function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }

# Blank out the contents of quoted strings. R1 fires on CLAIMS, and a trigger
# word inside a string literal is a value or a log message rather than an
# assertion about the work. R2 already covers telemetry claims separately.
#
# This strips a span ONLY when its delimiters are balanced. If a quote is left
# unterminated, nothing is stripped: the unmodified line is returned so the
# claim still matches. Failing open here would let one stray quote silence the
# rest of the line, which is how an ordinary English contraction used to slip
# through - an apostrophe inside a word is not a quote opener.
# The single-quote character is built with sprintf so this program can stay
# inside a single-quoted shell string.
function strip_quoted(s,   out, i, c, q, n, sq, prev) {
  sq = sprintf("%c", 39)
  out = ""; q = ""; n = length(s)
  for (i = 1; i <= n; i++) {
    c = substr(s, i, 1)
    if (q == "") {
      # An apostrophe directly after an alphanumeric character belongs to a
      # contraction or a possessive, never to an opening quote.
      if (c == sq && i > 1) {
        prev = substr(s, i - 1, 1)
        if (prev ~ /[[:alnum:]]/) { out = out c; continue }
      }
      # Backticks are NOT delimiters: a code span such as `verified` is still a
      # claim about the change (tests/governance-enforcement.test.ts asserts
      # exactly that), so stripping it would hide the very thing R1 looks for.
      if (c == "\"" || c == sq) q = c
      else out = out c
    } else {
      if (c == "\\") { i++; continue }
      if (c == q) q = ""
    }
  }
  if (q != "") return s
  return out
}

# R1 evaluates the PROSE of a line, not the shell syntax around it. The loop
# terminator "done" is a keyword, so it is dropped as the leading word of each
# command segment. Only the keyword goes: a claim that follows the terminator
# on the same line ("done; the parser is fixed now") is still a claim, so the
# remainder of the segment is still evaluated.
function r1_text(s,   segs, n, i, out, seg) {
  out = ""
  gsub(/&&|\|\||;|\|/, "\n", s)
  n = split(s, segs, "\n")
  for (i = 1; i <= n; i++) {
    seg = trim(segs[i])
    sub(/^done([ \t]|$)/, "", seg)
    seg = trim(seg)
    if (seg != "") out = (out == "" ? seg : out " " seg)
  }
  return out
}

function split_list(raw,    i, n, arr, out, t) {
  n = split(raw, arr, ",")
  out = ""
  for (i = 1; i <= n; i++) {
    t = tolower(trim(arr[i]))
    if (t != "") out = out " " t
  }
  return out
}

function is_disabled(rule,    i, token, list, arr, n) {
  list = split_list(disable)
  n = split(list, arr, " ")
  rule = tolower(rule)
  for (i = 1; i <= n; i++) {
    token = arr[i]
    if (token == "") continue
    if (token == rule || token == "rule" substr(rule,2) || token == "r" substr(rule,2)) return 1
  }
  return 0
}

function has_allow(line,    i, token, list, arr, n) {
  list = split_list(allow)
  n = split(list, arr, " ")
  for (i = 1; i <= n; i++) {
    token = arr[i]
    if (token == "") continue
    if (index(line, token) > 0) return 1
  }
  return 0
}

# POSIX ERE overrides are case-sensitive unless prefixed with (?i).
function matches_allow_regex(line,    re) {
  re = big_allow_re
  if (re == "") return 0
  if (sub(/^\(\?i\)/, "", re)) {
    return (tolower(line) ~ tolower(re)) ? 1 : 0
  }
  return (line ~ re) ? 1 : 0
}

function window_has(idx, pattern,    i, s) {
  for (i = idx; i <= idx + 2; i++) {
    if (i > total_lines) break
    s = diff_lines[i]
    if (s ~ /^diff --git / || s ~ /^@@ /) break
    if (substr(s, 1, 1) == "+" && s !~ /^\+\+\+/ && tolower(s) ~ pattern) return 1
  }
  return 0
}

function emit(level, rule, file, line_no, msg, snippet) {
  if (level == "FAIL") {
    fail_count++
  } else {
    warn_count++
  }
  print level " [" toupper(rule) "] " msg " at " file ":" line_no " -> " snippet
}

function report(rule, file, line_no, snippet, msg,    lvl) {
  if (is_disabled(rule)) return
  lvl = (mode == "warn" ? "WARN" : "FAIL")
  emit(lvl, rule, file, line_no, msg, snippet)
}

function is_comment(line) {
  return (line ~ /^[[:space:]]*[#\/]/) || (line ~ /^[[:space:]]*\*/) || (line ~ /^[[:space:]]*--/)
}

BEGIN {
  fail_count = 0
  warn_count = 0
  file = ""
  in_hunk = 0
  current_new_line = 0
  total_lines = 0
}

FNR == NR { diff_lines[FNR] = $0; total_lines = FNR; next }

{
  if ($0 ~ /^diff --git /) {
    file = $3
    sub(/^b\//, "", file)
    sub(/^a\//, "", file)
    in_hunk = 0
    # Skip the policy files themselves: the rules, their docs, and this script
    # source naturally contain the words we lint for (e.g. literal "flag=true"
    # as an example, or the regex pattern /fixed|works|done|.../ itself).
    # Extending the skip-list: HAPPY_PATH_POLICY_SKIP (comma-sep glob substrings).
    # Absorbed trees: `absorption/` and `native/` hold code written in another
    # project that arrived by absorption (perf-core via #797, the PlayCua
    # `native/` crate via #821). They are real, tested workspace members but not
    # prose authored here, so they inherit the `docs/absorbed-from-` exemption;
    # without it a mechanical `cargo fmt` trips the prose rules on pre-existing
    # lines rustfmt only re-indented. KNOWN GAP, not fixed here: any mechanical
    # reformat can still trip a prose rule because the guard cannot tell a
    # formatting-only hunk from one that adds content.
    #
    # Dated audit snapshots hold result tables quoting past outcomes. Their
    # provenance is the run they record, not the commit that adds them, so R1
    # and R2 judged them as claims about the current diff. Rewriting a historic
    # record to satisfy a prose rule would falsify it, which is worse. The
    # exemption is limited to the date-prefixed form (docs/audits/YYYY-MM-DD-)
    # so it cannot be used as a dumping ground for a fresh success claim.
    #
    # `researchledger/ingest/` is the research-ledger ingest pipeline, relocated
    # verbatim from KooshaPari/analysis-archive on 2026-11-11 (the corpus guard
    # that protects it moved in #903). It is the same class as the absorbed
    # trees above: real, tested code, but not prose authored here. A move shows
    # every line as added, so the prose rules judge 124 lines of pre-existing
    # code as if it were written in this diff - a Python helper literally named
    # `done()` reads as a completion claim, and three byte-count constants read
    # as blunt-force constants. Rewriting that code to satisfy the rules would
    # corrupt the move. The exemption is scoped to the relocated path only.
    skip_pat = "^(tests/governance-enforcement\\.test\\.ts$|governance/|docs/governance/|docs/ai-dd-pitfalls|/ai-dd-pitfalls|/feedback_aidd_hardening|/CLAUDE\\.md|docs/absorbed-from-|absorption/|native/|researchledger/ingest/|docs/audits/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-)"
    extra = ENVIRON["HAPPY_PATH_POLICY_SKIP"]
    if (extra != "") {
      n = split(extra, arr, ",")
      for (i = 1; i <= n; i++) {
        t = trim(arr[i])
        if (t != "") skip_pat = skip_pat "|^(" t ")"
      }
    }
    if (file ~ skip_pat) {
      file = ""
      in_hunk = 0
      next
    }
    next
  }

  if ($0 ~ /^@@ /) {
    if (match($0, /\+[0-9]+/)) {
      current_new_line = int(substr($0, RSTART + 1, RLENGTH - 1))
    }
    in_hunk = 1
    next
  }

  if (!in_hunk || $0 ~ /^\+\+\+/ || file == "") next

  tag = substr($0, 1, 1)
  body = substr($0, 2)
  lc = tolower(body)
  if (tag == "+") {
    current_new_line++
    line_no = current_new_line
    is_template = (file ~ /COMMIT_EDITMSG|MERGE_MSG|PULL_REQUEST_TEMPLATE|pull_request_template\.md/)

    # R1 fixed-claim-without-user-conf
    #
    # The trigger words are claims in PROSE. Two forms are not claims and do
    # not fire: the shell loop terminator (a keyword), and a word inside a
    # quoted string (a value or a log message). Everything else that matches
    # still needs a human-eye marker, exactly as before.
    if (!is_template) {
      claim = tolower(strip_quoted(r1_text(body)))
      if (claim ~ /(^|[^[:alnum:]_.])(fixed|works|done|passing|verified)([^[:alnum:]_]|$)|✅|✔|✔️/) {
        if (!window_has(FNR, "user-confirmed|user-saw|confirmed by user|eyes-on|last-link:")) {
          report("r1", file, line_no, body, "user-eye confirmation missing")
        }
      }
    }

    # R2 telemetry-only-success
    if (lc ~ /(flag=true|enabled=true|build ok|200 ok|submitcount|executed|compiled|patch applied)/) {
      if (!window_has(FNR, "pixel|screenshot by user|user said|framems|measured|observed|last-link:")) {
        report("r2", file, line_no, body, "telemetry-only success")
      }
    }

    # R3 blunt-force-constant
    if (lc ~ /= [0-9]{4,}/ ||
        lc ~ / *= *1[0-9]\./ ||
        lc ~ /scale *= *[0-9]{2,}/ ||
        lc ~ /multiplier *= *[0-9]{2,}/ ||
        lc ~ /voxelScale *= *[0-9.]+/ ||
        lc ~ /timeout *= *[0-9]{5,}/ ||
        lc ~ /bufferSize *= *[0-9]{6,}/) {
      if (!matches_allow_regex(body) && !has_allow(body) && !window_has(FNR, "todo|fixme|hack|root-cause|investigate")) {
        report("r3", file, line_no, body, "blunt-force constant assignment")
      }
    }

    # R4 iteration-grind
    if (lc ~ /(itercount|retrycount|attemptcount|loopcount|tries)[[:space:]]*=[[:space:]]*[0-9]+/) {
      if (match(lc, /(itercount|retrycount|attemptcount|loopcount|tries)[[:space:]]*=[[:space:]]*[0-9]+/)) {
        count_value = substr(lc, RSTART, RLENGTH)
        sub(/^[^=]*=[[:space:]]*/, "", count_value)
        if ((count_value + 0) > 20 && !window_has(FNR, "confirmedwins|userconfirmed|user-confirmed|confirmed by user|eyes-on|user-saw")) {
          report("r4", file, line_no, body, "iteration/grind without confirmed wins")
        }
      }
    }

    # R5 build-without-size-perf
    if (lc ~ /(compiled|build ok|npm test|cargo build|dotnet build|go test|mvn test)/ && is_comment(body)) {
      if (!window_has(FNR, "size=|framems|mb|ms|seconds|latency|memory|kb|throughput")) {
        report("r5", file, line_no, body, "build/test claim without size/perf/robustness token")
      }
    }

    # R6 stale-code-risk
    if (lc ~ /\b(rebuilt|compiled|tested)\b/ && !is_comment(body)) {
      if (!window_has(FNR, "version=|kill-stale|clear-cache|sha|hash|banner|last-link:")) {
        report("r6", file, line_no, body, "stale rebuild/test claim without reset/version/badge token")
      }
    }

    # R7 motion-without-result
    #
    # "client stubs" is the name of a generated artefact (codegen output), not
    # a placeholder implementation, so a task list that plans to generate Go and
    # Python client stubs is not motion-without-result. The exclusion is narrow:
    # a bare "stub" or "stub implementation" still fires.
    if (lc ~ /(enabled[[:space:]]*=[[:space:]]*false|featureflag[[:space:]]*=[[:space:]]*false|flag[[:space:]]*=[[:space:]]*false|experimental[[:space:]]*=[[:space:]]*false|verbose[[:space:]]*=[[:space:]]*false|# todo|no-op|stub|proposed only)/ \
        && lc !~ /(client|generated|codegen|sdk) stubs?/) {
      report("r7", file, line_no, body, "feature false/placeholder introduced without result signal")
    }

  } else if (tag == " ") {
    current_new_line++
  }
}

END {
  if (mode == "warn") {
    print "Summary: " warn_count " warning(s), " fail_count " muted-by-mode."
    exit 0
  }
  if (fail_count > 0) {
    print "Summary: " fail_count " failing check(s)."
    exit 1
  }
  print "Summary: no failures."
  exit 0
}
' "$tmp_diff" "$tmp_diff"

status=$?
rm -f "$tmp_diff"
exit "$status"
