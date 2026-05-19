"""BDD steps for match analysis (offline — uses a stub assessor)."""

from __future__ import annotations

import asyncio
import json

from pytest_bdd import given, scenarios, then, when

from quiver.application.analyst import AnalystService
from quiver.domain.models import (
    CandidateProfile,
    JobPosting,
    MatchRating,
    MatchReport,
    RequirementAssessment,
    VerificationStatus,
)
from tests.fakes import FakeAgentRunner

scenarios("../features/analysis.feature")

_ANALYSIS_JSON = json.dumps(
    {
        "assessments": [
            {"requirement": "2 年以上 PM 经验", "rating": "strong", "evidence": "10+ 年"},
            {"requirement": "系统化数据方法", "rating": "gap", "evidence": "无 A/B 实战"},
        ],
        "gaps": ["线上 A/B 测试经验"],
        "risks": ["12 年经验投 2 年门槛的岗位"],
        "verdict": "强匹配，但数据方法是真实缺口；建议投递。",
    }
)


@given("an analyst backed by a stub assessor", target_fixture="analyst")
def _analyst() -> AnalystService:
    return AnalystService(FakeAgentRunner(_ANALYSIS_JSON))


@when("I analyze the candidate against the job", target_fixture="report_md")
def _analyze(analyst: AnalystService) -> str:
    profile = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ years in product.")
    posting = JobPosting(
        title="Agent Harness 产品经理",
        company="DeepSeek",
        verification_status=VerificationStatus.PASTED,
    )
    return asyncio.run(analyst.analyze(profile, posting)).to_markdown()


@then("the report has per-requirement assessments, a gaps section, and a risks section")
def _report_has_sections(report_md: str) -> None:
    assert "## 逐条评估" in report_md
    assert "## 缺口" in report_md
    assert "## 风险" in report_md


@given("a job posting whose source was not verified", target_fixture="posting")
def _unverified_posting() -> JobPosting:
    return JobPosting(title="X", company="Y", verification_status=VerificationStatus.RECONSTRUCTED)


@when("I render its match report", target_fixture="report_md")
def _render(posting: JobPosting) -> str:
    report = MatchReport(
        posting=posting,
        assessments=(RequirementAssessment("r", MatchRating.GAP, "e"),),
        gaps=(),
        risks=(),
        verdict="v",
    )
    return report.to_markdown()


@then("the report header carries an unverified-JD warning")
def _report_has_warning(report_md: str) -> None:
    assert "未核实 JD" in report_md
