Feature: Dashboard service health endpoints
  As a dashboard operator
  I want real (non-mock) health checks for the backing services
  So that I can trust the /health and /services/health.json endpoints

  Background:
    Given a running `agileplus-dashboard` process
    And the HealthChecker port is wired with default adapters

  Scenario: SqliteChecker reports healthy
    When the SqliteChecker runs a check
    Then it returns healthy == true
    And it returns a non-negative latency in milliseconds

  Scenario: MemoryStoreChecker reports healthy
    When the MemoryStoreChecker runs a check
    Then it returns healthy == true
    And it returns a non-negative latency in milliseconds

  Scenario: ProcessChecker reports healthy
    When the ProcessChecker runs a check
    Then it returns healthy == true
    And it returns a non-negative latency in milliseconds

  Scenario: BuildInfoChecker reports healthy
    When the BuildInfoChecker runs a check
    Then it returns healthy == true
    And it returns a non-negative latency in milliseconds

  Scenario: run_health_checks returns all services
    When run_health_checks is invoked
    Then the result is a Vec with exactly 4 ServiceHealth entries
    And every entry has healthy == true

  Scenario: At least one service reports measurable latency
    When run_health_checks is invoked
    Then at least one entry has latency_ms == Some(_)

  Scenario: ServiceHealth shape is stable
    When any checker runs
    Then the resulting ServiceHealth has fields
      | field       | type        |
      | name        | String      |
      | healthy     | bool        |
      | degraded    | bool        |
      | latency_ms  | Option<u64> |
      | last_check  | DateTime    |

  Scenario: HealthChecker port contract
    When a HealthChecker is invoked
    Then the return type is a tuple (bool, Option<u64>)
    And the bool represents health
    And the Option<u64> represents latency in milliseconds
