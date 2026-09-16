Feature: FR-13 Plugin registry routes through base translator
  In order to support optional extension of syscall translation
  As a caller
  I want `PluginRegistry` to delegate known names to plugins and fallback to base translator.

  @pending
  Scenario: Registry fallback and routing behavior
    Given a `PluginRegistry` with a base `X86_64SyscallTranslator`
    And a registered plugin that supports `SyscallName::Read`
    When I translate syscall number 0
    Then output comes from plugin path
    When I translate a supported but unclaimed name
    Then output falls back to base translator

