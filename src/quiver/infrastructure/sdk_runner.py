"""Claude Agent SDK adapter — the infrastructure implementation of AgentRunner.

Authentication is whatever the logged-in Claude Code CLI provides: the SDK runs
the CLI headlessly and reuses its session. No API key required.
"""

from __future__ import annotations

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query


class ClaudeAgentRunner:
    """Runs prompts through the Claude Agent SDK. Implements the AgentRunner port."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model

    async def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Execute `prompt` and return the concatenated assistant text."""
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=self._model,
            allowed_tools=allowed_tools or [],
        )
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        return "".join(chunks)
