# L4-032 Triage Libification

## Goal

Extract the AgilePlus triage command logic into the shared agileplus-triage
crate so other tools can embed the same parsing, override, and classification
flow without depending on the CLI crate.

## Success Criteria

- crates/agileplus-triage owns the triage command args and runner.
- crates/agileplus-cli/src/commands/triage.rs becomes a thin compatibility
  shim that re-exports the shared surface.
- The triage crate builds and tests cleanly in isolation.

## Notes

- The workspace already contained crates/agileplus-triage/ and it was already
  listed in the root workspace members, so this task was completed as an
  extraction into the existing crate rather than creation of a new path.
