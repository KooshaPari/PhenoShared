Feature: FR-11 Linux constants are coherent with translator table
  In order to avoid mismatched wrappers
  As a caller
  I want Linux constant values to resolve through `translate`.

  @pending
  Scenario: Translate using documented constants
    Given `LinuxSyscallTranslator::new()`
    When I translate `LinuxSyscallTranslator::READ`
    And I translate `LinuxSyscallTranslator::OPENAT`
    And I translate `LinuxSyscallTranslator::GETRANDOM`
    Then each returns matching `SyscallName` values

