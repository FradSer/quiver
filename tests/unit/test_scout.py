"""Unit tests for the scout service (offline — uses a fake agent runner)."""

import asyncio
import json

from quiver.application.scout import ScoutService
from quiver.domain.models import CandidateProfile
from tests.fakes import FakeAgentRunner

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE")


def test_discover_returns_leads() -> None:
    payload = json.dumps(
        {"leads": [{"title": "PM", "company": "DeepSeek", "url": "https://x", "rationale": "fit"}]}
    )
    leads = asyncio.run(ScoutService(FakeAgentRunner(payload)).discover(_PROFILE))
    assert len(leads) == 1
    assert leads[0].company == "DeepSeek"


def test_discover_returns_empty_on_non_json() -> None:
    leads = asyncio.run(ScoutService(FakeAgentRunner("no leads here")).discover(_PROFILE))
    assert leads == ()


def test_discover_skips_blank_leads() -> None:
    payload = json.dumps({"leads": [{"title": "", "company": ""}, {"title": "PM", "company": "X"}]})
    leads = asyncio.run(ScoutService(FakeAgentRunner(payload)).discover(_PROFILE))
    assert len(leads) == 1
