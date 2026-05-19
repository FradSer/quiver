"""Pure scoring functions for the evaluation harness.

No IO, no agent calls — each function takes an eval case and an agent's output
and returns a CaseOutcome. This is the part of the harness that is unit-tested
offline.
"""

from __future__ import annotations

from quiver.domain.models import JobPosting, MatchRating, MatchReport, ReviewResult
from quiver.evaluation.models import (
    AnalystCase,
    CaseKind,
    CaseOutcome,
    IntakeCase,
    ReviewerCase,
)


def score_reviewer(case: ReviewerCase, result: ReviewResult) -> CaseOutcome:
    """Score a reviewer result against the case's expected verdict."""
    flagged = not result.is_clean
    if case.should_flag:
        caught = flagged and (
            not case.must_catch
            or any(case.must_catch in (i.claim + i.problem) for i in result.issues)
        )
        detail = (
            f"planted overclaim {'caught' if caught else 'MISSED'} "
            f"({len(result.issues)} issue(s) flagged)"
        )
        return CaseOutcome(case.case_id, CaseKind.REVIEWER, caught, detail)
    passed = not flagged
    detail = (
        "honest artifact left clean"
        if passed
        else f"FALSE POSITIVE: {len(result.issues)} issue(s) on an honest artifact"
    )
    return CaseOutcome(case.case_id, CaseKind.REVIEWER, passed, detail)


def score_intake(case: IntakeCase, posting: JobPosting) -> CaseOutcome:
    """Score an intake result for requirement coverage and verification status."""
    haystack = " ".join((*posting.requirements, *posting.responsibilities)).lower()
    found = [r for r in case.expected_requirements if r.lower() in haystack]
    coverage = len(found) / len(case.expected_requirements)
    status_ok = posting.verification_status.value == "pasted"
    passed = coverage >= case.min_coverage and status_ok
    detail = (
        f"coverage {len(found)}/{len(case.expected_requirements)} ({coverage:.0%}), "
        f"verification={posting.verification_status.value}"
    )
    return CaseOutcome(case.case_id, CaseKind.INTAKE, passed, detail)


def score_analyst(case: AnalystCase, report: MatchReport) -> CaseOutcome:
    """Score an analyst report for honest calibration of a known gap and strength."""

    def rating_for(substr: str) -> MatchRating | None:
        for assessment in report.assessments:
            if substr.lower() in assessment.requirement.lower():
                return assessment.rating
        return None

    gap_rating = rating_for(case.expected_gap)
    strong_rating = rating_for(case.expected_strong)
    gap_ok = gap_rating in (MatchRating.GAP, MatchRating.PARTIAL)
    strong_ok = strong_rating is MatchRating.STRONG
    not_all_strong = any(a.rating is not MatchRating.STRONG for a in report.assessments)
    passed = gap_ok and strong_ok and not_all_strong
    detail = (
        f"known gap rated {gap_rating.label if gap_rating else 'MISSING'}; "
        f"known strength rated {strong_rating.label if strong_rating else 'MISSING'}; "
        f"calibrated={'yes' if not_all_strong else 'NO — all strong'}"
    )
    return CaseOutcome(case.case_id, CaseKind.ANALYST, passed, detail)
