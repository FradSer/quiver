"""Unit tests for the verify_github MCP tool's result-formatting seam."""

from quiver.infrastructure.tools import format_stars


def test_format_stars_reports_a_verified_count() -> None:
    text = format_stars("anthropics/claude-code", 2152)
    assert "2152" in text
    assert "anthropics/claude-code" in text


def test_format_stars_flags_an_unverifiable_repo() -> None:
    text = format_stars("anthropics/claude-code", None)
    assert "anthropics/claude-code" in text
    assert "unverified" in text.lower()
