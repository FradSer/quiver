"""Test doubles for Quiver."""

from __future__ import annotations


class FakeAgentRunner:
    """An AgentRunner that returns a preset response and records the last call."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt: str | None = None
        self.last_allowed_tools: list[str] | None = None

    async def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Record the call and return the preset response."""
        self.last_prompt = prompt
        self.last_allowed_tools = allowed_tools
        return self.response


class ScriptedAgentRunner:
    """An AgentRunner that returns queued responses, one per call, in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Return the next queued response."""
        response = self._responses[self.calls]
        self.calls += 1
        return response
