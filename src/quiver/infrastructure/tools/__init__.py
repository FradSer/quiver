"""Custom SDK MCP tools — the harness's verifiable-fact instruments.

`verify_github` lets the reviewer check a repository against the live GitHub
record — its star count and whether it is a fork — instead of trusting an
artifact's own claims. These are the harness rules behind the "2,152 stars"
lesson and the rule that a forked framework must not be claimed as the
candidate's own work.
"""

from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from quiver.infrastructure.github import RepoFacts, fetch_repo_facts


def format_repo_facts(repo: str, facts: RepoFacts | None) -> str:
    """Render a repo lookup as the text the reviewer agent reads back."""
    if facts is None:
        return (
            f"{repo}: could not be fetched — treat any star count or ownership "
            f"claim about it as unverified."
        )
    line = f"{repo}: {facts.stars} stars, verified live via the gh CLI."
    if facts.is_fork:
        upstream = facts.parent or "another owner's repository"
        line += (
            f" This repository is a FORK of {upstream}: it is not original work — "
            f"flag any artifact that presents it as the candidate's own project."
        )
    return line


@tool(
    "verify_github",
    "Look up a GitHub repository named as 'owner/name' on the live GitHub record. "
    "Returns its star count and whether it is a fork of someone else's project. "
    "Call this to check any GitHub star figure, or any repository an artifact "
    "claims as the candidate's own work.",
    {"repo": str},
)
async def _verify_github(args: dict[str, Any]) -> dict[str, Any]:
    repo = str(args.get("repo", "")).strip()
    facts = await asyncio.to_thread(fetch_repo_facts, repo)
    return {"content": [{"type": "text", "text": format_repo_facts(repo, facts)}]}


def quiver_mcp_server() -> McpSdkServerConfig:
    """Build the in-process MCP server exposing Quiver's fact-check tools."""
    return create_sdk_mcp_server("quiver", tools=[_verify_github])
