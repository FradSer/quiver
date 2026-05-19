"""Unit tests for the evaluation scoring functions (pure, offline)."""

from quiver.domain.models import (
    JobPosting,
    MatchRating,
    MatchReport,
    RequirementAssessment,
    ReviewIssue,
    ReviewResult,
    VerificationStatus,
)
from quiver.evaluation.cases import REVIEWER_CASES
from quiver.evaluation.models import AnalystCase, CaseKind, CaseOutcome, EvalReport, IntakeCase
from quiver.evaluation.scoring import score_analyst, score_intake, score_reviewer

_PLANTED = next(c for c in REVIEWER_CASES if c.case_id == "reviewer-overclaim-maintainer")
_HONEST = next(c for c in REVIEWER_CASES if c.case_id == "reviewer-honest-dotclaude")


def test_score_reviewer_planted_caught() -> None:
    result = ReviewResult(issues=(ReviewIssue("OpenClaw 核心维护者", "档案说非维护者"),))
    assert score_reviewer(_PLANTED, result).passed


def test_score_reviewer_planted_missed() -> None:
    assert not score_reviewer(_PLANTED, ReviewResult(issues=())).passed


def test_score_reviewer_planted_caught_but_wrong_issue() -> None:
    # Flagged something, but not the planted overclaim — does not count as caught.
    result = ReviewResult(issues=(ReviewIssue("无关问题", "拼写"),))
    assert not score_reviewer(_PLANTED, result).passed


def test_score_reviewer_honest_left_clean() -> None:
    assert score_reviewer(_HONEST, ReviewResult(issues=())).passed


def test_score_reviewer_honest_false_positive() -> None:
    result = ReviewResult(issues=(ReviewIssue("dotclaude", "误判"),))
    assert not score_reviewer(_HONEST, result).passed


def test_score_intake_full_coverage_passes() -> None:
    case = IntakeCase(case_id="i", jd_text="", expected_requirements=("SQL", "本科"))
    posting = JobPosting(
        title="x",
        company="y",
        requirements=("熟悉 SQL", "本科及以上"),
        verification_status=VerificationStatus.PASTED,
    )
    assert score_intake(case, posting).passed


def test_score_intake_low_coverage_fails() -> None:
    case = IntakeCase(case_id="i", jd_text="", expected_requirements=("SQL", "本科", "B 端"))
    posting = JobPosting(
        title="x",
        company="y",
        requirements=("熟悉 SQL",),
        verification_status=VerificationStatus.PASTED,
    )
    assert not score_intake(case, posting).passed


def _analyst_case() -> AnalystCase:
    return AnalystCase(
        case_id="a",
        profile_md="# x",
        posting=JobPosting(title="x", company="y"),
        expected_gap="finance",
        expected_strong="code",
    )


def _report(gap: MatchRating, strong: MatchRating) -> MatchReport:
    return MatchReport(
        posting=JobPosting(title="x", company="y"),
        assessments=(
            RequirementAssessment("10 years finance", gap, "e"),
            RequirementAssessment("writes code", strong, "e"),
        ),
        gaps=(),
        risks=(),
        verdict="v",
    )


def test_score_analyst_calibrated_passes() -> None:
    report = _report(gap=MatchRating.GAP, strong=MatchRating.STRONG)
    assert score_analyst(_analyst_case(), report).passed


def test_score_analyst_overrated_gap_fails() -> None:
    report = _report(gap=MatchRating.STRONG, strong=MatchRating.STRONG)
    outcome = score_analyst(_analyst_case(), report)
    assert not outcome.passed


def test_eval_report_verdict_fails_on_gating_failure() -> None:
    report = EvalReport(
        outcomes=(
            CaseOutcome("ok", CaseKind.REVIEWER, True, ""),
            CaseOutcome("bad", CaseKind.REVIEWER, False, ""),
        ),
        reviewer_recall=(1, 2),
        reviewer_precision=(1, 1),
    )
    assert report.verdict_failed


def test_eval_report_verdict_ignores_informational_e2e() -> None:
    report = EvalReport(
        outcomes=(
            CaseOutcome("ok", CaseKind.REVIEWER, True, ""),
            CaseOutcome("e2e", CaseKind.E2E, False, "", gating=False),
        ),
        reviewer_recall=(1, 1),
        reviewer_precision=(0, 0),
    )
    assert not report.verdict_failed
