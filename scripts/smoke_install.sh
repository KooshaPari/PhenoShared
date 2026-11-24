#!/usr/bin/env bash
# T0 install-truth smoke: imports + bench CLI help/self-test (no Docker, no OmniRoute).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

echo "[smoke] python: $($PY --version 2>&1)"

echo "[smoke] import yaml + requests"
"$PY" -c "import yaml, requests; print('yaml', yaml.__version__, 'requests', requests.__version__)"

echo "[smoke] import bench / pheno / verifier"
"$PY" -c "import bench, pheno, verifier; print('bench', bench.__version__, 'pheno', pheno.__version__)"

echo "[smoke] python -m bench --help"
"$PY" -m bench --help >/dev/null

echo "[smoke] python -m bench self-test"
"$PY" -m bench self-test

if [[ -d "$ROOT/agileplus-specs" ]] && [[ -f "$ROOT/agileplus-specs/index/spec.md" || -f "$ROOT/agileplus-specs/.git" ]]; then
  echo "[smoke] agileplus-specs present"
else
  echo "[smoke] WARN: agileplus-specs empty — run: git submodule update --init --recursive" >&2
fi

echo "[smoke] OK"
