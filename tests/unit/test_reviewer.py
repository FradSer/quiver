"""Unit tests for the reviewer service (offline — uses a fake agent runner)."""

import asyncio
import json

import pytest

from quiver.application.reviewer import ReviewError, ReviewerService
from quiver.domain.models import CandidateProfile
from tests.fakes import FakeAgentRunner

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE\n\n8 PRs to OpenClaw.")


def test_review_flags_an_overclaim() -> None:
    payload = json.dumps({"issues": [{"claim": "核心维护者", "problem": "profile 仅显示 8 个 PR"}]})
    result = asyncio.run(ReviewerService(FakeAgentRunner(payload)).review(_PROFILE, "# x"))
    assert not result.is_clean
    assert result.issues[0].claim == "核心维护者"


def test_review_passes_an_honest_artifact() -> None:
    result = asyncio.run(
        ReviewerService(FakeAgentRunner(json.dumps({"issues": []}))).review(_PROFILE, "# x")
    )
    assert result.is_clean


def test_review_rejects_non_json() -> None:
    with pytest.raises(ReviewError):
        asyncio.run(ReviewerService(FakeAgentRunner("not json")).review(_PROFILE, "# x"))
