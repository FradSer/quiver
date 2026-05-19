"""BDD steps for evaluation-harness scoring (offline — pure scoring functions)."""

from __future__ import annotations

from pytest_bdd import given, scenarios, then, when

from quiver.domain.models import ReviewIssue, ReviewResult
from quiver.evaluation.models import CaseOutcome, ReviewerCase
from quiver.evaluation.scoring import score_reviewer

scenarios("../features/evaluation.feature")


@given("a planted-overclaim reviewer case", target_fixture="case")
def _case() -> ReviewerCase:
    return ReviewerCase(
        case_id="planted",
        profile_md="# profile",
        artifact_md="# 简历\n\n- OpenClaw 核心维护者。",
        should_flag=True,
        must_catch="维护",
    )


@when("the reviewer leaves the artifact clean", target_fixture="outcome")
def _clean(case: ReviewerCase) -> CaseOutcome:
    return score_reviewer(case, ReviewResult(issues=()))


@when("the reviewer flags the planted overclaim", target_fixture="outcome")
def _flagged(case: ReviewerCase) -> CaseOutcome:
    return score_reviewer(
        case, ReviewResult(issues=(ReviewIssue("OpenClaw 核心维护者", "档案无支撑"),))
    )


@then("the eval case fails")
def _fails(outcome: CaseOutcome) -> None:
    assert not outcome.passed


@then("the eval case passes")
def _passes(outcome: CaseOutcome) -> None:
    assert outcome.passed
