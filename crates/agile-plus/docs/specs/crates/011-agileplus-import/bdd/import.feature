Feature: AgilePlus import adapter
  As a migration operator
  I want to import PM data from external sources
  So that AgilePlus work packages reflect upstream state

  Background:
    Given an Importer port wired with a CSV adapter
    And an empty AgilePlus domain store

  Scenario: Idempotent re-import
    Given a manifest pointing at 10 CSV rows
    When the importer runs twice
    Then the second run creates zero new rows
    And the second run returns skipped == 10

  Scenario: Surface failures as events
    Given a manifest with one malformed row
    When the importer runs
    Then it returns failed == 1
    And it emits an ImportEvent::Failed for that row
