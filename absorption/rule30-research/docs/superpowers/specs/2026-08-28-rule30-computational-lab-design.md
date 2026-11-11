# Rule 30 Computational Lab Design

## Purpose

Build a private, reproducible research environment for investigating Wolfram's
three Rule 30 prize problems:

1. Whether the center column always remains non-periodic.
2. Whether zero and one occur with equal limiting frequency in the center column.
3. Whether computing the nth center-column cell requires at least O(n) effort.

The lab will support computational evidence and proof exploration. It will not
represent experimental results as proofs or prize-ready conclusions.

## Repository and Project

- Repository: `<REDACTED>/rule30-research`, private.
- GitHub Project: `Rule 30 Research`, private.
- The project will track five lanes: shared infrastructure, literature and prior
  work, and one lane for each prize problem.

## Architecture

```text
rule30-research/
|-- crates/
|   |-- rule30-core/       # Bit-packed evolution and center-column API
|   `-- rule30-cli/        # Dataset generation, inspection, and benchmarks
|-- python/
|   `-- rule30_analysis/   # Statistical analysis and visualization
|-- notebooks/             # Reproducible investigations
|-- problems/
|   |-- problem-1/
|   |-- problem-2/
|   `-- problem-3/
|-- tests/                 # Shared fixtures and cross-language parity tests
|-- benchmarks/            # Performance and complexity evidence
|-- data/                  # Metadata and small fixtures only
|-- grand.md               # Source research brief supplied by the sponsor
`-- .github/workflows/     # Tests, linting, and bounded benchmarks
```

Rust is the authoritative computation layer. Python and Jupyter are the
analysis layer. The boundary between them is a documented, versioned dataset
format rather than an in-process language binding in the first release.

## Components

### `rule30-core`

Provide a small Rust library for Rule 30 evolution from a single nonzero cell.
It will expose reference and bit-packed implementations, streaming
center-column generation, bounded row generation, and deterministic state
serialization. The reference implementation prioritizes clarity and serves as
an oracle for optimized implementations.

### `rule30-cli`

Expose commands to generate center-column data, inspect dataset metadata,
verify checksums, and run controlled benchmarks. Commands will accept explicit
step counts, output paths, algorithm selection, and resource limits. Machine
readable output will be stable enough for notebooks and CI.

### `rule30_analysis`

Load exported datasets and provide reusable analyses for symbol counts,
running imbalance, block frequencies, autocorrelation, candidate-period
searches, and benchmark-model fitting. Statistical outputs must identify the
sample range and method and must not label finite observations as asymptotic
proofs.

### Problem workspaces

Each problem directory will contain a README defining the exact claim, known
results, experiment registry, negative results, proof sketches, and links to
reproducible artifacts. Shared methods belong in the core or analysis packages;
problem directories hold research narratives and problem-specific experiments.

## Data and Reproducibility

Every generated dataset will carry:

- schema version;
- Rule 30 initial condition and requested range;
- implementation and algorithm identifiers;
- repository commit SHA when available;
- creation timestamp and runtime environment summary;
- payload checksum;
- timing and resource-limit metadata.

Small fixtures may be committed. Large generated outputs, notebook checkpoints,
and local environments will be ignored. A manifest will document how to
regenerate every cited artifact.

## Error Handling

The CLI will reject invalid ranges, unsupported schema versions, conflicting
options, corrupt datasets, and unsafe output overwrites. Resource exhaustion or
interruption must leave no valid-looking partial artifact: output is written to
a temporary sibling and promoted only after metadata and checksum completion.
Python loaders will validate schema and checksum before analysis.

## Verification

Testing will include:

- known early Rule 30 rows and center-column bits;
- equivalence between reference and bit-packed implementations over varied
  bounded inputs;
- deterministic serialization and checksum verification;
- Rust export and Python import parity;
- corruption and invalid-parameter failure cases;
- property tests for local transition semantics;
- smoke execution of maintained notebooks;
- benchmark harness checks that validate results before recording timings.

CI will run formatting, linting, unit tests, parity tests, and short bounded
benchmarks. Long-running research experiments will remain explicit manual jobs
with recorded manifests.

## Initial GitHub Project Backlog

1. Scaffold the Rust workspace, Python package, reproducible environments, and CI.
2. Implement and cross-check the reference Rule 30 engine.
3. Add the bit-packed engine and benchmark harness.
4. Define and validate dataset schema v1.
5. Build the baseline analysis notebook and reusable statistics.
6. Catalog literature and known results for all three problems.
7. Establish one reproducible baseline experiment for each prize problem.

## Non-Goals for the Initial Release

- Claiming a solution to any prize problem.
- Distributed execution, GPU kernels, or cloud orchestration.
- A public website or interactive frontend.
- Wolfram Language as a required runtime.
- Committing large generated datasets.

These may be proposed later only when a measured research need justifies them.

## Acceptance Criteria

The initial lab is ready when a clean clone can install pinned Rust and Python
dependencies, run all verification, generate a documented center-column
dataset, validate it in Python, execute the baseline notebook, and reproduce a
bounded benchmark through documented commands. The private GitHub Project must
show the infrastructure and three research lanes with their initial work items.
