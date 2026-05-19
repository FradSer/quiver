"""Unit tests for the filesystem artifact store."""

from pathlib import Path

from quiver.domain.models import JobPosting, VerificationStatus
from quiver.infrastructure.store import FileSystemArtifactStore


def test_load_profile_reads_markdown(tmp_path: Path) -> None:
    (tmp_path / "frad-lee-profile.md").write_text("# Frad LEE\n\nhello", encoding="utf-8")
    profile = FileSystemArtifactStore(tmp_path).load_profile()
    assert profile.name == "Frad LEE"
    assert "hello" in profile.raw_markdown


def test_job_posting_round_trips_through_the_store(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    posting = JobPosting(
        title="Agent Harness 产品经理",
        company="DeepSeek",
        requirements=("2 年以上经验",),
        verification_status=VerificationStatus.PASTED,
    )
    md_path = store.save_job_posting(posting)
    assert md_path == tmp_path / "jobs" / posting.slug / "jd.md"
    assert store.load_job_posting(posting.slug) == posting


def test_write_and_read_artifact(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    path = store.write_artifact("deepseek-pm", "match-report.md", "# Report\n")
    assert path == tmp_path / "jobs" / "deepseek-pm" / "match-report.md"
    assert store.read_artifact("deepseek-pm", "match-report.md") == "# Report\n"


def test_write_leads_goes_to_jobs_leads(tmp_path: Path) -> None:
    path = FileSystemArtifactStore(tmp_path).write_leads("# 岗位线索\n")
    assert path == tmp_path / "jobs" / "leads.md"
    assert path.read_text(encoding="utf-8") == "# 岗位线索\n"
