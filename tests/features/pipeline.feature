Feature: Full harness pipeline
  Quiver runs intake, analysis, tailoring, and email drafting end to end,
  then reviews both the resume and the email for honesty.

  Scenario: A run produces every artifact and reviews the resume and the email
    Given a pipeline backed by stub agents
    When I run the pipeline on a pasted job description
    Then it produces a posting, a match report, a resume, and an email
    And both the resume and the email have passed the review gate
