"""Domain value objects. Pure: depends only on the standard library."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class VerificationStatus(Enum):
    """How a job description's content was obtained."""

    SOURCE_VERIFIED = "source_verified"  # fetched from an authoritative source
    PASTED = "pasted"  # supplied verbatim by the user
    RECONSTRUCTED = "reconstructed"  # secondary sources — treat as unverified

    @property
    def is_trustworthy(self) -> bool:
        """Whether analysis built on this JD may omit an "unverified" warning."""
        return self in (VerificationStatus.SOURCE_VERIFIED, VerificationStatus.PASTED)


class MatchRating(Enum):
    """How a candidate measures against one job requirement."""

    STRONG = "strong"
    PARTIAL = "partial"
    GAP = "gap"

    @property
    def label(self) -> str:
        """A short Chinese label for reports."""
        return {
            MatchRating.STRONG: "强",
            MatchRating.PARTIAL: "部分",
            MatchRating.GAP: "缺口",
        }[self]


def _slugify(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace and underscores to hyphens."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", cleaned) or "untitled"


def _section(heading: str, items: tuple[str, ...]) -> str:
    """Render one Markdown section, or "" when there are no items."""
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items)
    return f"\n## {heading}\n\n{body}\n"


def _cell(text: str) -> str:
    """Make text safe for a single Markdown table cell."""
    return text.replace("|", "/").replace("\n", " ").strip()


def _bullets(items: tuple[str, ...], empty: str) -> list[str]:
    """Render items as Markdown bullets, or a single fallback bullet when empty."""
    return [f"- {item}" for item in items] if items else [f"- {empty}"]


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """The candidate profile — the read-only source of truth, loaded from markdown."""

    raw_markdown: str
    source: Path | None = None

    @property
    def name(self) -> str:
        """The candidate's name, taken from the first level-1 Markdown heading."""
        for line in self.raw_markdown.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""


