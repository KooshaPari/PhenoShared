Feature: FR-12 Windows translator constants map to expected names
  In order to keep NT translation stable
  As a caller
  I want `WindowsNtSyscallTranslator` to resolve documented constants correctly.

  @pending
  Scenario: Translate key NT constants
    Given `WindowsNtSyscallTranslator::new()`
    When I translate constants `NT_CREATE_FILE`, `NT_READ_FILE`, `NT_WRITE_FILE`
    And I translate constants `NT_ALLOCATE_VIRTUAL_MEMORY`, `NT_WAIT_FOR_SINGLE_OBJECT`
    Then I receive expected `WindowsSyscallName` variants for each

