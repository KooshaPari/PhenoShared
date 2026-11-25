Feature: FR-8 Snapshot serialization roundtrips process snapshots
  In order to persist and restore process state
  As a caller
  I want `JsonFileSerializationPort` to save/load JSON snapshots consistently.

  @pending
  Scenario: Save and load snapshot
    Given a `ProcessSnapshot` with non-empty fields
    When I call `JsonFileSerializationPort::save(snapshot, path)`
    And I call `JsonFileSerializationPort::load(path)`
    Then the loaded snapshot equals the original
    And empty destinations produce `SerializationError::InvalidDestination` or `SerializationError::Empty`

