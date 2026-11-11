# Rule 30 Computational Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reproducible Rust and Python/Jupyter research lab for generating, validating, storing, and analyzing Rule 30 experiments, with a clear starting workspace for each of the three prize problems described in `grand.md`.

**Architecture:** A Rust workspace owns deterministic cellular-automaton generation, dataset serialization, verification, command-line entrypoints, and benchmarks. A Python package owns dataset loading, schema validation, statistics, and notebook helpers. Versioned datasets form the boundary between them; CI proves core parity and executes a small end-to-end experiment.

**Tech Stack:** Rust stable (Cargo, `clap`, `serde`, `sha2`), Python 3.12 (`uv`, `numpy`, `pandas`, `pyarrow`, `pytest`), Jupyter, GitHub Actions.

---

## Delivery rules

- Keep the universe finite and explicitly represent the boundary condition in every generated dataset.
- The reference implementation is the behavioral oracle; optimization never changes the public dataset semantics.
- Every output dataset has schema version, generator version, parameters, seed or initial-state digest, record count, and content checksum.
- Tests construct fixtures in temporary directories. Never write generated runs into the tracked `data/` tree during tests.
- Commit each completed task with the commit message shown below. Run its verification commands before committing.

## File layout after completion

```text
rule30-research/
  crates/rule30-core/          deterministic reference and packed engines
  crates/rule30-cli/           generate, inspect, verify commands
  data/.gitkeep                intentionally empty local dataset root
  datasets/schema/v1.json      portable dataset contract
  experiments/                 one directory per prize problem
  notebooks/                   reproducible analysis notebooks
  python/rule30_lab/           loading, validation, and statistics
  tests/                       Python unit and end-to-end tests
  .github/workflows/ci.yml     Rust and Python verification
```

## Task 1: Scaffold the lab and lock its toolchains

**Files:** `README.md`, `.gitignore`, `Cargo.toml`, `rust-toolchain.toml`, `crates/rule30-core/Cargo.toml`, `crates/rule30-core/src/lib.rs`, `crates/rule30-cli/Cargo.toml`, `crates/rule30-cli/src/main.rs`, `pyproject.toml`, `uv.lock`, `python/rule30_lab/__init__.py`, `tests/test_package.py`, `data/.gitkeep`

- [ ] Add a Cargo workspace with `rule30-core` and `rule30-cli`; pin stable Rust in `rust-toolchain.toml`.
- [ ] Add `pyproject.toml` using Python `>=3.12,<3.13`, packages from `python/`, and test dependencies `pytest`, `numpy`, `pandas`, and `pyarrow`.
- [ ] Write a README with bootstrap commands, the Rust/Python ownership boundary, and a short statement that `grand.md` is source material rather than an asserted solution.
- [ ] Add ignore rules for `target/`, `.venv/`, Jupyter checkpoints, generated parquet/JSONL datasets, and benchmark output; retain `data/.gitkeep`.

Test first:

```python
# tests/test_package.py
from rule30_lab import __version__

def test_package_has_version() -> None:
    assert __version__ == "0.1.0"
```

Implement `python/rule30_lab/__init__.py` as:

```python
"""Analysis helpers for reproducible Rule 30 experiments."""
__version__ = "0.1.0"
```

Verify:

```bash
uv sync --all-groups
uv run pytest -q
cargo test --workspace
cargo run -p rule30-cli -- --help
```

Expected: one Python test passes, Cargo tests pass, and CLI help lists a `generate` command placeholder only after Task 4.

Commit: `chore: scaffold reproducible Rule 30 lab`

## Task 2: Implement the reference Rule 30 engine from tests

**Files:** `crates/rule30-core/src/lib.rs`, `crates/rule30-core/tests/reference.rs`

- [ ] Define `Boundary::{FixedZero, Wrap}` and `Rule30Config { width, boundary }`; reject width zero.
- [ ] Define `Row` as a width-checked vector of binary cells and expose `cells()` only as an immutable slice.
- [ ] Implement the elementary rule using the canonical truth table: output is `left XOR (center OR right)`.
- [ ] Implement `next_row` and `generate_rows(initial, steps)` without hidden global state.

Write these assertions before the implementation:

```rust
#[test]
fn single_seed_matches_the_first_four_rule30_rows() {
    let config = Rule30Config::new(9, Boundary::FixedZero).unwrap();
    let seed = Row::from_cells(vec![0, 0, 0, 0, 1, 0, 0, 0, 0], 9).unwrap();
    let rows = generate_rows(&config, &seed, 4).unwrap();
    assert_eq!(rows[1].cells(), &[0, 0, 0, 1, 1, 1, 0, 0, 0]);
    assert_eq!(rows[2].cells(), &[0, 0, 1, 1, 0, 0, 1, 0, 0]);
    assert_eq!(rows[3].cells(), &[0, 1, 1, 0, 1, 1, 1, 1, 0]);
}

#[test]
fn wrap_boundary_reads_across_both_edges() {
    let config = Rule30Config::new(5, Boundary::Wrap).unwrap();
    let row = Row::from_cells(vec![1, 0, 0, 0, 0], 5).unwrap();
    assert_eq!(next_row(&config, &row).unwrap().cells(), &[1, 1, 0, 0, 1]);
}
```

