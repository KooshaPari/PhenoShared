Feature: FR-9 Compatibility and runtime adapters are instantiable
  In order to initialize core integration points
  As a caller
  I want zero-arg constructors to succeed.

  @pending
  Scenario: Create compatibility and runtime objects
    Given module types `CompatibilityLayer` and `NvmsRuntime`
    When I call `new()` and `default()` on both types
    Then all constructors return values successfully
    And `Default` and `new` produce equivalent construction paths

