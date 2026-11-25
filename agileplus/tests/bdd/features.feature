Feature: Bidirectional Plane.so Sync
  As a project manager
  I want to sync features between AgilePlus and Plane.so
  So that I can manage work in both systems

  @sync @bdd
  Scenario: Pull features from Plane.so
    Given I am logged in as "test_user"
    And I navigate to "Sync"
    When I click "Pull from Plane.so"
    Then I should see "Sync in progress"
    And I should see "Features imported"
    And I should see a "Review Imported Features" button

  @sync @bdd
  Scenario: Push feature to Plane.so
    Given I am logged in as "test_user"
    And I navigate to "Features"
    When I click "Create Feature"
    And I enter "Test Feature" in "Feature Name"
    And I click "Save"
    And I click "Sync to Plane.so"
    Then I should see "Successfully published to Plane.so"
    And I should see "Plane Work Item ID"

  @sync @conflict @bdd
  Scenario: Detect and resolve sync conflicts
    Given I am logged in as "test_user"
    And I navigate to "Sync"
    When I click "Pull from Plane.so"
    And conflicts are detected
    Then I should see a conflict resolution table
    When I click "Merge" on "Feature A"
    Then I should see "Conflict resolved"

Feature: Feature Specification Management
  As a product owner
  I want to create and manage feature specifications
  So that I can track requirements and progress

  @spec @bdd
  Scenario: Create feature with PRD structure
    Given I am logged in as "test_user"
    And I navigate to "Features"
    When I click "New Feature"
    And I enter "Mobile Auth" in "Title"
    And I enter "FR-AUTH-001" in "Feature ID"
    And I click "Create Feature"
    Then I should see "Feature created successfully"

  @spec @hierarchy @bdd
  Scenario: View feature hierarchy
    Given I am logged in as "test_user"
    And I navigate to "Features"
    When I click on "Auth System"
    Then I should see "Overview"
    And I should see "User Stories"
    And I should see "Work Packages"
    And I should see "Specifications"

Feature: Work Package Management
  As a team lead
  I want to manage work packages
  So that I can track implementation progress

  @work @bdd
  Scenario: Create work package from feature
    Given I am logged in as "test_user"
    And I navigate to "Features"
    And I click on "API Design"
    When I click "Work Packages"
    And I click "Create Work Package"
    And I enter "Database Schema" in "Title"
    And I select "Implementation" in "Type"
    And I click "Create"
    Then I should see "Work Package created"
    And I should see link "Parent: API Design"

  @work @kanban @bdd
  Scenario: Move work package on kanban
    Given I am logged in as "test_user"
    And I navigate to "Work Packages"
    Then I should see column "Backlog"
    And I should see column "In Progress"
    And I should see column "Review"
    And I should see column "Done"
    When I drag "Database Schema" to "In Progress"
    Then "Database Schema" should be in "In Progress"

Feature: Dashboard and Analytics
  As a stakeholder
  I want to view project metrics
  So that I can track progress

  @dashboard @bdd
  Scenario: View dashboard metrics
    Given I am logged in as "test_user"
    And I navigate to "Dashboard"
    Then I should see metric "Active Features"
    And I should see metric "Completed Work Packages"
    And I should see chart "Velocity Trend"
    When I click "Last 30 Days"
    Then the chart values should update

  @dashboard @drilldown @bdd
  Scenario: Drill down from chart
    Given I am logged in as "test_user"
    And I navigate to "Dashboard"
    When I click on bar in "Work Package Completion"
    Then I should see "Work Packages for March 2026"
    And I should see a table of work packages

Feature: Responsive UI
  As a user
  I want the app to work on all devices
  So that I can use it anywhere

  @ui @responsive @bdd
  Scenario: Mobile hamburger menu
    Given the viewport is set to mobile
    And I navigate to "Dashboard"
    Then I should see hamburger menu
    When I click the hamburger menu
    Then I should see menu with "Features"
    And I should see menu with "Work Packages"
    And I should see menu with "Sync"

  @ui @accessibility @bdd
  Scenario: Keyboard navigation
    Given I am logged in as "test_user"
    And I navigate to "Dashboard"
    When I press Tab 3 times
    Then focused element should be "Features" link
    When I press Enter
    Then I should be on "Features" page