Verify:

```bash
cargo fmt --check
cargo test -p rule30-core
```

Expected: reference tests pass with no warnings.

Commit: `feat: add tested reference Rule 30 engine`

## Task 3: Define the dataset contract and atomic exporter

**Files:** `datasets/schema/v1.json`, `crates/rule30-core/src/dataset.rs`, `crates/rule30-core/tests/dataset.rs`, `docs/dataset-schema.md`

- [ ] Create schema v1 for a JSON metadata document plus a Parquet row table. Metadata must contain `schema_version`, `generator`, `generator_version`, `created_at_utc`, `width`, `steps`, `boundary`, `initial_state_sha256`, `rows_sha256`, and `row_count`.
- [ ] Store rows as `step: u64` and a packed binary payload. Specify bit order as least-significant-bit first, with zero-filled unused tail bits.
- [ ] Implement `DatasetMetadata::validate()` and reject unsupported schema versions, mismatched dimensions, non-monotonic steps, or checksum mismatch.
- [ ] Write output to a sibling temporary path, fsync file contents, rename it to the final filename, then write metadata last. Remove only the temporary file if serialization fails.

Test first:

```rust
#[test]
fn export_then_verify_round_trips_and_checksums() {
    let output = tempfile::tempdir().unwrap();
    let run = tiny_fixed_zero_run();
    export_run(&run, output.path()).unwrap();
    let verified = verify_run(output.path()).unwrap();
    assert_eq!(verified.row_count, run.rows.len() as u64);
}

#[test]
fn verifier_rejects_a_tampered_row_file() {
    let output = tempfile::tempdir().unwrap();
    export_run(&tiny_fixed_zero_run(), output.path()).unwrap();
    tamper_first_payload_byte(output.path());
    assert!(verify_run(output.path()).is_err());
}
```

Verify:

```bash
cargo test -p rule30-core dataset
```

Expected: a pristine run verifies and a changed payload fails checksum verification.

Commit: `feat: add versioned dataset export and verification`

## Task 4: Add the reproducible command-line workflow

**Files:** `crates/rule30-cli/src/main.rs`, `crates/rule30-cli/tests/cli.rs`, `docs/cli.md`

- [ ] Implement `generate`, `inspect`, and `verify` subcommands with `clap`.
- [ ] `generate` accepts `--width`, `--steps`, `--boundary`, `--seed-index`, and `--out`; it builds a single-cell seed at the supplied index and refuses to overwrite an existing completed run directory.
- [ ] `inspect` prints only structured JSON metadata; `verify` prints structured JSON containing `valid`, `row_count`, and verified checksums.
- [ ] Use exit code 2 for invalid arguments and exit code 1 for a failed validation or I/O error. Send diagnostics to stderr.

Test first:

```rust
#[test]
fn generate_and_verify_are_an_end_to_end_round_trip() {
    let tmp = assert_fs::TempDir::new().unwrap();
    Command::cargo_bin("rule30").unwrap()
        .args(["generate", "--width", "33", "--steps", "16", "--boundary", "fixed-zero", "--seed-index", "16", "--out"])
        .arg(tmp.path())
        .assert()
        .success();
    Command::cargo_bin("rule30").unwrap().args(["verify", "--run"]).arg(tmp.path()).assert().success();
}
```

Verify:

```bash
cargo test -p rule30-cli
cargo run -p rule30-cli -- generate --width 33 --steps 16 --boundary fixed-zero --seed-index 16 --out /tmp/rule30-smoke
cargo run -p rule30-cli -- verify --run /tmp/rule30-smoke
```

Expected: the verifier reports `"valid":true` and `"row_count":17`.

Commit: `feat: expose reproducible generation CLI`

## Task 5: Add bit-packed generation and prove parity

**Files:** `crates/rule30-core/src/packed.rs`, `crates/rule30-core/tests/packed.rs`, `crates/rule30-core/benches/generation.rs`, `docs/benchmarks.md`

- [ ] Implement `PackedRow` with width, `Vec<u64>`, safe bit access, and canonical tail-bit clearing.
- [ ] Implement fixed-zero and wrapped neighbor shifts across word boundaries.
- [ ] Convert between `Row` and `PackedRow`; make the packed result the CLI generation engine only after parity passes.
- [ ] Benchmark reference versus packed generation at widths 257, 4,097, and 65,537 for 1,000 rows; report time and throughput without asserting a speedup in CI.

Test first, with deterministic randomized widths and seeds:

```rust
#[test]
fn packed_and_reference_match_for_odd_word_boundaries() {
    for width in [1, 2, 63, 64, 65, 127, 128, 129] {
        for boundary in [Boundary::FixedZero, Boundary::Wrap] {
            assert_equivalent_for_seed(width, boundary, 96, width / 2);
        }
    }
}
```

