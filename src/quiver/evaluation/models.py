"""Value objects for the evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from quiver.domain.models import JobPosting


class CaseKind(Enum):
    """Which capability an eval case exercises."""

    REVIEWER = "reviewer"
    INTAKE = "intake"
    ANALYST = "analyst"
    E2E = "e2e"


@dataclass(frozen=True, slots=True)
class ReviewerCase:
    """A reviewer eval case: an artifact the reviewer should (or should not) flag."""

    case_id: str
    profile_md: str
    artifact_md: str
    should_flag: bool
    must_catch: str = ""  # substring the flagged issue text should reference


@dataclass(frozen=True, slots=True)
class IntakeCase:
    """An intake eval case: a JD with known requirements that should be extracted."""

    case_id: str
    jd_text: str
    expected_requirements: tuple[str, ...]
    min_coverage: float = 0.8


@dataclass(frozen=True, slots=True)
class AnalystCase:
    """An analyst eval case: a profile + posting with a known gap and a known strength."""

    case_id: str
    profile_md: str
    posting: JobPosting
    expected_gap: str  # requirement substring that must rate gap/partial, not strong
    expected_strong: str  # requirement substring that should rate strong


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    """The result of scoring one eval case."""

    case_id: str
    kind: CaseKind
    passed: bool
    detail: str
    gating: bool = True  # informational cases (e2e) never fail the verdict


def _cell(text: str) -> str:
    """Make text safe for a single Markdown table cell."""
    return text.replace("|", "/").replace("\n", " ").strip()


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Aggregated results of one evaluation run."""

    outcomes: tuple[CaseOutcome, ...]
    reviewer_recall: tuple[int, int]  # (planted overclaims caught, total planted)
    reviewer_precision: tuple[int, int]  # (honest artifacts left clean, total honest)

    @property
    def verdict_failed(self) -> bool:
        """Whether any gating case failed — a leaky honesty gate fails here."""
        return any(not o.passed for o in self.outcomes if o.gating)

    def summary(self) -> str:
        """A short multi-line summary for the terminal."""
        gating = [o for o in self.outcomes if o.gating]
        passed = sum(o.passed for o in gating)
        rc, rt = self.reviewer_recall
        pc, pt = self.reviewer_precision
        verdict = "FAIL" if self.verdict_failed else "PASS"
        return (
            f"eval: {verdict} — {passed}/{len(gating)} gating cases passed\n"
            f"  reviewer recall {rc}/{rt} (planted overclaims caught), "
            f"precision {pc}/{pt} (honest artifacts left clean)"
        )

    def to_markdown(self) -> str:
        """Render the full evaluation report as Markdown."""
        rc, rt = self.reviewer_recall
        pc, pt = self.reviewer_precision
        verdict = "FAIL" if self.verdict_failed else "PASS"
        lines = [
            "# Quiver 评测报告",
            "",
            f"**结论：{verdict}**",
            "",
            f"- reviewer 查全率（planted overclaim 被抓到）：{rc}/{rt}",
            f"- reviewer 查准率（honest artifact 留 clean）：{pc}/{pt}",
            "",
            "## 逐例结果",
            "",
            "| 用例 | 类型 | 结果 | 说明 |",
            "| --- | --- | --- | --- |",
        ]
        for o in self.outcomes:
            result = "信息" if not o.gating else ("通过" if o.passed else "未通过")
            lines.append(f"| {_cell(o.case_id)} | {o.kind.value} | {result} | {_cell(o.detail)} |")
        return "\n".join(lines) + "\n"
