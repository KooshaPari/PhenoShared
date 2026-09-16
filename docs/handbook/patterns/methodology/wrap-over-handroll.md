# Wrap over hand-roll; reduce LOC

**Status:** adopted · **Applies to:** all new code.

## Convention

Before writing something from scratch, look for an existing library, crate, or fork that already does it and **wrap it behind a port** (see [xdd](xdd.md) — hexagonal). Prefer the existing ecosystem; hand-rolling is the exception you justify, not the default.

LOC reduction and simplification are **first-class goals**, weighted alongside features. A change that deletes more than it adds while preserving behavior is a win, not a risk.

## Why

Wrapping a maintained dependency behind a port gives us its bug fixes and security patches for free while keeping our domain swappable. Hand-rolled equivalents become unowned liabilities. Less code is less surface to test, audit, and break.

## Do / Don't

- **DO** wrap a vetted crate/library behind an adapter, with the port owned by our domain.
- **DO** delete dead code and collapse duplication aggressively.
- **DON'T** reimplement retry/backoff, auth, serialization, HTTP, or config parsing by hand when a standard option exists.
- **DON'T** keep a hand-rolled version "because we already wrote it" — sunk cost is not a reason.

Pair with the libification threshold in [xdd](xdd.md): extract at the 2nd use.