@dataclass(frozen=True, slots=True)
class JobLead:
    """A discovered job-posting candidate, before intake structures it."""

    title: str
    company: str
    url: str = ""
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class JobPosting:
    """A normalized job description and its provenance."""

    title: str
    company: str
    location: str = ""
    responsibilities: tuple[str, ...] = ()
    requirements: tuple[str, ...] = ()
    bonuses: tuple[str, ...] = ()
    contact: str = ""
    source_url: str = ""
    verification_status: VerificationStatus = VerificationStatus.RECONSTRUCTED

    @property
    def slug(self) -> str:
        """Stable identifier used as this posting's artifact folder name."""
        return f"{_slugify(self.company)}-{_slugify(self.title)}"

    def to_markdown(self) -> str:
        """Render this posting as a Markdown document."""
        header = (
            f"# {self.title}\n\n"
            f"- **Company**: {self.company}\n"
            f"- **Location**: {self.location or '—'}\n"
            f"- **Contact**: {self.contact or '—'}\n"
            f"- **Source**: {self.source_url or '—'}\n"
            f"- **Verification**: {self.verification_status.value}\n"
        )
        return header + "".join(
            _section(heading, items)
            for heading, items in (
                ("Responsibilities", self.responsibilities),
                ("Requirements", self.requirements),
                ("Bonuses", self.bonuses),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "responsibilities": list(self.responsibilities),
            "requirements": list(self.requirements),
            "bonuses": list(self.bonuses),
            "contact": self.contact,
            "source_url": self.source_url,
            "verification_status": self.verification_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobPosting:
        """Rebuild a posting from a dict produced by `to_dict`."""

        def strs(key: str) -> tuple[str, ...]:
            return tuple(str(x) for x in data.get(key) or [])

        return cls(
            title=str(data["title"]),
            company=str(data["company"]),
            location=str(data.get("location", "")),
            responsibilities=strs("responsibilities"),
            requirements=strs("requirements"),
            bonuses=strs("bonuses"),
            contact=str(data.get("contact", "")),
            source_url=str(data.get("source_url", "")),
            verification_status=VerificationStatus(
                data.get("verification_status", "reconstructed")
            ),
        )


@dataclass(frozen=True, slots=True)
class RequirementAssessment:
    """How the candidate measures against one job requirement."""

    requirement: str
    rating: MatchRating
    evidence: str


@dataclass(frozen=True, slots=True)
class MatchReport:
    """An honest candidate-to-job match analysis."""

    posting: JobPosting
    assessments: tuple[RequirementAssessment, ...]
    gaps: tuple[str, ...]
    risks: tuple[str, ...]
    verdict: str

    def to_markdown(self) -> str:
        """Render this match report as a Markdown document."""
        lines = [f"# 匹配报告：{self.posting.title} @ {self.posting.company}", ""]
        if not self.posting.verification_status.is_trustworthy:
            lines += [
                "> **未核实 JD** —— 本报告基于来源未核实"
                f"（{self.posting.verification_status.value}）的职位描述，"
                "结论需谨慎核对原始 JD。",
                "",
            ]
        lines += ["## 逐条评估", "", "| 要求 | 评级 | 证据 |", "| --- | --- | --- |"]
        lines += [
            f"| {_cell(a.requirement)} | {a.rating.label} | {_cell(a.evidence)} |"
            for a in self.assessments
        ]
        lines += ["", "## 缺口", *_bullets(self.gaps, "（无明显缺口）")]
        lines += ["", "## 风险", *_bullets(self.risks, "（无明显风险）")]
        lines += ["", "## 结论", "", self.verdict, ""]
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, md: str, posting: JobPosting) -> MatchReport:
        """Best-effort parse of a match report back from Markdown."""
        assessments: list[RequirementAssessment] = []
        gaps: list[str] = []
        risks: list[str] = []
        verdict = ""

        sections = re.split(r"\n## ", md)
        for section in sections:
            if section.startswith("逐条评估"):
                # Simple table parser
                for line in section.splitlines():
                    if "|" in line and "评级" not in line and "---" not in line:
                        parts = [p.strip() for p in line.split("|") if p.strip()]
                        if len(parts) >= 3:
                            rating_map = {"强": MatchRating.STRONG, "部分": MatchRating.PARTIAL, "缺口": MatchRating.GAP}
                            rating = rating_map.get(parts[1], MatchRating.PARTIAL)
                            assessments.append(RequirementAssessment(parts[0], rating, parts[2]))
            elif section.startswith("缺口"):
                gaps = [l[2:].strip() for l in section.splitlines() if l.startswith("- ") and "无明显缺口" not in l]
            elif section.startswith("风险"):
                risks = [l[2:].strip() for l in section.splitlines() if l.startswith("- ") and "无明显风险" not in l]
            elif section.startswith("结论"):
                verdict = "\n".join(l.strip() for l in section.splitlines()[1:] if l.strip())

        return cls(posting, tuple(assessments), tuple(gaps), tuple(risks), verdict)


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    """One honesty problem the reviewer found in a generated artifact."""

    claim: str
    problem: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """The fact-check reviewer's verdict on an artifact."""

    issues: tuple[ReviewIssue, ...]

    @property
    def is_clean(self) -> bool:
        """Whether the artifact passed with no honesty issues."""
        return not self.issues

    def to_markdown(self) -> str:
        """Render this review as a Markdown document."""
        if self.is_clean:
            return "# 事实核查\n\n通过：未发现无证据声明或未核实数字。\n"
        lines = ["# 事实核查", "", f"发现 {len(self.issues)} 处问题：", ""]
        lines += [f"- **{_cell(i.claim)}** —— {i.problem}" for i in self.issues]
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, slots=True)
class ResumeDraft:
    """A job-tailored résumé."""

    posting: JobPosting
    markdown: str


@dataclass(frozen=True, slots=True)
class EmailDraft:
    """An application email draft."""

    posting: JobPosting
    subject: str
    body: str

    def to_markdown(self) -> str:
        """Render this email draft as a Markdown document."""
        return (
            f"# 申请邮件：{self.posting.company} / {self.posting.title}\n\n"
            f"**主题**：{self.subject}\n\n---\n\n{self.body}\n"
        )

    @classmethod
    def from_markdown(cls, md: str, posting: JobPosting) -> EmailDraft:
        """Best-effort parse of an email draft back from Markdown."""
        subject = ""
        body = ""
        match = re.search(r"\*\*主题\*\*：(.*)", md)
        if match:
            subject = match.group(1).strip()
        parts = md.split("---\n\n")
        if len(parts) >= 2:
            body = parts[1].strip()
        return cls(posting, subject, body)


def leads_to_markdown(leads: tuple[JobLead, ...]) -> str:
    """Render discovered job leads as a Markdown document."""
    lines = ["# 岗位线索", ""]
    if not leads:
        lines.append("（未发现线索）")
    for lead in leads:
        lines += [
            f"## {lead.company} —— {lead.title}",
            f"- 链接：{lead.url or '—'}",
            f"- 匹配理由：{lead.rationale or '—'}",
            "",
        ]
    return "\n".join(lines)
