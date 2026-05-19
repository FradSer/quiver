"""Unit tests for the writer service (offline — uses a fake agent runner)."""

import asyncio
import json

import pytest

from quiver.application.writer import WriterError, WriterService
from quiver.domain.models import CandidateProfile, JobPosting
from tests.fakes import FakeAgentRunner

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ years in product.")
_POSTING = JobPosting(title="Agent Harness PM", company="DeepSeek")


def test_write_produces_an_email_draft() -> None:
    payload = json.dumps({"subject": "Application — Agent Harness PM", "body": "Hello."})
    draft = asyncio.run(WriterService(FakeAgentRunner(payload)).write(_PROFILE, _POSTING, "# r"))
    assert draft.subject == "Application — Agent Harness PM"
    assert draft.body == "Hello."


def test_write_rejects_missing_body() -> None:
    payload = json.dumps({"subject": "only a subject"})
    with pytest.raises(WriterError):
        asyncio.run(WriterService(FakeAgentRunner(payload)).write(_PROFILE, _POSTING, "# r"))


def test_write_rejects_non_json() -> None:
    with pytest.raises(WriterError):
        asyncio.run(WriterService(FakeAgentRunner("no json")).write(_PROFILE, _POSTING, "# r"))
