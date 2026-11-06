Feature: FR-3 PE parser emits normalized PeBinary output
  In order to validate PE metadata extraction
  As a caller
  I want `parse_pe` to return stable section and entry metadata.

  @pending
  Scenario: Parse minimal PE fixture
    Given valid PE bytes containing one `.text` section
    When I call `parse_pe` with those bytes
    Then the result is `Ok(PeBinary)`
    And `entry_point`, `image_base`, and `.text` section details are correct

