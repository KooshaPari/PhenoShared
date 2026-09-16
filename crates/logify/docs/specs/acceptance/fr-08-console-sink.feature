# status: pending
# maps-to: src/adapters/sinks/mod.rs::ConsoleSink
@fr-8 @adapters
Feature: Console sink adapter
  Routes high-severity lines to stderr and lower severities to stdout.

  Scenario: new and default construct equivalent sinks
  # PENDING: ConsoleSink::new() and Default::default() behave identically

  Scenario: Error and Fatal entries write to stderr
  # PENDING: captured stderr for Level::Error entry

  Scenario: Below-Error entries write to stdout
  # PENDING: captured stdout for Level::Info entry

  Scenario: flush succeeds without side effects
  # PENDING: ConsoleSink::flush().await == Ok(())
