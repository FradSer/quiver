Feature: Candidate-to-job match analysis
  Quiver produces an honest, evidence-based match report.

  Scenario: A structured report covers assessments, gaps, and risks
    Given an analyst backed by a stub assessor
    When I analyze the candidate against the job
    Then the report has per-requirement assessments, a gaps section, and a risks section

  Scenario: An unverified job description is flagged
    Given a job posting whose source was not verified
    When I render its match report
    Then the report header carries an unverified-JD warning
