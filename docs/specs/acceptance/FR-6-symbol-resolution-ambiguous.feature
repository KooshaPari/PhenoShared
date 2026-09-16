Feature: FR-6 Symbol resolution supports scoped and ambiguous resolution
  In order to resolve runtime symbols safely
  As a caller
  I want exact symbol resolution plus module-scoped lookups with ambiguity signaling.

  @pending
  Scenario: Resolve ambiguity and scoped resolution
    Given an `InMemorySymbolResolver` with duplicate `name` across modules
    When I call `resolve(name)`
    Then I receive `ResolveError::Ambiguous`
    When I call `resolve_in_module(name, module)`
    Then I receive the module-specific `Symbol`

