Feature: AgilePlus GitHub integration
  As a repo steward
  I want AgilePlus to sync with GitHub issues and PRs
  So that work packages stay aligned with upstream activity

  Background:
    Given a webhook handler with a configured secret
    And a GitHub adapter wired with the in-memory recorder

  Scenario: Duplicate webhook delivery is dropped
    Given a webhook payload with delivery ID "abc-123"
    When the same delivery is posted twice
    Then the second delivery is silently dropped

  Scenario: Invalid signature is rejected
    Given a webhook payload signed with the wrong secret
    When the handler is invoked
    Then the response is HTTP 401
