"""Unit tests for the domain value objects."""

from quiver.domain.models import (
    CandidateProfile,
    EmailDraft,
    JobLead,
    JobPosting,
    MatchRating,
    MatchReport,
    RequirementAssessment,
    ResumeDraft,
    ReviewIssue,
    ReviewResult,
    VerificationStatus,
    leads_to_markdown,
)


def test_verification_status_trustworthiness() -> None:
    assert VerificationStatus.SOURCE_VERIFIED.is_trustworthy
    assert VerificationStatus.PASTED.is_trustworthy
    assert not VerificationStatus.RECONSTRUCTED.is_trustworthy


def test_job_posting_defaults_to_reconstructed() -> None:
    assert JobPosting(title="x", company="y").verification_status is (
        VerificationStatus.RECONSTRUCTED
    )


def test_job_posting_slug_combines_company_and_title() -> None:
    assert JobPosting(title="Agent Harness PM", company="DeepSeek").slug == (
        "deepseek-agent-harness-pm"
    )


def test_job_posting_to_markdown_has_header_and_sections() -> None:
    posting = JobPosting(
        title="Agent Harness PM",
        company="DeepSeek",
        responsibilities=("Plan the roadmap",),
        verification_status=VerificationStatus.PASTED,
    )
    md = posting.to_markdown()
    assert md.startswith("# Agent Harness PM")
    assert "## Responsibilities" in md
    assert "pasted" in md


def test_job_posting_round_trips_through_dict() -> None:
    posting = JobPosting(
        title="Agent Harness PM",
        company="DeepSeek",
        requirements=("2+ years as a PM", "本科及以上"),
        verification_status=VerificationStatus.PASTED,
    )
    assert JobPosting.from_dict(posting.to_dict()) == posting


def test_candidate_profile_name_from_first_heading() -> None:
    assert CandidateProfile(raw_markdown="---\n---\n\n# Frad LEE\n\nbody").name == "Frad LEE"


def test_job_lead_carries_discovery_fields() -> None:
    assert JobLead(title="PM", company="DeepSeek").company == "DeepSeek"


def test_match_rating_labels() -> None:
    assert MatchRating.STRONG.label == "强"
    assert MatchRating.GAP.label == "缺口"


def _report(status: VerificationStatus) -> MatchReport:
    return MatchReport(
        posting=JobPosting(title="PM", company="DeepSeek", verification_status=status),
        assessments=(RequirementAssessment("2+ years PM", MatchRating.STRONG, "10+ years"),),
        gaps=("online A/B testing",),
        risks=("over-tenured for the role",),
        verdict="Strong fit; apply.",
    )


def test_match_report_to_markdown_has_all_sections() -> None:
    md = _report(VerificationStatus.PASTED).to_markdown()
    assert "## 逐条评估" in md and "## 缺口" in md and "## 风险" in md and "## 结论" in md


def test_match_report_warns_on_unverified_jd() -> None:
    assert "未核实 JD" in _report(VerificationStatus.RECONSTRUCTED).to_markdown()


def test_match_report_omits_warning_for_trustworthy_jd() -> None:
    assert "未核实 JD" not in _report(VerificationStatus.PASTED).to_markdown()


def test_review_result_is_clean_when_no_issues() -> None:
    assert ReviewResult(issues=()).is_clean
    assert not ReviewResult(issues=(ReviewIssue("x", "y"),)).is_clean


def test_review_result_to_markdown_lists_issues() -> None:
    md = ReviewResult(issues=(ReviewIssue("核心维护者", "仅 8 个 PR"),)).to_markdown()
    assert "核心维护者" in md and "1 处问题" in md
    assert "通过" in ReviewResult(issues=()).to_markdown()


def test_resume_draft_holds_markdown() -> None:
    draft = ResumeDraft(posting=JobPosting(title="PM", company="X"), markdown="# Résumé")
    assert draft.markdown == "# Résumé"


def test_email_draft_to_markdown_has_subject_and_body() -> None:
    md = EmailDraft(
        posting=JobPosting(title="PM", company="DeepSeek"), subject="Application", body="Hi."
    ).to_markdown()
    assert "Application" in md and "Hi." in md


def test_leads_to_markdown_renders_each_lead() -> None:
    md = leads_to_markdown((JobLead(title="PM", company="DeepSeek", url="https://x"),))
    assert "DeepSeek" in md and "https://x" in md
