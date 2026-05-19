"""Unit tests for the analyst service (offline — uses a fake agent runner)."""

import asyncio
import json

import pytest

from quiver.application.analyst import AnalysisError, AnalystService
from quiver.domain.models import CandidateProfile, JobPosting, MatchRating
from tests.fakes import FakeAgentRunner

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ years in product.")
_POSTING = JobPosting(title="Agent Harness PM", company="DeepSeek")

_GOOD = json.dumps(
    {
        "assessments": [
            {"requirement": "2+ years PM", "rating": "strong", "evidence": "10+ years"},
            {"requirement": "A/B testing", "rating": "gap", "evidence": "none shown"},
        ],
        "gaps": ["online A/B testing"],
        "risks": ["over-tenured for a 2-year role"],
        "verdict": "Strong fit with one real gap; apply.",
    }
)


def test_analyze_builds_a_match_report() -> None:
    report = asyncio.run(AnalystService(FakeAgentRunner(_GOOD)).analyze(_PROFILE, _POSTING))
    assert len(report.assessments) == 2
    assert report.assessments[0].rating is MatchRating.STRONG
    assert report.assessments[1].rating is MatchRating.GAP
    assert report.gaps == ("online A/B testing",)
    assert report.verdict


def test_unknown_rating_falls_back_to_partial() -> None:
    payload = json.dumps(
        {
            "assessments": [{"requirement": "r", "rating": "excellent", "evidence": "e"}],
            "verdict": "v",
        }
    )
    report = asyncio.run(AnalystService(FakeAgentRunner(payload)).analyze(_PROFILE, _POSTING))
    assert report.assessments[0].rating is MatchRating.PARTIAL


def test_analyze_rejects_response_without_json() -> None:
    with pytest.raises(AnalysisError):
        asyncio.run(AnalystService(FakeAgentRunner("no json here")).analyze(_PROFILE, _POSTING))


def test_analyze_rejects_empty_assessments() -> None:
    payload = json.dumps({"assessments": [], "verdict": "v"})
    with pytest.raises(AnalysisError):
        asyncio.run(AnalystService(FakeAgentRunner(payload)).analyze(_PROFILE, _POSTING))


def test_analyze_rejects_missing_verdict() -> None:
    payload = json.dumps({"assessments": [{"requirement": "r", "rating": "gap", "evidence": "e"}]})
    with pytest.raises(AnalysisError):
        asyncio.run(AnalystService(FakeAgentRunner(payload)).analyze(_PROFILE, _POSTING))
