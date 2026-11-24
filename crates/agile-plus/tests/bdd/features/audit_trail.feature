@evidence @audit @mcp
Feature: Audit Trail

  As an MCP client
  I want to query the audit trail for evidence records
  So that I can verify compliance and reconstruct work history

  Scenario: audit_trail is queryable by work_package_id
    Given evidence records exist for work_package "WP-042"
    When the client queries audit_trail with work_package_id "WP-042"
    Then the response contains all evidence records for that work package
    And records are ordered by timestamp ascending

  Scenario: audit_trail filters by evidence_type
    Given evidence records of type "test_result" and "ci_output" for "WP-042"
    When the client queries audit_trail with work_package_id "WP-042" and evidence_type "test_result"
    Then the response contains only records with evidence_type "test_result"

  Scenario: audit_trail filters by date range
    Given evidence records spanning multiple days
    When the client queries audit_trail with from and to date filters
    Then the response contains only records within the inclusive date range

  Scenario: audit_trail returns empty for unknown work package
    Given no evidence records exist for work_package "WP-UNKNOWN"
    When the client queries audit_trail with work_package_id "WP-UNKNOWN"
    Then the response is an empty list
    And the response includes a pagination block with total zero
