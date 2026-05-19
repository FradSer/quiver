"""Ports: interfaces the application layer depends on.

Per Clean Architecture these are declared in the consuming layer; their
implementations live in `infrastructure`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from quiver.domain.models import CandidateProfile, JobPosting


class AgentRunner(Protocol):
    """Runs a prompt through an agent and returns its final text output."""

    async def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Execute `prompt` and return the concatenated assistant text."""
        ...


class ArtifactStore(Protocol):
    """Loads the candidate profile and persists generated artifacts."""

    def load_profile(self) -> CandidateProfile:
        """Load the candidate profile (the read-only source of truth)."""
        ...

    def load_job_posting(self, slug: str) -> JobPosting:
        """Load a previously intaken job posting by slug."""
        ...

    def save_job_posting(self, posting: JobPosting) -> Path:
        """Persist a structured job posting; return the Markdown path written."""
        ...

    def read_artifact(self, slug: str, filename: str) -> str:
        """Read a previously written artifact under `jobs/<slug>/`."""
        ...

    def write_artifact(self, slug: str, filename: str, content: str) -> Path:
        """Write an artifact under `jobs/<slug>/`; return the path written."""
        ...

    def write_leads(self, content: str) -> Path:
        """Write the job-leads document; return the path written."""
        ...
