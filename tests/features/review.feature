Feature: Artifact fact-check
  Quiver reviews generated artifacts for honesty before they ship.

  Scenario: An overclaim is flagged
    Given a reviewer that finds an overclaim
    When I review an artifact
    Then the review is not clean and names the issue

  Scenario: An honest artifact passes review
    Given a reviewer that finds nothing wrong
    When I review an artifact
    Then the review is clean

  Scenario: The reviewer can verify GitHub repositories against the live record
    Given a reviewer that finds nothing wrong
    When I review an artifact
    Then the reviewer is equipped with the verify_github tool
