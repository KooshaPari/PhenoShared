# ADR — pyhex

## ADR-001: Protocol-Based Ports
**Status:** Accepted
**Context:** Python supports both ABC-based and Protocol-based structural subtyping.
**Decision:** Ports are `Protocol` classes. Adapters do not need to explicitly inherit from port classes; structural compatibility is sufficient.
**Rationale:** Decouples adapter code from library imports; adapters can be used without depending on pyhex at runtime.

## ADR-002: Result Type vs Exceptions
**Status:** Accepted
**Context:** Python convention uses exceptions, but they are untyped and invisible in function signatures.
**Decision:** Use cases return `Result[T, E]`. Exceptions are reserved for unrecoverable programmer errors (assertions, invariant violations).
**Rationale:** Forces error handling at call sites; improves mypy inference of error types.
**Alternatives considered:** `returns` library (fp-ts style) — heavier dep; bare exceptions — untyped.

## ADR-003: Python Version Floor
**Status:** Accepted
**Context:** Modern Python type features (PEP 695, `Self`, `tomllib`) require 3.11+.
**Decision:** Minimum supported version is Python 3.11. No backports of `tomllib` or `Self`.
**Rationale:** Phenotype platform targets current Python; backport complexity not justified.

## ADR-004: No Framework in Core
**Status:** Accepted
**Context:** FastAPI, Django, and other frameworks should not be forced on consumers.
**Decision:** Core package has zero production deps. Framework adapters shipped as `pyhex[fastapi]`, `pyhex[django]` extras.
**Rationale:** Consumers choose their framework; pyhex is framework-agnostic.
