# status: pending
# maps-to: src/domain/logger.rs::Logger
@fr-3 @domain
Feature: Logger port
  Application code depends on an async logger trait, not concrete sinks.

  Scenario: Mock logger implements log and level
  # PENDING: async mock Logger::log returns Ok(()); level() returns configured Level

  Scenario: Logger trait requires Send and Sync
  # PENDING: Arc<dyn Logger> compiles and is Send + Sync
