# status: pending
# maps-to: src/application/logger_builder.rs::ConsoleLogger
@fr-6 @application
Feature: Console logger adapter
  Default built logger writes formatted lines when severity meets threshold.

  Scenario: log writes entries at or above configured level
  # PENDING: captured stdout contains "[INFO] app: visible"

  Scenario: log suppresses entries below configured level
  # PENDING: no output when entry.level < logger.level()

  Scenario: log line format includes level, name, and message
  # PENDING: output matches "[{level}] {name}: {message}"
