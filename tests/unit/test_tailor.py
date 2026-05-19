"""Unit tests for the tailor service (offline — uses a fake agent runner)."""

import asyncio

import pytest

from quiver.application.tailor import TailorError, TailorService
from quiver.domain.models import CandidateProfile, JobPosting
from tests.fakes import FakeAgentRunner

_PROFILE = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ years in product.")
_POSTING = JobPosting(title="Agent Harness PM", company="DeepSeek")


def test_tailor_produces_a_resume_draft() -> None:
    runner = FakeAgentRunner("# Frad LEE\n\nTailored résumé.")
    resume = asyncio.run(TailorService(runner).tailor(_PROFILE, _POSTING, "# Match report"))
    assert resume.markdown.startswith("# Frad LEE")
    assert resume.posting is _POSTING


def test_tailor_rejects_empty_output() -> None:
    with pytest.raises(TailorError):
        asyncio.run(TailorService(FakeAgentRunner("   ")).tailor(_PROFILE, _POSTING, "# r"))
