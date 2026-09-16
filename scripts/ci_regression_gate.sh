#!/usr/bin/env bash
set -uo pipefail

HARNESS="/Users/kooshapari/CodeProjects/Phenotype/pheno-harness"
OMLX="/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-omlx"
PORTAGE="/Users/kooshapari/CodeProjects/Phenotype/repos/portage"
EIDOLON="/Users/kooshapari/CodeProjects/Phenotype/repos/Eidolon"
BENCHORA="/Users/kooshapari/CodeProjects/Phenotype/repos/Benchora"

PASS=0
FAIL=0

run_check() {
	local name="$1"
	shift
	echo -n "$name... "
	if "$@" 2>/dev/null; then
		echo "PASS"
		PASS=$((PASS + 1))
	else
		echo "FAIL"
		FAIL=$((FAIL + 1))
	fi
}

echo "=== Cross-Repo CI Regression Gate ==="
echo ""

# Smoke tests
run_check "pheno-harness imports" python -c "from bench.types import EnergySource; from bench.executor import Executor"
run_check "portage imports" python -c "import portage"
run_check "codegen tests" python -m pytest "$HARNESS/tests/test_codegen.py" -q
run_check "bench harness smoke" bash "$HARNESS/scripts/bench_harness_smoke.sh"

# Contract validation
run_check "V5 contract validation" python "$HARNESS/scripts/validate_interchange.py" "$HARNESS/bench/results/stock-vs-ours/run-v5-qwen35-08b-contract.json"

# Rust checks
run_check "omlx cargo check" bash -c "cd '$OMLX/perf-core' && cargo check --quiet"
run_check "Eidolon cargo check" bash -c "cd '$EIDOLON' && cargo check --quiet"
run_check "Benchora cargo check" bash -c "cd '$BENCHORA' && cargo check --quiet"

# File size limits
echo -n "file size limits... "
OVERSIZE=$(find "$HARNESS/bench" "$PORTAGE/src" "$EIDOLON/crates" "$BENCHORA/src" -name "*.py" -o -name "*.rs" 2>/dev/null | xargs wc -l 2>/dev/null | awk '$1 > 500 && !/total/ {print}' | wc -l)
if [ "$OVERSIZE" -eq 0 ]; then
	echo "PASS (0 oversized)"
	PASS=$((PASS + 1))
else
	echo "FAIL ($OVERSIZE files >500 lines)"
	FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed out of $((PASS + FAIL)) ==="
exit $FAIL
