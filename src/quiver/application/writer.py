"""Writer: draft an application email from the profile and match report."""

from __future__ import annotations

from quiver.application.extraction import JsonExtractionError, parse_json_object
from quiver.domain.models import CandidateProfile, EmailDraft, JobPosting
from quiver.domain.ports import AgentRunner

_SYSTEM_PROMPT = """\
You draft application emails for Quiver, a job-search harness.

Given a candidate profile, a job description, and a match report, return ONLY a
JSON object — no prose, no fences — with these keys:
  "subject": string — a concise email subject line
  "body": string — the email body, a few short paragraphs

Rules:
- Use ONLY facts present in the profile. Never invent experience or numbers.
- Reference 2-3 concrete, JD-relevant projects from the profile.
- Be direct and honest; no inflated claims.
"""


class WriterError(Exception):
    """Raised when the writer produced no usable email."""


class WriterService:
    """Produces an application email from a profile, posting, and match report."""

    def __init__(self, runner: AgentRunner) -> None:
        self._runner = runner

    async def write(
        self, profile: CandidateProfile, posting: JobPosting, report_markdown: str
    ) -> EmailDraft:
        """Draft an application email for `posting`; return it as an EmailDraft."""
        prompt = (
            f"# Candidate profile\n\n{profile.raw_markdown}\n\n"
            f"# Job description\n\n{posting.to_markdown()}\n\n"
            f"# Match report\n\n{report_markdown}"
        )
        raw = await self._runner.run(prompt, system_prompt=_SYSTEM_PROMPT)
        try:
            data = parse_json_object(raw)
        except JsonExtractionError as exc:
            raise WriterError(str(exc)) from exc
        subject = str(data.get("subject") or "").strip()
        body = str(data.get("body") or "").strip()
        if not subject or not body:
            raise WriterError("email draft is missing a subject or body")
        return EmailDraft(posting=posting, subject=subject, body=body)
