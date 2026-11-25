# status: pending
# maps-to: src/domain/log_entry.rs::LogEntry::fields
@nfr-2
Feature: Structured field interoperability
  Log entries carry arbitrary JSON values and serde round-trip.

  Scenario: with_field accepts heterogeneous JSON value types
  # PENDING: string, number, bool, object, array fields survive serde round-trip

  Scenario: Level and LogEntry derive Serialize and Deserialize
  # PENDING: serde_json round-trip on both types