Verify:

```bash
cargo test -p rule30-core packed
cargo bench -p rule30-core --bench generation
```

Expected: parity suite passes; benchmark output contains each requested width.

Commit: `feat: add parity-tested packed Rule 30 engine`

## Task 6: Implement Python loading, validation, and baseline statistics

**Files:** `python/rule30_lab/dataset.py`, `python/rule30_lab/stats.py`, `tests/test_dataset.py`, `tests/test_stats.py`, `python/rule30_lab/py.typed`

- [ ] Load metadata and Parquet payloads into a `Run` dataclass; validate schema version, dimensions, row ordering, and SHA-256 before returning data.
- [ ] Expose `unpack_row`, `center_column`, `density_by_step`, `run_lengths`, and `lag_autocorrelation` with NumPy return types.
- [ ] Keep statistical functions pure: no filesystem operations and no implicit plots.
- [ ] Match Rust bit order exactly with explicit cross-language fixture tests generated by the Rust CLI.

Test first:

```python
def test_center_column_for_known_reference_fixture(reference_run: Path) -> None:
    run = load_run(reference_run)
    assert center_column(run).tolist()[:4] == [1, 1, 0, 1]

def test_run_lengths_handles_zero_and_one_runs() -> None:
    assert run_lengths(np.array([0, 0, 1, 1, 1, 0])).tolist() == [2, 3, 1]
```

Verify:

```bash
uv run pytest -q
uv run python -c 'from rule30_lab.dataset import load_run; print("import-ok")'
```

Expected: Python validates the Rust-created fixture and all statistics tests pass.

Commit: `feat: add Python dataset analysis toolkit`

## Task 7: Create the research entrypoints and baseline notebook

**Files:** `notebooks/01-baseline-rule30.ipynb`, `experiments/problem-1-central-column/README.md`, `experiments/problem-2-preimage/README.md`, `experiments/problem-3-invertibility/README.md`, `docs/literature.md`, `scripts/execute_baseline.sh`

- [ ] Create a parameterized notebook that loads a verified generated run, plots density and the center column, and writes figures only under `artifacts/`.
- [ ] Add a compact literature registry with source URL/identifier, claim, relevance to one prize problem, and verification status. Do not present literature claims as proofs.
- [ ] Give each problem workspace a precise falsifiable first experiment, required dataset parameters, expected artifact names, and stop condition.
- [ ] Write `scripts/execute_baseline.sh` to generate a fixed `width=4097`, `steps=4096`, fixed-zero centered-seed run, verify it, and execute the notebook headlessly.

Notebook acceptance cells:

```python
run = load_run(Path("../artifacts/baseline/run"))
assert run.metadata["boundary"] == "fixed-zero"
assert run.rows.shape == (4097, 4097)
assert verify_run(Path("../artifacts/baseline/run")).valid
```

Verify:

```bash
uv run jupyter nbconvert --execute --to notebook --inplace notebooks/01-baseline-rule30.ipynb
./scripts/execute_baseline.sh
```

Expected: executed notebook has no error outputs and baseline artifacts are reproducible from an empty `artifacts/` directory.

Commit: `docs: add Rule 30 research entrypoints and baseline`

## Task 8: Install CI and complete release-level verification

**Files:** `.github/workflows/ci.yml`, `README.md`, `docs/reproducibility.md`

- [ ] Create separate Rust and Python jobs on supported Ubuntu. Cache Cargo registry/build artifacts and uv downloads by lockfile hash.
- [ ] Rust job runs formatting, Clippy with warnings denied, all workspace tests, and a release-mode 257x128 CLI generate/verify smoke test.
- [ ] Python job installs the locked environment, runs `pytest`, and runs a small cross-language fixture validation.
- [ ] A final job depends on both and reports the exact command sequence in CI logs; it must not upload generated research data.
- [ ] Document hardware-independent reproducibility guarantees and explicitly distinguish them from benchmark comparability.

CI commands:

```bash
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo run --release -p rule30-cli -- generate --width 257 --steps 128 --boundary fixed-zero --seed-index 128 --out /tmp/rule30-ci
cargo run --release -p rule30-cli -- verify --run /tmp/rule30-ci
uv sync --all-groups --frozen
uv run pytest -q
```

Verify locally before push:

```bash
git diff --check
cargo fmt --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace
uv run pytest -q
git status --short --branch
```

Expected: no whitespace errors, all checks pass, and only intentional commits are ahead of `origin/main`.

Commit: `ci: verify the Rule 30 lab end to end`

## Final acceptance checklist

- [ ] A clean clone reaches a working environment with the documented Rust and uv commands.
- [ ] Reference and packed engines match across boundary modes and word boundaries.
- [ ] A dataset exported by Rust is accepted and decoded by Python; any payload alteration is rejected.
- [ ] The baseline script produces the same verified data metadata for identical parameters.
- [ ] CI is green on the pushed commit.
- [ ] The three prize-problem workspaces contain scoped experiments and literature provenance, without claiming a prize solution.
