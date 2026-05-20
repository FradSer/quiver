"""GitHub fact-check helper — verifies repository provenance via the `gh` CLI.

Numbers and ownership claims in generated artifacts must be verifiable, never
guessed. This module is the live source for a repository's star count and fork
status — the harness rules behind the "2,152 stars" lesson and the lesson that a
forked framework must not be claimed as the candidate's own work.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RepoFacts:
    """Live facts about a GitHub repository."""

    repo: str
    stars: int
    is_fork: bool
    parent: str | None  # upstream "owner/name" when forked, else None


def parse_repo_facts(repo: str, stdout: str) -> RepoFacts | None:
    """Parse a `gh api repos/<repo>` JSON response; return None when it is unusable."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("stargazers_count"), int):
        return None
    parent = data.get("parent")
    return RepoFacts(
        repo=repo,
        stars=data["stargazers_count"],
        is_fork=bool(data.get("fork")),
        parent=parent.get("full_name") if isinstance(parent, dict) else None,
    )


def fetch_repo_facts(repo: str) -> RepoFacts | None:
    """Return live facts for `owner/name`, or None if they cannot be fetched."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return parse_repo_facts(repo, result.stdout)
