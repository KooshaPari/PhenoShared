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

tmp_diff="$(mktemp)"
git diff --cached --no-color --unified=3 > "$tmp_diff"

if [ ! -s "$tmp_diff" ]; then
  rm -f "$tmp_diff"
  exit 0
fi

awk -v disable="$HAPPY_PATH_DISABLE" \
    -v allow="$HAPPY_PATH_BIG_CONSTANT_ALLOW" \
    -v big_allow_re="$HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX" \
    -v mode="$mode" '
function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }

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

# R3 allowlist via regex. The default regex (configurable via
# HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX) covers well-known root-cause constants
# such as the canonical WSM3D VoxelScaleMultiplier=8.0 fix. Override per-repo.
# Note: gawk's `(?i)` inline flag is silently dropped when a regex is passed
# via a string variable, so we strip the prefix and lower-case both the
# regex and the input line. Callers already pass `lc` (lowercased body).
# This keeps the default `(?i)voxelscalemultiplier` and any case-insensitive
# user override effective on both gawk and POSIX awk.
function matches_allow_regex(line,    re) {
  re = big_allow_re
  if (re == "") return 0
  # Strip any leading inline flags (e.g. "(?i)") so they don't end up in
  # the matched text. Inline flags accepted: (?i) for case-insensitive.
  sub(/^\(\?[imx]+\)/, "", re)
  re = tolower(re)
  return (line ~ re) ? 1 : 0
}

function window_has(idx, pattern,    i, s) {
  for (i = idx; i <= idx + 2; i++) {
    if (i > total_lines) break
    s = diff_lines[i]
    if (tolower(s) ~ pattern) return 1
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

{
  total_lines = NR
  diff_lines[NR] = $0

  if ($0 ~ /^diff --git /) {
    file = $3
    sub(/^b\//, "", file)
    sub(/^a\//, "", file)
    in_hunk = 0
    # Skip the policy files themselves: the rules, their docs, and this script
    # source naturally contain the words we lint for (e.g. literal "flag=true"
    # as an example, or the regex pattern /fixed|works|done|.../ itself).
    # Extending the skip-list: HAPPY_PATH_POLICY_SKIP (comma-sep glob substrings).
    skip_pat = "^(governance/|docs/governance/|docs/ai-dd-pitfalls|/ai-dd-pitfalls|/feedback_aidd_hardening|/CLAUDE\\.md)"
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
    if (!is_template && lc ~ /(fixed|works|done|passing|verified|✅|✔|✔️)/) {
      if (!window_has(NR, /user-confirmed|user-saw|confirmed by user|eyes-on|last-link:/)) {
        report("r1", file, line_no, body, "user-eye confirmation missing")
      }
    }

    # R2 telemetry-only-success
    if (lc ~ /(flag=true|enabled=true|build ok|200 ok|submitcount|executed|compiled|patch applied)/) {
      if (!window_has(NR, /pixel|screenshot by user|user said|frameMs|measured|observed|last-link:/)) {
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
      if (!matches_allow_regex(lc) && !has_allow(body) && !window_has(NR, /todo|fixme|hack|root-cause|investigate/)) {
        report("r3", file, line_no, body, "blunt-force constant assignment")
      }
    }

    # R4 iteration-grind
    if (lc ~ /(itercount|retrycount|attemptcount|loopcount|tries)[[:space:]]*=[[:space:]]*[0-9]+/) {
      if (match(lc, /(itercount|retrycount|attemptcount|loopcount|tries)[[:space:]]*=[[:space:]]*([0-9]+)/, m)) {
        if ((m[2] + 0) > 20 && !window_has(NR, /confirmedwins|userconfirmed|user-confirmed|confirmed by user|eyes-on|user-saw/)) {
          report("r4", file, line_no, body, "iteration/grind without confirmed wins")
        }
      }
    }

    # R5 build-without-size-perf
    if (lc ~ /(compiled|build ok|npm test|cargo build|dotnet build|go test|mvn test)/ && is_comment(body)) {
      if (!window_has(NR, /size=|frameMs|mb|ms|seconds|latency|memory|kb|throughput/)) {
        report("r5", file, line_no, body, "build/test claim without size/perf/robustness token")
      }
    }

    # R6 stale-code-risk
    if (lc ~ /\b(rebuilt|compiled|tested)\b/ && !is_comment(body)) {
      if (!window_has(NR, /version=|kill-stale|clear-cache|sha|hash|banner|last-link:/)) {
        report("r6", file, line_no, body, "stale rebuild/test claim without reset/version/badge token")
      }
    }

    # R7 motion-without-result
    if (lc ~ /(enabled[[:space:]]*=[[:space:]]*false|featureflag[[:space:]]*=[[:space:]]*false|flag[[:space:]]*=[[:space:]]*false|experimental[[:space:]]*=[[:space:]]*false|verbose[[:space:]]*=[[:space:]]*false|# todo|no-op|stub|proposed only)/) {
      report("r7", file, line_no, body, "feature false/placeholder introduced without result signal")
    }

  } else if (tag == " " || tag == "-") {
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
' "$tmp_diff"

status=$?
rm -f "$tmp_diff"
exit "$status"

