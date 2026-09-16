# status: pending
# maps-to: src/domain/log_entry.rs::LogEntry
@fr-2 @domain
Feature: Structured log entry
  Each log event is a record with identity, severity, message, timestamp, and fields.

  Scenario: new assigns level and message
  # PENDING: LogEntry::new(Level::Info, "hello").message == "hello"

  Scenario: new generates non-nil UUID and UTC timestamp
  # PENDING: id != Uuid::nil(); timestamp within tolerance of Utc::now()

  Scenario: with_field appends structured key-value pairs
  # PENDING: chained with_field calls increase fields.len()

  Scenario: LogEntry round-trips through JSON serde
  # PENDING: serialize/deserialize preserves id, level, message, timestamp, fields
