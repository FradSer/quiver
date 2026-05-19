"""Tailor: produce a job-tailored résumé from the profile and match report."""

from __future__ import annotations

from quiver.domain.models import CandidateProfile, JobPosting, ResumeDraft
from quiver.domain.ports import AgentRunner

_SYSTEM_PROMPT = """\
You tailor résumés for Quiver, a job-search harness.

Given a candidate profile, a job description, and a match report, write a résumé
in Markdown that is tailored to this job. Return ONLY the résumé Markdown — no
prose around it, no fences.

Rules:
- Use ONLY facts present in the profile. Never invent experience, numbers,
  titles, or projects.
- Do not cite GitHub star or follower counts as headline numbers.
- Lead with the evidence most relevant to this job's requirements.
- Be honest: do not paper over the gaps named in the match report.
"""


class TailorError(Exception):
    """Raised when the tailor produced no usable résumé."""


class TailorService:
    """Produces a tailored résumé from a profile, posting, and match report."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def tailor(
        self, profile: CandidateProfile, posting: JobPosting, report_markdown: str
    ) -> ResumeDraft:
        """Write a résumé tailored to `posting`; return it as a ResumeDraft."""
        prompt = (
            f"# Candidate profile\n\n{profile.raw_markdown}\n\n"
            f"# Job description\n\n{posting.to_markdown()}\n\n"
            f"# Match report\n\n{report_markdown}"
        )
        raw = await self._runner.run(prompt, system_prompt=_SYSTEM_PROMPT)
        if not raw.strip():
            raise TailorError("tailor produced an empty résumé")
        return ResumeDraft(posting=posting, markdown=raw.strip())
