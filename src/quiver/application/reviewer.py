"""Reviewer: the fact-check gate — flags dishonesty before an artifact ships."""

from __future__ import annotations

from quiver.application.extraction import JsonExtractionError, parse_json_object
from quiver.domain.models import CandidateProfile, ReviewIssue, ReviewResult
from quiver.domain.ports import AgentRunner

_SYSTEM_PROMPT = """\
You are the fact-check reviewer for Quiver, a job-search harness. Catch dishonesty
before an artifact reaches the user.

You are given the candidate's profile (the source of truth) and a generated
artifact (a match report, résumé, or email). Return ONLY a JSON object:
  "issues": array of objects, each {"claim": string, "problem": string}

Flag a claim when it:
- states experience, a title, a number, or a project not supported by the profile
- inflates a role (e.g. "core maintainer" when the profile shows minor contributions)
- cites a number (GitHub stars, years, counts) that contradicts the profile or is
  not traceable to it — a figure faithfully copied from the profile is NOT an issue
- treats an unverified job description as established fact

Return {"issues": []} if the artifact is honest and supported by the profile.
Do NOT flag wording, paraphrase, generalisation, or omitted detail — these are not
dishonesty. Flag only claims the profile contradicts or does not support, or that
materially overstate the candidate. When in doubt, do not flag.
"""


class ReviewError(Exception):
    """Raised when the reviewer could not produce a usable result."""


class ReviewerService:
    """Reviews a generated artifact against the profile for honesty."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def review(self, profile: CandidateProfile, artifact_markdown: str) -> ReviewResult:
        """Review `artifact_markdown` against the profile; return found issues."""
        prompt = (
            f"# Candidate profile (source of truth)\n\n{profile.raw_markdown}\n\n"
            f"# Generated artifact to review\n\n{artifact_markdown}"
        )
        raw = await self._runner.run(prompt, system_prompt=_SYSTEM_PROMPT)
        try:
            data = parse_json_object(raw)
        except JsonExtractionError as exc:
            raise ReviewError(str(exc)) from exc
        issues = tuple(
            ReviewIssue(
                claim=str(item.get("claim") or "").strip(),
                problem=str(item.get("problem") or "").strip(),
            )
            for item in (data.get("issues") or [])
            if isinstance(item, dict)
        )
        return ReviewResult(issues=issues)
