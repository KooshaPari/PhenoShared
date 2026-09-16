# status: pending
# maps-to: src/domain/log_level.rs::Level
@fr-1 @domain
Feature: Log level model
  The library exposes a total-order severity enum for filtering and serialization.

  Scenario: Default level is Info
  # PENDING: Level::default() == Level::Info

  Scenario Outline: Level as_str returns canonical uppercase label
  # PENDING: Level::<variant>.as_str() == "<label>"
    Examples:
      | variant | label   |
      | Trace   | TRACE   |
      | Debug   | DEBUG   |
      | Info    | INFO    |
      | Warn    | WARN    |
      | Error   | ERROR   |
      | Fatal   | FATAL   |

  Scenario: Levels are totally ordered by severity
  # PENDING: Trace < Debug < Info < Warn < Error < Fatal

  Scenario: Level round-trips through JSON serde
  # PENDING: serde_json::to_string(Level::Warn) deserializes back to Warn
