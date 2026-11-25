@governance @transitions @mcp
Feature: Governance State Transitions

  As an MCP client
  I want to advance work packages through governance-valid transitions
  So that only evidence-satisfied changes are recorded in the ledger

  Scenario: Valid transition records a new evidence entry in the ledger
    Given a governance rule: "validated" to "shipped" requires evidence_type "review_approval"
    And a work package in "validated" state with review_approval evidence present
    When the client calls advance_transition with valid evidence
    Then a new evidence record is appended to the audit ledger
    And the work package state is updated to "shipped"

  Scenario: Transition blocked when required evidence threshold is not met
    Given a governance rule: "implementing" to "validated" requires min_coverage >= 80
    And a work package with test coverage of 65
    When the client calls advance_transition with insufficient evidence
    Then the transition is rejected
    And the response indicates which threshold was not met
    And no new evidence record is written to the ledger

  Scenario: Policy references are included in transition response
    Given a governance rule with policy_refs "POL-001" and "POL-002"
    When a transition is evaluated
    Then the response includes the policy_refs array
    And clients can use policy_refs to fetch governing documentation
