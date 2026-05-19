"""Custom SDK MCP tools — the harness's verifiable-fact instruments.

`verify_github` exists so the reviewer can check a GitHub star count against the
live repository instead of trusting whatever number an artifact states (the
harness rule behind the "2,152 stars" lesson).
"""

from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from quiver.infrastructure.github import repo_stars


def format_stars(repo: str, stars: int | None) -> str:
    """Render a star-count lookup as the text the reviewer agent reads back."""
    if stars is None:
        return f"{repo}: star count could not be fetched — treat any figure for it as unverified."
    return f"{repo}: {stars} stars, verified live via the gh CLI."


@tool(
    "verify_github",
    "Fetch the live GitHub star count for a repository named as 'owner/name'. "
    "Call this to check any GitHub star figure an artifact states.",
    {"repo": str},
)
async def _verify_github(args: dict[str, Any]) -> dict[str, Any]:
    repo = str(args.get("repo", "")).strip()
    stars = await asyncio.to_thread(repo_stars, repo)
    return {"content": [{"type": "text", "text": format_stars(repo, stars)}]}


def quiver_mcp_server() -> McpSdkServerConfig:
    """Build the in-process MCP server exposing Quiver's fact-check tools."""
    return create_sdk_mcp_server("quiver", tools=[_verify_github])
