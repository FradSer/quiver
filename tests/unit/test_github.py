"""Unit tests for the GitHub fact-check helper's parsing seam."""

from quiver.infrastructure.github import parse_count


def test_parse_count_reads_an_integer() -> None:
    assert parse_count("547\n") == 547


def test_parse_count_rejects_non_integers() -> None:
    assert parse_count("not a number") is None
    assert parse_count("") is None
