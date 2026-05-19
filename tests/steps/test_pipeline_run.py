"""BDD steps for the full harness pipeline (offline — uses scripted stub agents)."""

from __future__ import annotations

import asyncio
import json

from pytest_bdd import given, scenarios, then, when

from quiver.application.analyst import AnalystService
from quiver.application.intake import IntakeService
from quiver.application.pipeline import Pipeline, PipelineResult
from quiver.application.reviewer import ReviewerService
from quiver.application.tailor import TailorService
from quiver.application.writer import WriterService
from quiver.domain.models import CandidateProfile
from tests.fakes import ScriptedAgentRunner

scenarios("../features/pipeline.feature")

_INTAKE = json.dumps(
    {
        "available": True,
        "title": "Agent Harness 产品经理",
        "company": "DeepSeek",
        "responsibilities": ["规划路线图"],
        "requirements": ["2 年以上 PM 经验"],
        "bonuses": [],
    }
)
_ANALYSIS = json.dumps(
    {
        "assessments": [{"requirement": "2 年 PM", "rating": "strong", "evidence": "10+ 年"}],
        "gaps": ["线上 A/B 测试"],
        "risks": ["资历偏高"],
        "verdict": "强匹配，建议投递。",
    }
)
_RESUME = "# Frad LEE\n\n对标 Agent Harness PM 的简历。"
_EMAIL = json.dumps({"subject": "应聘 Agent Harness 产品经理", "body": "你好，我想申请这个岗位。"})
_CLEAN_REVIEW = json.dumps({"issues": []})


@given("a pipeline backed by stub agents", target_fixture="pipeline")
def _pipeline() -> Pipeline:
    # The pipeline calls the runner six times: intake, analyst, tailor, writer,
    # then a review of the resume and a review of the email.
    runner = ScriptedAgentRunner(
        [_INTAKE, _ANALYSIS, _RESUME, _EMAIL, _CLEAN_REVIEW, _CLEAN_REVIEW]
    )
    return Pipeline(
        intake=IntakeService(runner),
        analyst=AnalystService(runner),
        tailor=TailorService(runner),
        writer=WriterService(runner),
        reviewer=ReviewerService(runner),
    )


@when("I run the pipeline on a pasted job description", target_fixture="result")
def _run(pipeline: Pipeline) -> PipelineResult:
    profile = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ 年产品。")
    return asyncio.run(pipeline.run("Agent Harness 产品经理 — DeepSeek", profile))


@then("it produces a posting, a match report, a resume, and an email")
def _produces_artifacts(result: PipelineResult) -> None:
    assert result.posting.company == "DeepSeek"
    assert result.report.assessments
    assert result.resume.markdown
    assert result.email.subject


@then("both the resume and the email have passed the review gate")
def _both_reviewed(result: PipelineResult) -> None:
    assert result.resume_review.is_clean
    assert result.email_review.is_clean
