# status: pending
# maps-to: src/lib.rs
@fr-9 @crate
Feature: Crate public module surface
  Hexagonal layers are exposed with selective re-exports at crate root.

  Scenario: Root re-exports resolve domain and application types
  # PENDING: use logkit::{Level, LogEntry, Logger, LogError, LoggerBuilder, ConsoleLogger}

  Scenario: Layer modules are public
  # PENDING: logkit::domain, application, adapters, infrastructure accessible

  Scenario: Adapter sink types reachable via adapters module
  # PENDING: use logkit::adapters::{Sink, ConsoleSink}
