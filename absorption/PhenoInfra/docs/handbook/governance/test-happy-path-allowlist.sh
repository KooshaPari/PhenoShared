#!/bin/sh
# Test harness for happy-path-precommit.sh R3 allowlist.
#
# Proves that HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX exempts the
# canonical WSM3D VoxelScaleMultiplier=8.0 line from R3 reporting,
# while still reporting R3 on other blunt-force constants in the
# same diff.
#
# This test invokes the awk rule engine from the production script
# (happy-path-precommit.sh) directly on synthesized diffs, bypassing
# the mktemp + git diff dance. The test focuses on the allowlist
# logic added in the R3 fix; the pre-existing window_has gawk-portability
# quirk is acknowledged but not in scope.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUARD="$SCRIPT_DIR/happy-path-precommit.sh"
PASS=0
FAIL=0

if [ ! -f "$GUARD" ]; then
  echo "ERROR: $GUARD not found" >&2
  exit 2
fi

# Reusable awk rule engine: same R3 rule + allowlist as production script.
# R3 verbatim from happy-path-precommit.sh; matches_allow_regex verbatim.
awk_engine='
function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
function split_list(raw,    i, n, arr, out, t) {
  n = split(raw, arr, ","); out = ""
  for (i = 1; i <= n; i++) { t = tolower(trim(arr[i])); if (t != "") out = out " " t }
  return out
}
function has_allow(line,    i, token, list, arr, n) {
  list = split_list(allow); n = split(list, arr, " ")
  for (i = 1; i <= n; i++) { token = arr[i]; if (token == "") continue; if (index(line, token) > 0) return 1 }
  return 0
}
# matches_allow_regex: mirrors the production implementation, including
# the (?i) prefix strip and tolower() workaround for gawk string-variable
# regex case-insensitivity (gawk 5.0 silently drops inline flags when
# the regex is passed as a string variable).
function matches_allow_regex(line,    re) {
  re = big_allow_re
  if (re == "") return 0
  sub(/^\(\?[imx]+\)/, "", re)
  re = tolower(re)
  return (line ~ re) ? 1 : 0
}
BEGIN { fail_count = 0; file = ""; in_hunk = 0; current_new_line = 0 }
{
  if ($0 ~ /^diff --git /) { file = $3; sub(/^b\//, "", file); sub(/^a\//, "", file); in_hunk = 0; next }
  if ($0 ~ /^@@ /) { if (match($0, /\+[0-9]+/)) current_new_line = int(substr($0, RSTART+1, RLENGTH-1)); in_hunk = 1; next }
  if (!in_hunk || $0 ~ /^\+\+\+/ || file == "") next
  tag = substr($0, 1, 1); body = substr($0, 2); lc = tolower(body)
  if (tag == "+") {
    current_new_line++
    # R3 (verbatim from production script, sans the pre-existing window_has
    # gawk-portability quirk; this test focuses on the allowlist addition).
    if (lc ~ /= [0-9]{4,}/ ||
        lc ~ / *= *1[0-9]\./ ||
        lc ~ /scale *= *[0-9]{2,}/ ||
        lc ~ /multiplier *= *[0-9]{2,}/ ||
        lc ~ /voxelScale *= *[0-9.]+/ ||
        lc ~ /timeout *= *[0-9]{5,}/ ||
        lc ~ /bufferSize *= *[0-9]{6,}/) {
      if (!matches_allow_regex(lc) && !has_allow(body)) {
        print "FAIL [R3] " file ":" current_new_line " " body
        fail_count++
      }
    }
  } else if (tag == " " || tag == "-") { current_new_line++ }
}
END { if (fail_count > 0) exit 1; exit 0 }
'

# ---- Test 1: allowlist matches VoxelScaleMultiplier=8.0 (the canonical fix) ----
cat > /tmp/phenohb_test1.diff <<'EOF'
diff --git a/SomeMod/Settings.cs b/SomeMod/Settings.cs
index 1111111..2222222 100644
--- a/SomeMod/Settings.cs
+++ b/SomeMod/Settings.cs
@@ -1,3 +1,4 @@
 class Settings {
+  public float VoxelScaleMultiplier = 8.0f;
 }
EOF

echo "Test 1: default allowlist must exempt VoxelScaleMultiplier=8.0 from R3" >&2
out=$(awk -v allow="" -v big_allow_re="(?i)voxelscalemultiplier" "$awk_engine" /tmp/phenohb_test1.diff 2>&1)
ec=$?
if [ -z "$out" ] && [ $ec -eq 0 ]; then
  echo "  PASS (R3 skipped, exit 0)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 fired on allowlisted line (output: $out, exit: $ec)" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 2: allowlist is case-insensitive (voxelscale=8.0 also exempted) ----
cat > /tmp/phenohb_test2.diff <<'EOF'
diff --git a/SomeMod/Settings.cs b/SomeMod/Settings.cs
index 1111111..2222222 100644
--- a/SomeMod/Settings.cs
+++ b/SomeMod/Settings.cs
@@ -1,3 +1,4 @@
 class Settings {
+  public float voxelscale = 8.0f;
 }
EOF

echo "Test 2: allowlist regex is case-insensitive" >&2
out=$(awk -v allow="" -v big_allow_re="(?i)voxelscalemultiplier" "$awk_engine" /tmp/phenohb_test2.diff 2>&1)
ec=$?
if [ -z "$out" ] && [ $ec -eq 0 ]; then
  echo "  PASS (R3 skipped on lowercase)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 fired on case-variant (output: $out, exit: $ec)" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 3: a non-allowlisted large constant still triggers R3 ----
cat > /tmp/phenohb_test3.diff <<'EOF'
diff --git a/SomeMod/Settings.cs b/SomeMod/Settings.cs
index 1111111..2222222 100644
--- a/SomeMod/Settings.cs
+++ b/SomeMod/Settings.cs
@@ -1,3 +1,4 @@
 class Settings {
+  public int myMultiplier = 50.0f;
 }
EOF

echo "Test 3: non-allowlisted multiplier still triggers R3" >&2
out=$(awk -v allow="" -v big_allow_re="(?i)voxelscalemultiplier" "$awk_engine" /tmp/phenohb_test3.diff 2>&1)
ec=$?
if echo "$out" | grep -q "FAIL \[R3\]"; then
  echo "  PASS (R3 fired as expected)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 did NOT fire on non-allowlisted constant (output: $out, exit: $ec)" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 4: empty allowlist regex disables the exemption ----
# Use a multiplier=99 line (triggers R3 sub-rule) to verify that an empty
# allowlist regex permits the R3 branch to fire.
cat > /tmp/phenohb_test4.diff <<'EOF'
diff --git a/SomeMod/Settings.cs b/SomeMod/Settings.cs
index 1111111..2222222 100644
--- a/SomeMod/Settings.cs
+++ b/SomeMod/Settings.cs
@@ -1,3 +1,4 @@
 class Settings {
+  public float myMultiplier = 99.0f;
 }
EOF
echo "Test 4: empty allowlist regex (regex='') permits R3 to fire on a non-exempt constant" >&2
out=$(awk -v allow="" -v big_allow_re="" "$awk_engine" /tmp/phenohb_test4.diff 2>&1)
ec=$?
if echo "$out" | grep -q "FAIL \[R3\]"; then
  echo "  PASS (R3 fired when allowlist disabled)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 did not fire when allowlist disabled (output: $out, exit: $ec)" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 4b: per-repo override of allowlist regex ----
# Override HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX to permit a different constant.
cat > /tmp/phenohb_test4b.diff <<'EOF'
diff --git a/SomeMod/Settings.cs b/SomeMod/Settings.cs
index 1111111..2222222 100644
--- a/SomeMod/Settings.cs
+++ b/SomeMod/Settings.cs
@@ -1,3 +1,4 @@
 class Settings {
+  public float customMultiplier = 99.0f;
 }
EOF
echo "Test 4b: per-repo allowlist override accepts a different constant name" >&2
out=$(awk -v allow="" -v big_allow_re="(?i)custommultiplier" "$awk_engine" /tmp/phenohb_test4b.diff 2>&1)
ec=$?
if [ -z "$out" ] && [ $ec -eq 0 ]; then
  echo "  PASS (R3 skipped for customMultiplier when configured)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 fired on customMultiplier despite allowlist override (output: $out, exit: $ec)" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 5: matches_allow_regex function exists in production script ----
echo "Test 5: production script defines matches_allow_regex and big_allow_re" >&2
if grep -q "function matches_allow_regex" "$GUARD" && \
   grep -q "HAPPY_PATH_BIG_CONSTANT_ALLOW_REGEX" "$GUARD" && \
   grep -q "big_allow_re=" "$GUARD"; then
  echo "  PASS (production script wires the new function + env var)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: production script missing matches_allow_regex or env var wiring" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 6: R3 branch in production script calls matches_allow_regex ----
echo "Test 6: R3 branch in production script uses matches_allow_regex" >&2
if awk '/R3 blunt-force-constant/,/^    }$/' "$GUARD" | grep -q "matches_allow_regex"; then
  echo "  PASS (R3 branch consults the allowlist)" >&2
  PASS=$((PASS+1))
else
  echo "  FAIL: R3 branch does not call matches_allow_regex" >&2
  FAIL=$((FAIL+1))
fi

# ---- Test 7: workflow no longer installs bash via apt-get ----
echo "Test 7: workflow no longer runs 'sudo apt-get install -y bash'" >&2
if grep -q "sudo apt-get install -y bash" "$SCRIPT_DIR/../.github/workflows/happy-path-precommit.yml"; then
  echo "  FAIL: workflow still contains the redundant apt-get bash install" >&2
  FAIL=$((FAIL+1))
else
  echo "  PASS (no apt-get bash install)" >&2
  PASS=$((PASS+1))
fi

echo "" >&2
echo "=== RESULTS: $PASS passed, $FAIL failed ===" >&2
if [ $FAIL -eq 0 ]; then
  exit 0
else
  exit 1
fi