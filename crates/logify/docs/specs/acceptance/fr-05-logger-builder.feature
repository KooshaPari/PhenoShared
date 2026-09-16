# status: pending
# maps-to: src/application/logger_builder.rs::LoggerBuilder
@fr-5 @application
Feature: Logger builder
  Fluent builder constructs a configured logger.

  Scenario: new defaults to Info level
  # PENDING: LoggerBuilder::new("app").build().level() == Level::Info

  Scenario: level sets minimum severity via chaining
  # PENDING: LoggerBuilder::new("app").level(Level::Warn).build().level() == Warn

  Scenario: build returns a Logger implementation
  # PENDING: built value implements Logger trait
