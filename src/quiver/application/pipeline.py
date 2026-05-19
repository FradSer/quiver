"""The harness pipeline: intake -> analyst -> tailor -> writer, with review gates.

Every artifact built on the candidate's facts — the match report, the resume,
and the email — passes the fact-check reviewer. A gate that flags issues raises
PipelineGateError and blocks every downstream step: a dishonest artifact never
ships. This is the harness's enforcement layer; it lives here, in orchestration,
because no agent writes files itself for a tool-use hook to intercept.
"""

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
    """Everything one pipeline run produced. Reaching this means every gate passed."""

    posting: JobPosting
    report: MatchReport
    resume: ResumeDraft
    email: EmailDraft
    report_review: ReviewResult
    resume_review: ReviewResult
    email_review: ReviewResult


class PipelineGateError(Exception):
    """Raised when a review gate flags honesty issues — the run is blocked.

    Carries the stage that failed and the unclean reviews, keyed by artifact
    filename, so the caller can report exactly what was rejected.
    """

    def __init__(self, stage: str, reviews: tuple[tuple[str, ReviewResult], ...]) -> None:
        self.stage = stage
        self.reviews = reviews
        flagged = ", ".join(f"{name} ({len(review.issues)})" for name, review in reviews)
        super().__init__(f"{stage} gate blocked the run — flagged: {flagged}")


class Pipeline:
    """Runs intake -> analyst -> tailor -> writer; gates every fact-bearing artifact."""

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

        The match report is gated before the resume and email are written, so a
        dishonest report never seeds downstream artifacts. The resume and email
        are then gated together. Any flagged gate raises PipelineGateError.
        """
        posting = await self._intake.from_text(jd_text)
        report = await self._analyst.analyze(profile, posting)
        report_md = report.to_markdown()
        report_review = await self._reviewer.review(profile, report_md)
        if not report_review.is_clean:
            raise PipelineGateError("match-report", (("match-report.md", report_review),))

        resume = await self._tailor.tailor(profile, posting, report_md)
        email = await self._writer.write(profile, posting, report_md)
        resume_review = await self._reviewer.review(profile, resume.markdown)
        email_review = await self._reviewer.review(profile, email.to_markdown())
        flagged = tuple(
            (name, review)
            for name, review in (("resume.md", resume_review), ("email.md", email_review))
            if not review.is_clean
        )
        if flagged:
            raise PipelineGateError("resume/email", flagged)

        return PipelineResult(
            posting=posting,
            report=report,
            resume=resume,
            email=email,
            report_review=report_review,
            resume_review=resume_review,
            email_review=email_review,
        )
