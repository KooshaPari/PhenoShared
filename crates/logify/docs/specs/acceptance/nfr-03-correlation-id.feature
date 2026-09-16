# status: pending
# maps-to: src/domain/log_entry.rs::LogEntry::id
@nfr-3
Feature: Correlation identity
  Each log entry receives a unique UUID for tracing.

  Scenario: Sequential new calls produce distinct ids
  # PENDING: LogEntry::new(...).id != LogEntry::new(...).id

  Scenario: id serializes as UUID string in JSON
  # PENDING: JSON field "id" is hyphenated UUID format
