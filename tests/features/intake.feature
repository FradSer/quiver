Feature: Job description intake
  Quiver turns a job description into a structured, provenance-tagged posting.

  Scenario: Pasted text becomes a structured posting
    Given an intake service backed by a stub extractor
    When I intake a pasted job description
    Then I get a structured posting marked as pasted

  Scenario: An unreadable URL is reported, not faked
    Given an intake service whose extractor cannot read the page
    When I intake a job URL
    Then intake fails and asks for pasted text
