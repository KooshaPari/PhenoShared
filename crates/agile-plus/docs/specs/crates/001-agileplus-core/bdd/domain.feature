Feature: Domain event and snapshot models
  As an application-layer developer
  I want stable Event and Snapshot constructors and serde round-trips
  So that the event store and snapshot store can rely on safe store-managed defaults

  Background:
    Given the agileplus-domain crate is compiled
    And the Event type is available from agileplus_domain::domain::event
    And the Snapshot type is available from agileplus_domain::domain::snapshot

  Scenario: Event::new preserves identity, payload, and actor
    When a caller invokes Event::new("story", 42, "Created", payload, "user@host")
    Then the resulting Event has entity_type "story"
    And the resulting Event has entity_id 42
    And the resulting Event has event_type "Created"
    And the resulting Event has actor "user@host"
    And the resulting Event has the original payload

  Scenario: Event::new initializes store-managed fields
    When a caller invokes Event::new("story", 42, "Created", payload, "user@host")
    Then the resulting Event has id == 0
    And the resulting Event has sequence == 0
    And the resulting Event has prev_hash == [0; 32]
    And the resulting Event has hash == [0; 32]

  Scenario: Event timestamp is non-future
    When a caller invokes Event::new("story", 42, "Created", payload, "user@host")
    Then the resulting Event's timestamp is not after the post-construction clock
    And the resulting Event's timestamp is at or before the post-construction clock

  Scenario: Event round-trips through serde_json
    When a caller serializes an Event to JSON
    And a caller deserializes the JSON back into an Event
    Then the deserialized Event has the original entity_type
    And the deserialized Event has the original entity_id
    And the deserialized Event has the original event_type
    And the deserialized Event has the original actor
    And the deserialized Event has the original payload
    And the deserialized Event has the original sequence

  Scenario: Snapshot::new preserves identity, state, and event sequence
    When a caller invokes Snapshot::new("story", 42, state, 100)
    Then the resulting Snapshot has entity_type "story"
    And the resulting Snapshot has entity_id 42
    And the resulting Snapshot has event_sequence 100
    And the resulting Snapshot has the original state

  Scenario: Snapshot::new initializes id to zero
    When a caller invokes Snapshot::new("story", 42, state, 100)
    Then the resulting Snapshot has id == 0

  Scenario: Snapshot timestamp is non-future
    When a caller invokes Snapshot::new("story", 42, state, 100)
    Then the resulting Snapshot's taken_at is not after the post-construction clock
    And the resulting Snapshot's taken_at is at or before the post-construction clock

  Scenario: Snapshot round-trips through serde_json
    When a caller serializes a Snapshot to JSON
    And a caller deserializes the JSON back into a Snapshot
    Then the deserialized Snapshot has the original entity_type
    And the deserialized Snapshot has the original entity_id
    And the deserialized Snapshot has the original event_sequence
    And the deserialized Snapshot has the original state
