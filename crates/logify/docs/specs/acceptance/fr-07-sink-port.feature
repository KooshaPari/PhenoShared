# status: pending
# maps-to: src/adapters/sinks/mod.rs::Sink
@fr-7 @adapters
Feature: Sink port
  Output adapters implement async write and flush for structured entries.

  Scenario: Mock sink implements write and flush
  # PENDING: async mock Sink::write and flush return Ok(())

  Scenario: Sink trait requires Send and Sync
  # PENDING: Arc<dyn Sink> compiles and is Send + Sync
