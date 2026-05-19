Feature: Full harness pipeline
  Quiver runs intake, analysis, tailoring, and email drafting end to end.
  The match report, the resume, and the email each pass a review gate; a
  flagged artifact blocks the run rather than shipping.

  Scenario: A clean run produces every artifact and passes all three review gates
    Given a pipeline backed by stub agents
    When I run the pipeline on a pasted job description
    Then it produces a posting, a match report, a resume, and an email
    And the match report, the resume, and the email have all passed the review gate

  Scenario: A flagged match report blocks the pipeline
    Given a pipeline whose reviewer flags the match report
    When I run the pipeline on a pasted job description
    Then the pipeline is blocked at the match-report gate
    And no resume or email is produced
