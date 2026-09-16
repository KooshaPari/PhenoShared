Feature: FR-14 Core typed model objects are explicitly constructible
  In order to keep public domain types explicit
  As a caller
  I want core wrappers and descriptor models to expose expected constructor and field behavior.

  @pending
  Scenario: Construct typed models and inspect fields
    Given a `ProcessId`, `SyscallNumber`, `AssetId`, `AssetDescriptor`, `Symbol`, `Section`, and `ProcessSnapshot`
    When I initialize those values via constructors or literals
    Then all field values are accessible and match expected inputs
    And no direct ad-hoc stringly-typed state is required

