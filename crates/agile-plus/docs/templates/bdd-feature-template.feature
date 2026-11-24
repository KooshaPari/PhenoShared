# Template: BDD feature for a journey page
# Owner: docs/journeys/README.md (mirrors hwLedger add-rich-journey-embeds-to-docs-v10)
# Linked spec: kitty-specs/eco-022-rich-journey-embeds/spec.md
# Linked journey: docs/journeys/<journey-id>.md
# Linked FR: <fr_id>
#
# Copy this file to `specs/<spec_slug>/bdd/<journey-id>.feature` and
# rename `Feature:` and `Scenario:` titles. Tag every Scenario with the
# matching `@fr-XXX` tag so tooling/trace-validator (eco-024) can
# bind scenarios to FR rows in FUNCTIONAL_REQUIREMENTS.md.
#
# Hard rules (enforced by eco-021 docs gate):
#   - One Feature per journey page.
#   - One Background per Feature.
#   - One Scenario per Acceptance Criterion in the journey page.
#   - Every Scenario has a stable @fr-XXX tag.
#   - Renaming a Scenario is a breaking change to the BDD contract;
#     the linked journey page's Traceability table must be updated
#     in the same PR.

@journey=<journey-id>
@fr=<FR-XXX-NNN>
@spec=<kitty-spec-slug>
Feature: <Human-Readable Title>
  As a <role>
  I want <capability>
  So that <outcome>

  Background:
    Given <precondition common to all scenarios>
    And <precondition common to all scenarios>

  @fr=<FR-XXX-NNN> @ac=1
  Scenario: AC1 — <short criterion name>
    When <action>
    And <action>
    Then <observable outcome>
    And <observable outcome>

  @fr=<FR-XXX-NNN> @ac=2
  Scenario: AC2 — <short criterion name>
    When <action>
    Then <observable outcome>
    And <observable outcome>

  @fr=<FR-XXX-NNN> @ac=3
  Scenario: AC3 — <short criterion name>
    When <action>
    And <action>
    Then <observable outcome>
    And <observable outcome>

  @fr=<FR-XXX-NNN> @ac=4
  Scenario: AC4 — <short criterion name>
    When <action>
    Then <observable outcome>
    And <observable outcome>
