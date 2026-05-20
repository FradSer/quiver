"""Unit tests for the GitHub fact-check helper's parsing seam."""

from quiver.infrastructure.github import parse_repo_facts


def test_parse_repo_facts_reads_an_original_repo() -> None:
    facts = parse_repo_facts("FradSer/dotclaude", '{"stargazers_count": 548, "fork": false}')
    assert facts is not None
    assert facts.stars == 548
    assert facts.is_fork is False
    assert facts.parent is None


def test_parse_repo_facts_reads_a_fork_with_its_parent() -> None:
    facts = parse_repo_facts(
        "FradSer/superpowers",
        '{"stargazers_count": 0, "fork": true, "parent": {"full_name": "obra/superpowers"}}',
    )
    assert facts is not None
    assert facts.is_fork is True
    assert facts.parent == "obra/superpowers"


def test_parse_repo_facts_rejects_unusable_responses() -> None:
    assert parse_repo_facts("x/y", "not json") is None
    assert parse_repo_facts("x/y", '{"message": "Not Found"}') is None
