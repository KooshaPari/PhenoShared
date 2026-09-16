Feature: FR-5 Asset registry enforces registration and lookup contracts
  In order to keep process asset state safe
  As a caller
  I want duplicate assets rejected and missing assets reported through `AssetError`.

  @pending
  Scenario: Reject duplicate register and return not-found
    Given a new `InMemoryAssetRegistry`
    When I register an asset id once
    And I register the same id again
    Then I receive `AssetError::AlreadyRegistered`
    And `get` on an unknown id returns `AssetError::NotFound`
    And unknown `unregister` returns `false`

