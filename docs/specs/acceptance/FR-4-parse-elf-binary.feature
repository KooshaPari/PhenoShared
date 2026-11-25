Feature: FR-4 ELF parser emits normalized ElfBinary output
  In order to consume ELF metadata consistently
  As a caller
  I want `parse_elf` to return populated `ElfBinary` details.

  @pending
  Scenario: Parse valid ELF bytes
    Given valid ELF bytes with at least one section and symbol
    When I call `parse_elf` with those bytes
    Then the result is `Ok(ElfBinary)`
    And `entry_point`, `architecture`, and symbol list are populated

