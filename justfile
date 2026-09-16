# Grade targets (strictest checks — no caching)
grade:
    @echo "=== Running full grade ==="
    ./grade.sh

grade-fast:
    @echo "=== Running fast grade ==="
    ./grade.sh --fast

grade-json:
    @echo "=== Running grade (JSON) ==="
    ./grade.sh --json

grade-html:
    @echo "=== Running grade (HTML) ==="
    ./grade.sh --html

# Measure code coverage (SSOT: see grade.sh for the canonical command)
coverage:
    cargo llvm-cov --workspace --fail-under-lines 85
