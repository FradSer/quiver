"""Intake: turn a job description (pasted text or a URL) into a structured JobPosting."""

from __future__ import annotations

from quiver.application.extraction import (
    JsonExtractionError,
    parse_json_object,
    str_tuple,
)
from quiver.domain.models import JobPosting, VerificationStatus
from quiver.domain.ports import AgentRunner

_SYSTEM_PROMPT = """\
You extract structured data from job descriptions for Quiver, a job-search harness.

Return ONLY a JSON object — no prose, no Markdown fences — with these keys:
  "available": boolean — true if a real job description was provided or readable
  "title": string
  "company": string
  "location": string — "" if not stated
  "responsibilities": array of strings
  "requirements": array of strings
  "bonuses": array of strings — nice-to-haves / "加分项"; [] if none
  "contact": string — application email or channel; "" if not stated

Rules:
- Copy faithfully from the source. Never invent, infer, or embellish.
- If given a URL you cannot fetch or read a real job description from
  (e.g. a JavaScript app shell), return {"available": false, "reason": "<short reason>"}.
- Keep each list item to a single concise line.
"""


class JdUnavailableError(Exception):
    """Raised when no readable job description could be obtained."""


class IntakeService:
    """Extracts a structured JobPosting from raw input using an agent."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def from_text(self, text: str) -> JobPosting:
        """Extract a posting from pasted job-description text."""
        if not text.strip():
            raise JdUnavailableError("empty job description text")
        raw = await self._runner.run(f"Job description:\n\n{text}", system_prompt=_SYSTEM_PROMPT)
        return _parse_posting(raw, status=VerificationStatus.PASTED, source_url="")

    async def from_url(self, url: str) -> JobPosting:
        """Fetch a job description from a URL and extract a posting.

        Best-effort: many job boards are JavaScript app shells the fetch cannot
        read, in which case JdUnavailableError is raised.
        """
        raw = await self._runner.run(
            f"Fetch this URL and extract the job description: {url}",
            system_prompt=_SYSTEM_PROMPT,
            allowed_tools=["WebFetch"],
        )
        return _parse_posting(raw, status=VerificationStatus.SOURCE_VERIFIED, source_url=url)


def _parse_posting(raw: str, *, status: VerificationStatus, source_url: str) -> JobPosting:
    """Parse an extraction agent's JSON response into a JobPosting."""
    try:
        data = parse_json_object(raw)
    except JsonExtractionError as exc:
        raise JdUnavailableError(str(exc)) from exc
    if data.get("available") is False:
        raise JdUnavailableError(str(data.get("reason") or "job description could not be read"))
    title = str(data.get("title") or "").strip()
    company = str(data.get("company") or "").strip()
    if not title or not company:
        raise JdUnavailableError("extraction is missing a title or company")
    return JobPosting(
        title=title,
        company=company,
        location=str(data.get("location") or "").strip(),
        responsibilities=str_tuple(data.get("responsibilities")),
        requirements=str_tuple(data.get("requirements")),
        bonuses=str_tuple(data.get("bonuses")),
        contact=str(data.get("contact") or "").strip(),
        source_url=source_url,
        verification_status=status,
    )
