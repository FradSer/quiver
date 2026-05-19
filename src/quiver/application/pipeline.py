"""The harness pipeline: intake -> analyst -> tailor -> writer, with review gates."""

from __future__ import annotations

from dataclasses import dataclass

from quiver.application.analyst import AnalystService
from quiver.application.intake import IntakeService
from quiver.application.reviewer import ReviewerService
from quiver.application.tailor import TailorService
from quiver.application.writer import WriterService
from quiver.domain.models import (
    CandidateProfile,
    EmailDraft,
    JobPosting,
    MatchReport,
    ResumeDraft,
    ReviewResult,
)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Everything one pipeline run produced, including the review gates."""

    posting: JobPosting
    report: MatchReport
    resume: ResumeDraft
    email: EmailDraft
    resume_review: ReviewResult
    email_review: ReviewResult


class Pipeline:
    """Runs intake -> analyst -> tailor -> writer, then reviews the resume and email."""

    def __init__(
        self,
        *,
        intake: IntakeService,
        analyst: AnalystService,
        tailor: TailorService,
        writer: WriterService,
        reviewer: ReviewerService,
    ) -> None:
        self._intake = intake
        self._analyst = analyst
        self._tailor = tailor
        self._writer = writer
        self._reviewer = reviewer

    async def run(self, jd_text: str, profile: CandidateProfile) -> PipelineResult:
        """Run the full pipeline on a pasted job description.

        Both candidate-facing artifacts — the résumé and the email — pass through
        the fact-check reviewer before the result is returned.
        """
        posting = await self._intake.from_text(jd_text)
        report = await self._analyst.analyze(profile, posting)
        report_md = report.to_markdown()
        resume = await self._tailor.tailor(profile, posting, report_md)
        email = await self._writer.write(profile, posting, report_md)
        resume_review = await self._reviewer.review(profile, resume.markdown)
        email_review = await self._reviewer.review(profile, email.to_markdown())
        return PipelineResult(
            posting=posting,
            report=report,
            resume=resume,
            email=email,
            resume_review=resume_review,
            email_review=email_review,
        )
