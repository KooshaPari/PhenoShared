# status: pending
# maps-to: src/lib.rs, src/domain/, src/application/, src/adapters/
@nfr-5
Feature: Hexagonal layer separation
  Domain, application, and adapter layers maintain dependency direction.

  Scenario: Domain has no adapter imports
  # PENDING: domain/ sources do not reference crate::adapters

  Scenario: Application depends on domain only for logger construction
  # PENDING: logger_builder.rs imports only crate::domain

  Scenario: Adapters depend on domain for Sink contract
  # PENDING: sinks/mod.rs imports crate::domain types only
