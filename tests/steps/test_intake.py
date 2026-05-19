"""BDD steps for job-description intake (offline — uses a stub extractor)."""

from __future__ import annotations

import asyncio
import json

from pytest_bdd import given, scenarios, then, when

from quiver.application.intake import IntakeService, JdUnavailableError
from quiver.domain.models import JobPosting, VerificationStatus
from tests.fakes import FakeAgentRunner

scenarios("../features/intake.feature")

_GOOD_JSON = json.dumps(
    {
        "available": True,
        "title": "Agent Harness 产品经理",
        "company": "DeepSeek",
        "location": "北京市",
        "responsibilities": ["规划 Harness 产品路线图"],
        "requirements": ["2 年以上产品经理经验"],
        "bonuses": ["深度参与开源社区"],
        "contact": "",
    }
)
_UNREADABLE_JSON = json.dumps({"available": False, "reason": "page is a JS app shell"})


@given("an intake service backed by a stub extractor", target_fixture="service")
def _service_ok() -> IntakeService:
    return IntakeService(FakeAgentRunner(_GOOD_JSON))


@given(
    "an intake service whose extractor cannot read the page",
    target_fixture="service",
)
def _service_unreadable() -> IntakeService:
    return IntakeService(FakeAgentRunner(_UNREADABLE_JSON))


@when("I intake a pasted job description", target_fixture="outcome")
def _intake_text(service: IntakeService) -> object:
    return asyncio.run(service.from_text("Agent Harness 产品经理 — DeepSeek"))


@when("I intake a job URL", target_fixture="outcome")
def _intake_url(service: IntakeService) -> object:
    try:
        return asyncio.run(service.from_url("https://example.com/jobs/1"))
    except JdUnavailableError as exc:
        return exc


@then("I get a structured posting marked as pasted")
def _posting_is_pasted(outcome: object) -> None:
    assert isinstance(outcome, JobPosting)
    assert outcome.verification_status is VerificationStatus.PASTED
    assert outcome.company == "DeepSeek"
    assert outcome.responsibilities


@then("intake fails and asks for pasted text")
def _intake_failed(outcome: object) -> None:
    assert isinstance(outcome, JdUnavailableError)
