"""Unit tests for the intake service (offline — uses a fake agent runner)."""

import asyncio
import json

import pytest

from quiver.application.intake import IntakeService, JdUnavailableError
from quiver.domain.models import JobPosting, VerificationStatus
from tests.fakes import FakeAgentRunner

_GOOD = json.dumps(
    {
        "available": True,
        "title": "Agent Harness PM",
        "company": "DeepSeek",
        "location": "Beijing",
        "responsibilities": ["Plan the Harness roadmap"],
        "requirements": ["2+ years as a PM"],
        "bonuses": ["Open-source community work"],
        "contact": "",
    }
)


def test_from_text_builds_a_pasted_posting() -> None:
    service = IntakeService(FakeAgentRunner(_GOOD))
    posting = asyncio.run(service.from_text("Agent Harness PM at DeepSeek..."))
    assert isinstance(posting, JobPosting)
    assert posting.company == "DeepSeek"
    assert posting.verification_status is VerificationStatus.PASTED
    assert posting.responsibilities == ("Plan the Harness roadmap",)


def test_from_url_marks_source_verified() -> None:
    service = IntakeService(FakeAgentRunner(_GOOD))
    posting = asyncio.run(service.from_url("https://example.com/job"))
    assert posting.verification_status is VerificationStatus.SOURCE_VERIFIED
    assert posting.source_url == "https://example.com/job"


def test_from_text_rejects_empty_input() -> None:
    service = IntakeService(FakeAgentRunner(_GOOD))
    with pytest.raises(JdUnavailableError):
        asyncio.run(service.from_text("   "))


def test_unavailable_when_agent_reports_not_available() -> None:
    runner = FakeAgentRunner(json.dumps({"available": False, "reason": "JS app shell"}))
    with pytest.raises(JdUnavailableError, match="JS app shell"):
        asyncio.run(IntakeService(runner).from_url("https://example.com/spa"))


def test_rejects_response_without_json() -> None:
    service = IntakeService(FakeAgentRunner("sorry, I could not help"))
    with pytest.raises(JdUnavailableError):
        asyncio.run(service.from_text("some jd text"))


def test_rejects_extraction_missing_company() -> None:
    runner = FakeAgentRunner(json.dumps({"available": True, "title": "PM"}))
    with pytest.raises(JdUnavailableError):
        asyncio.run(IntakeService(runner).from_text("some jd text"))
