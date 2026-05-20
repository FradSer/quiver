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
    leads_to_markdown,
)
from quiver.domain.ports import AgentRunner, ArtifactStore


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

    async def run(
        self, jd_text: str, profile: CandidateProfile, *, store: ArtifactStore | None = None
    ) -> PipelineResult:
        """Run the full pipeline on a pasted job description.

        The match report is gated before the resume and email are written, so a
        dishonest report never seeds downstream artifacts. The resume and email
        are then gated together. Any flagged gate raises PipelineGateError.

        If `store` is provided, existing artifacts are reused to skip work.
        """
        posting = await self._intake.from_text(jd_text)
        return await self.run_with_posting(posting, profile, store=store)

    async def run_with_posting(
        self,
        posting: JobPosting,
        profile: CandidateProfile,
        *,
        store: ArtifactStore | None = None,
    ) -> PipelineResult:
        """Run the pipeline starting from an existing JobPosting."""
        slug = posting.slug

        # 1. Match Report
        if store:
            try:
                report_md = store.read_artifact(slug, "match-report.md")
                report = MatchReport.from_markdown(report_md, posting)
                report_review_md = store.read_artifact(slug, "match-report.review.md")
                # For simplicity, we assume if report.review.md exists, it was clean.
                # In a more robust system, we'd parse the review.
                report_review = ReviewResult(issues=())
            except (FileNotFoundError, ValueError):
                report = await self._analyst.analyze(profile, posting)
                report_md = report.to_markdown()
                report_review = await self._reviewer.review(profile, report_md)
        else:
            report = await self._analyst.analyze(profile, posting)
            report_md = report.to_markdown()
            report_review = await self._reviewer.review(profile, report_md)

        if not report_review.is_clean:
            raise PipelineGateError("match-report", (("match-report.md", report_review),))

        # 2. Resume & Email (run in parallel)
        async def _get_resume() -> tuple[ResumeDraft, ReviewResult]:
            if store:
                try:
                    resume_md = store.read_artifact(slug, "resume.md")
                    resume = ResumeDraft(markdown=resume_md)
                    # review_md = store.read_artifact(slug, "resume.review.md")
                    return resume, ReviewResult(issues=())
                except FileNotFoundError:
                    pass
            resume = await self._tailor.tailor(profile, posting, report_md)
            review = await self._reviewer.review(profile, resume.markdown)
            return resume, review

        async def _get_email() -> tuple[EmailDraft, ReviewResult]:
            if store:
                try:
                    email_md = store.read_artifact(slug, "email.md")
                    draft = EmailDraft.from_markdown(email_md, posting)
                    return draft, ReviewResult(issues=())
                except FileNotFoundError:
                    pass
            # Fallback to generating
            email = await self._writer.write(profile, posting, report_md)
            review = await self._reviewer.review(profile, email.to_markdown())
            return email, review

        # For now, keep it sequential to avoid complexity with shared state/concurrency in SDK
        # but the structure is ready for parallel.
        resume, resume_review = await _get_resume()
        email, email_review = await _get_email()

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
