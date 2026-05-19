"""BDD steps for artifact fact-check (offline — uses a stub reviewer)."""

from __future__ import annotations

import asyncio
import json

from pytest_bdd import given, scenarios, then, when

from quiver.application.reviewer import ReviewerService
from quiver.domain.models import CandidateProfile, ReviewResult
from tests.fakes import FakeAgentRunner

scenarios("../features/review.feature")

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE\n\n8 PRs to OpenClaw.")
_FLAG = json.dumps({"issues": [{"claim": "核心维护者", "problem": "profile 仅显示 8 个 PR"}]})
_CLEAN = json.dumps({"issues": []})


@given("a reviewer that finds an overclaim", target_fixture="runner")
def _runner_flags() -> FakeAgentRunner:
    return FakeAgentRunner(_FLAG)


@given("a reviewer that finds nothing wrong", target_fixture="runner")
def _runner_clean() -> FakeAgentRunner:
    return FakeAgentRunner(_CLEAN)


@when("I review an artifact", target_fixture="result")
def _review(runner: FakeAgentRunner) -> ReviewResult:
    return asyncio.run(ReviewerService(runner).review(_PROFILE, "# Résumé\n\nOpenClaw 核心维护者"))


@then("the review is not clean and names the issue")
def _flagged(result: ReviewResult) -> None:
    assert not result.is_clean
    assert result.issues[0].claim == "核心维护者"


@then("the review is clean")
def _clean(result: ReviewResult) -> None:
    assert result.is_clean


@then("the reviewer is equipped with the verify_github tool")
def _equipped(runner: FakeAgentRunner, result: ReviewResult) -> None:
    assert runner.last_allowed_tools is not None
    assert any("verify_github" in tool for tool in runner.last_allowed_tools)
