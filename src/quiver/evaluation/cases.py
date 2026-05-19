"""Golden evaluation cases — minimal, controlled synthetic fixtures.

Each case is purpose-built so its expected outcome is unambiguous; the metrics
are only as honest as the cases are controlled.
"""

from __future__ import annotations

from quiver.domain.models import JobPosting, VerificationStatus
from quiver.evaluation.models import AnalystCase, IntakeCase, ReviewerCase

# --- Reviewer cases ---------------------------------------------------------

_PROFILE_OPENCLAW = (
    "# Frad LEE\n\n"
    "Contributed 8 pull requests to OpenClaw, all in a personal fork — none "
    "merged upstream. He is an OpenClaw ecosystem contributor, not a core "
    "maintainer of openclaw/openclaw."
)

REVIEWER_CASES: tuple[ReviewerCase, ...] = (
    ReviewerCase(
        case_id="reviewer-overclaim-maintainer",
        profile_md=_PROFILE_OPENCLAW,
        artifact_md="# 简历\n\n- OpenClaw 核心维护者，主导项目核心架构。",
        should_flag=True,
        must_catch="维护",
    ),
    ReviewerCase(
        case_id="reviewer-overclaim-number",
        profile_md="# Frad LEE\n\nGitHub: 2,152 stars across his original repositories.",
        artifact_md="# 简历\n\n- GitHub 上累计 5,000+ stars。",
        should_flag=True,
        must_catch="5,000",
    ),
    ReviewerCase(
        case_id="reviewer-overclaim-unsupported",
        profile_md="# Frad LEE\n\nUses Claude Code and Cursor daily.",
        artifact_md="# 简历\n\n- 深度使用 Manus 两年，是其早期重度用户。",
        should_flag=True,
        must_catch="Manus",
    ),
    ReviewerCase(
        case_id="reviewer-honest-dotclaude",
        profile_md="# Frad LEE\n\nBuilt dotclaude, a pack of 14 Claude Code plugins, 547 stars.",
        artifact_md="# 简历\n\n- dotclaude：为 Claude Code 写的 14 个插件，547★。",
        should_flag=False,
    ),
    ReviewerCase(
        case_id="reviewer-honest-design",
        profile_md="# Frad LEE\n\n8 项公开交互设计专利；约 6 年专业交互/产品设计经验。",
        artifact_md="# 简历\n\n- 8 项公开交互设计专利；约 6 年专业交互/产品设计经验。",
        should_flag=False,
    ),
)

# --- Intake case ------------------------------------------------------------

INTAKE_CASES: tuple[IntakeCase, ...] = (
    IntakeCase(
        case_id="intake-coverage",
        jd_text=(
            "产品经理\n\n"
            "公司：示例科技有限公司\n\n"
            "任职要求：\n"
            "1. 3 年以上产品经理经验。\n"
            "2. 熟悉 SQL 与数据分析。\n"
            "3. 具备 B 端产品设计经验。\n"
            "4. 优秀的跨团队沟通能力。\n"
            "5. 本科及以上学历。\n"
        ),
        expected_requirements=("产品经理", "SQL", "B 端", "沟通", "本科"),
        min_coverage=0.8,
    ),
)

# --- Analyst case -----------------------------------------------------------

ANALYST_CASES: tuple[AnalystCase, ...] = (
    AnalystCase(
        case_id="analyst-calibration",
        profile_md=(
            "# Frad LEE\n\n"
            "Ships production code daily in Go, Python, and TypeScript. "
            "Has no investment-banking or finance-industry experience whatsoever."
        ),
        posting=JobPosting(
            title="Engineer",
            company="ExampleCo",
            requirements=(
                "Writes production code in Python",
                "10 years of investment-banking experience",
            ),
            verification_status=VerificationStatus.PASTED,
        ),
        expected_gap="investment-banking",
        expected_strong="production code",
    ),
)

# --- End-to-end (tailor honesty, informational) -----------------------------

E2E_PROFILE = (
    "# Frad LEE\n\n"
    "Product manager. Built dotclaude (14 Claude Code plugins, 547 stars). "
    "Contributed 8 PRs to OpenClaw in a fork. ~6 years of design experience, "
    "8 interaction-design patents."
)
E2E_POSTING = JobPosting(
    title="Agent Product Manager",
    company="ExampleCo",
    requirements=("Builds AI agent tooling", "Has product and design skill"),
    verification_status=VerificationStatus.PASTED,
)
E2E_REPORT_MD = "# 匹配报告\n\n候选人在 Agent 工具与设计上较强；无明显硬伤。"
