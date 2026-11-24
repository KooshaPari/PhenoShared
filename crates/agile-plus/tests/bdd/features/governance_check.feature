@governance @mcp
Feature: Governance Check

  As an MCP client
  I want to verify governance rules are satisfied
  So that work packages cannot advance without required evidence

  Scenario: check_governance returns valid response for a clean transition
    Given a governance rule for transition "implementing" to "validated"
    And required evidence types "test_result" and "ci_output"
    And a work package with all evidence satisfying thresholds
    When the client calls check_governance with work_package_id and transition
    Then the response status is "pass"
    And the response includes the rule_id and matched evidence

  Scenario: check_governance returns failure when evidence is missing
    Given a governance rule for transition "implementing" to "validated"
    And a work package missing required evidence
    When the client calls check_governance with work_package_id and transition
    Then the response status is "fail"
    And the response includes a list of missing_evidence items

  Scenario: check_governance returns error for unknown transition
    Given a governance rule set loaded from the evidence ledger
    And a transition not defined in any rule
    When the client calls check_governance with work_package_id and transition
    Then the response status is "error"
    And the response message indicates unknown transition
