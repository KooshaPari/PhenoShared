Feature: FR-7 Section reader enforces bounded virtual reads
  In order to prevent invalid memory access
  As a caller
  I want `SectionReader` reads to fail with out-of-bounds errors.

  @pending
  Scenario: Read bytes within and outside bounds
    Given an `InMemorySectionReader` with one loaded section
    When I read bytes wholly inside the section range
    Then I receive those bytes
    When I read bytes that exceed the section bounds
    Then I receive `SectionError::OutOfBounds`

