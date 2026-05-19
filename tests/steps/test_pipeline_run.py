"""BDD steps for the full harness pipeline (offline — uses scripted stub agents)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from pytest_bdd import given, scenarios, then, when

from quiver.application.analyst import AnalystService
from quiver.application.intake import IntakeService
from quiver.application.pipeline import Pipeline, PipelineGateError, PipelineResult
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
_FLAG_REVIEW = json.dumps(
    {"issues": [{"claim": "核心维护者", "problem": "profile 仅显示 8 个 PR"}]}
)


def _build(runner: ScriptedAgentRunner) -> Pipeline:
    return Pipeline(
        intake=IntakeService(runner),
        analyst=AnalystService(runner),
        tailor=TailorService(runner),
        writer=WriterService(runner),
        reviewer=ReviewerService(runner),
    )


@given("a pipeline backed by stub agents", target_fixture="runner")
def _clean_runner() -> ScriptedAgentRunner:
    # Seven calls: intake, analyst, match-report review, tailor, writer,
    # resume review, email review.
    return ScriptedAgentRunner(
        [_INTAKE, _ANALYSIS, _CLEAN_REVIEW, _RESUME, _EMAIL, _CLEAN_REVIEW, _CLEAN_REVIEW]
    )


@given("a pipeline whose reviewer flags the match report", target_fixture="runner")
def _flagging_runner() -> ScriptedAgentRunner:
    # Three calls: intake, analyst, match-report review — the gate raises here.
    return ScriptedAgentRunner([_INTAKE, _ANALYSIS, _FLAG_REVIEW])


@when("I run the pipeline on a pasted job description", target_fixture="outcome")
def _run(runner: ScriptedAgentRunner) -> dict[str, Any]:
    profile = CandidateProfile(raw_markdown="# Frad LEE\n\n10+ 年产品。")
    try:
        result = asyncio.run(_build(runner).run("Agent Harness 产品经理 — DeepSeek", profile))
        return {"result": result, "error": None}
    except PipelineGateError as exc:
        return {"result": None, "error": exc}


@then("it produces a posting, a match report, a resume, and an email")
def _produces_artifacts(outcome: dict[str, Any]) -> None:
    result: PipelineResult = outcome["result"]
    assert result is not None
    assert result.posting.company == "DeepSeek"
    assert result.report.assessments
    assert result.resume.markdown
    assert result.email.subject


@then("the match report, the resume, and the email have all passed the review gate")
def _all_reviewed(outcome: dict[str, Any]) -> None:
    result: PipelineResult = outcome["result"]
    assert result.report_review.is_clean
    assert result.resume_review.is_clean
    assert result.email_review.is_clean


@then("the pipeline is blocked at the match-report gate")
def _blocked(outcome: dict[str, Any]) -> None:
    error = outcome["error"]
    assert isinstance(error, PipelineGateError)
    assert error.stage == "match-report"


@then("no resume or email is produced")
def _no_downstream(outcome: dict[str, Any], runner: ScriptedAgentRunner) -> None:
    assert outcome["result"] is None
    assert runner.calls == 3
