# Research

## In-Repo Findings

- crates/agileplus-cli/src/commands/triage.rs previously owned TriageArgs,
  run_triage, and local intent parsing while already depending on
  agileplus-triage::TriageClassifier.
- crates/agileplus-triage/src/lib.rs already existed as the public surface
  for shared triage modules, making it the correct extraction target.
- Cargo.toml already listed crates/agileplus-triage in [workspace].members.

## Extraction Decision

Move the CLI-owned parsing and command runner into agileplus-triage::lib,
re-export that API from the CLI command module, and add focused unit tests for
the extracted surface (parse_triage_input, classify_ticket).
