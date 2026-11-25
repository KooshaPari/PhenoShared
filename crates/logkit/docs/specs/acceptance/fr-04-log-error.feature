# status: pending
# maps-to: src/domain/logger.rs::LogError
@fr-4 @domain
Feature: Log error taxonomy
  Logging failures are classified for callers to handle.

  Scenario Outline: Display formats error variants
  # PENDING: format!("{}", err) matches expected prefix
    Examples:
      | variant         | message | expected_prefix          |
      | Io              | disk    | IO error: disk           |
      | Serialization   | json    | Serialization error: json|

  Scenario: LogError implements std::error::Error
  # PENDING: trait bound LogError: Error compiles
