"""Analyst: assess a candidate against a job posting and produce an honest MatchReport."""

from __future__ import annotations

from typing import Any

from quiver.application.extraction import (
    JsonExtractionError,
    parse_json_object,
    str_tuple,
)
from quiver.domain.models import (
    CandidateProfile,
    JobPosting,
    MatchRating,
    MatchReport,
    RequirementAssessment,
)
from quiver.domain.ports import AgentRunner

_SYSTEM_PROMPT = """\
You are the match analyst for Quiver, a job-search harness.

Given a candidate profile and a job description, return ONLY a JSON object
— no prose, no Markdown fences — with these keys:
  "assessments": array of objects, one per distinct JD requirement, each with:
      "requirement": string — the requirement, quoted from the JD
      "rating": one of "strong", "partial", "gap"
      "evidence": string — what in the profile supports it, or why it falls short
  "gaps": array of strings — concrete things the candidate lacks
  "risks": array of strings — what could sink the application
  "verdict": string — one honest paragraph: apply or not, and the biggest risk

Rules:
- Cite only evidence actually present in the profile. Never invent experience,
  numbers, titles, or projects.
- If the profile does not support a requirement, rate it "gap" — do not stretch.
- Be calibrated: rating everything "strong" is a failure. Most real candidates
  are "partial" on several requirements.
"""


class AnalysisError(Exception):
    """Raised when the analyst could not produce a usable match report."""


class AnalystService:
    """Produces a MatchReport from a profile and a job posting using an agent."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def analyze(self, profile: CandidateProfile, posting: JobPosting) -> MatchReport:
        """Assess the candidate against the posting and return a MatchReport."""
        prompt = (
            f"# Candidate profile\n\n{profile.raw_markdown}\n\n"
            f"# Job description\n\n{posting.to_markdown()}"
        )
        raw = await self._runner.run(prompt, system_prompt=_SYSTEM_PROMPT)
        return _parse_report(raw, posting)


def _parse_report(raw: str, posting: JobPosting) -> MatchReport:
    """Parse an analyst agent's JSON response into a MatchReport."""
    try:
        data = parse_json_object(raw)
    except JsonExtractionError as exc:
        raise AnalysisError(str(exc)) from exc
    assessments = tuple(
        _assessment(item) for item in (data.get("assessments") or []) if isinstance(item, dict)
    )
    if not assessments:
        raise AnalysisError("analysis produced no requirement assessments")
    verdict = str(data.get("verdict") or "").strip()
    if not verdict:
        raise AnalysisError("analysis produced no verdict")
    return MatchReport(
        posting=posting,
        assessments=assessments,
        gaps=str_tuple(data.get("gaps")),
        risks=str_tuple(data.get("risks")),
        verdict=verdict,
    )


def _assessment(item: dict[str, Any]) -> RequirementAssessment:
    """Build one RequirementAssessment from a JSON object."""
    return RequirementAssessment(
        requirement=str(item.get("requirement") or "").strip(),
        rating=_rating(str(item.get("rating") or "")),
        evidence=str(item.get("evidence") or "").strip(),
    )


def _rating(value: str) -> MatchRating:
    """Map an agent's rating string to a MatchRating, defaulting to PARTIAL."""
    try:
        return MatchRating(value.strip().lower())
    except ValueError:
        return MatchRating.PARTIAL
