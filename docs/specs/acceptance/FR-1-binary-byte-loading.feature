Feature: FR-1 Binary byte loading handles missing input paths as errors
  In order to provide predictable failure behavior when loading binaries
  As a caller
  I want byte load APIs to return explicit path-aware errors.

  @pending
  Scenario: Return error when path is missing
    Given a non-existent file path
    When I call `pine_loader::read_bytes` with that path
    Then the result is `Err`
    And the error message contains the path
    And no bytes are produced

