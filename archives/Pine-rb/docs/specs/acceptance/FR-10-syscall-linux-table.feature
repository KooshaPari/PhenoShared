Feature: FR-10 Linux syscall translator maps known numbers
  In order to provide stable Linux translation behavior
  As a caller
  I want `X86_64SyscallTranslator` to map known syscall numbers and reject unknowns.

  @pending
  Scenario: Translate known and unknown syscall numbers
    Given `X86_64SyscallTranslator::new()`
    When I translate known numbers such as 0, 1, 2, 9, and 60
    Then each returns expected `SyscallResult.name`
    When I translate an unknown number
    Then I receive `SyscallError::UnknownSyscall`

