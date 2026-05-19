"""GitHub fact-check helper — verifies repository stats via the `gh` CLI.

Numbers in generated artifacts must be verifiable, never guessed. This is the
live source for GitHub star counts (the harness rule behind the "2,152★" lesson).
"""

from __future__ import annotations

import subprocess


def parse_count(stdout: str) -> int | None:
    """Parse a `gh api --jq` integer response; return None when it is not an integer."""
    value = stdout.strip()
    return int(value) if value.isdigit() else None


def repo_stars(repo: str) -> int | None:
    """Return the live star count for `owner/name`, or None if it cannot be fetched."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}", "--jq", ".stargazers_count"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return parse_count(result.stdout)
