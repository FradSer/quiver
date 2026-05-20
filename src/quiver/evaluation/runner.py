"""The evaluation runner — exercises the real agents against the golden cases."""

from __future__ import annotations

from quiver.application.analyst import AnalysisError, AnalystService
from quiver.application.intake import IntakeService, JdUnavailableError
from quiver.application.reviewer import ReviewError, ReviewerService
from quiver.application.tailor import TailorError, TailorService
from quiver.domain.models import CandidateProfile
from quiver.evaluation import cases
from quiver.evaluation.models import (
    AnalystCase,
    CaseKind,
    CaseOutcome,
    EvalReport,
    IntakeCase,
    ReviewerCase,
)
from quiver.evaluation.scoring import score_analyst, score_intake, score_reviewer


def _collapse(outcomes: list[CaseOutcome], repeat: int) -> CaseOutcome:
    """Fold `repeat` runs of one case into a single outcome.

    Stochastic agents can be slightly inconsistent. If repeat > 1, we require
    at least 75% of runs to pass for the case to be considered passed.
    """
    first = outcomes[0]
    passed_runs = sum(o.passed for o in outcomes)
    threshold = 0.75
    passed = (passed_runs / len(outcomes)) >= threshold
    suffix = f" [{passed_runs}/{repeat} runs]" if repeat > 1 else ""
    return CaseOutcome(first.case_id, first.kind, passed, first.detail + suffix, first.gating)


class EvalRunner:
    """Runs the golden eval cases against the real agent services."""

    def __init__(
        self,
        *,
        intake: IntakeService,
        analyst: AnalystService,
        reviewer: ReviewerService,
        tailor: TailorService,
    ) -> None:
        self._intake = intake
        self._analyst = analyst
        self._reviewer = reviewer
        self._tailor = tailor

    async def run(self, repeat: int = 1) -> EvalReport:
        """Run every golden case `repeat` times and aggregate an EvalReport."""
        outcomes: list[CaseOutcome] = []
        for r_case in cases.REVIEWER_CASES:
            outcomes.append(await self._run_reviewer(r_case, repeat))
        for i_case in cases.INTAKE_CASES:
            outcomes.append(await self._run_intake(i_case, repeat))
        for a_case in cases.ANALYST_CASES:
            outcomes.append(await self._run_analyst(a_case, repeat))
        outcomes.append(await self._run_e2e(repeat))

        by_id = {o.case_id: o for o in outcomes if o.kind is CaseKind.REVIEWER}
        planted = [c for c in cases.REVIEWER_CASES if c.should_flag]
        honest = [c for c in cases.REVIEWER_CASES if not c.should_flag]
        recall = (sum(by_id[c.case_id].passed for c in planted), len(planted))
        precision = (sum(by_id[c.case_id].passed for c in honest), len(honest))
        return EvalReport(
            outcomes=tuple(outcomes),
            reviewer_recall=recall,
            reviewer_precision=precision,
        )

    async def _run_reviewer(self, case: ReviewerCase, repeat: int) -> CaseOutcome:
        profile = CandidateProfile(raw_markdown=case.profile_md)
        runs: list[CaseOutcome] = []
        for _ in range(repeat):
            try:
                result = await self._reviewer.review(profile, case.artifact_md)
            except ReviewError as exc:
                runs.append(CaseOutcome(case.case_id, CaseKind.REVIEWER, False, f"error: {exc}"))
                continue
            runs.append(score_reviewer(case, result))
        return _collapse(runs, repeat)

    async def _run_intake(self, case: IntakeCase, repeat: int) -> CaseOutcome:
        runs: list[CaseOutcome] = []
        for _ in range(repeat):
            try:
                posting = await self._intake.from_text(case.jd_text)
            except JdUnavailableError as exc:
                runs.append(CaseOutcome(case.case_id, CaseKind.INTAKE, False, f"error: {exc}"))
                continue
            runs.append(score_intake(case, posting))
        return _collapse(runs, repeat)

    async def _run_analyst(self, case: AnalystCase, repeat: int) -> CaseOutcome:
        profile = CandidateProfile(raw_markdown=case.profile_md)
        runs: list[CaseOutcome] = []
        for _ in range(repeat):
            try:
                report = await self._analyst.analyze(profile, case.posting)
            except AnalysisError as exc:
                runs.append(CaseOutcome(case.case_id, CaseKind.ANALYST, False, f"error: {exc}"))
                continue
            runs.append(score_analyst(case, report))
        return _collapse(runs, repeat)

    async def _run_e2e(self, repeat: int) -> CaseOutcome:
        profile = CandidateProfile(raw_markdown=cases.E2E_PROFILE)
        runs: list[CaseOutcome] = []
        for _ in range(repeat):
            try:
                resume = await self._tailor.tailor(profile, cases.E2E_POSTING, cases.E2E_REPORT_MD)
                review = await self._reviewer.review(profile, resume.markdown)
            except (TailorError, ReviewError) as exc:
                runs.append(
                    CaseOutcome("e2e-tailor-honesty", CaseKind.E2E, False, f"error: {exc}", False)
                )
                continue
            detail = f"tailored résumé drew {len(review.issues)} reviewer issue(s)"
            runs.append(
                CaseOutcome("e2e-tailor-honesty", CaseKind.E2E, review.is_clean, detail, False)
            )
        return _collapse(runs, repeat)
