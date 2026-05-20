"""Unit tests for the verify_github MCP tool's result-formatting seam."""

from quiver.infrastructure.github import RepoFacts
from quiver.infrastructure.tools import format_repo_facts


def test_format_reports_a_verified_original_repo() -> None:
    facts = RepoFacts(repo="FradSer/dotclaude", stars=548, is_fork=False, parent=None)
    text = format_repo_facts("FradSer/dotclaude", facts)
    assert "548" in text
    assert "FORK" not in text


def test_format_flags_a_fork_with_its_upstream() -> None:
    facts = RepoFacts(
        repo="FradSer/superpowers", stars=0, is_fork=True, parent="obra/superpowers"
    )
    text = format_repo_facts("FradSer/superpowers", facts)
    assert "FORK" in text
    assert "obra/superpowers" in text


def test_format_flags_an_unverifiable_repo() -> None:
    text = format_repo_facts("x/y", None)
    assert "unverified" in text.lower()
