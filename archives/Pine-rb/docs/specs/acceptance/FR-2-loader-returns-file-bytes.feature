Feature: FR-2 ELF loader and PE loader return file bytes as raw payload
  In order to ensure consistent loader behavior
  As a caller
  I want both loaders to read complete file contents.

  @pending
  Scenario: Load returns exact bytes
    Given a temporary binary file containing arbitrary bytes
    When I call `ElfLoader::load` with the file path
    And I call `PeLoader::load` with the same file path
    Then both calls return `Ok(Vec<u8>)`
    And both vectors equal `std::fs::read(path)`

