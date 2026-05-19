"""Filesystem artifact store — Quiver's knowledge base and output area.

Reads the knowledge directory and profile filename from environment variables
(`QUIVER_KNOWLEDGE_DIR`, `QUIVER_PROFILE_FILENAME`) with sensible defaults.
Generated artifacts live under `jobs/<slug>/` inside the knowledge directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from quiver.domain.models import CandidateProfile, JobPosting

_DEFAULT_KNOWLEDGE_DIR = Path.home() / "Documents" / "Work Research"
_DEFAULT_PROFILE_FILENAME = "profile.md"

KNOWLEDGE_DIR: Path = Path(os.environ.get("QUIVER_KNOWLEDGE_DIR", _DEFAULT_KNOWLEDGE_DIR))
PROFILE_FILENAME: str = os.environ.get("QUIVER_PROFILE_FILENAME", _DEFAULT_PROFILE_FILENAME)


class FileSystemArtifactStore:
    """Reads the profile and writes artifacts under the knowledge directory.

    Implements the ArtifactStore port.
    """

    def __init__(
        self,
        knowledge_dir: Path = KNOWLEDGE_DIR,
        profile_filename: str = PROFILE_FILENAME,
    ) -> None:
        self._dir = knowledge_dir
        self._profile_filename = profile_filename

    def load_profile(self) -> CandidateProfile:
        """Load the candidate profile from the configured profile file."""
        path = self._dir / self._profile_filename
        return CandidateProfile(raw_markdown=path.read_text(encoding="utf-8"), source=path)

    def load_job_posting(self, slug: str) -> JobPosting:
        """Load a previously intaken posting from `jobs/<slug>/jd.json`."""
        path = self._dir / "jobs" / slug / "jd.json"
        return JobPosting.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_job_posting(self, posting: JobPosting) -> Path:
        """Write the posting to `jobs/<slug>/` as `jd.json` + `jd.md`; return the md path."""
        folder = self._jobs_dir / posting.slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "jd.json").write_text(
            json.dumps(posting.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        md_path = folder / "jd.md"
        md_path.write_text(posting.to_markdown(), encoding="utf-8")
        return md_path

    def read_artifact(self, slug: str, filename: str) -> str:
        """Read an artifact under `jobs/<slug>/`."""
        return (self._jobs_dir / slug / filename).read_text(encoding="utf-8")

    def write_artifact(self, slug: str, filename: str, content: str) -> Path:
        """Write `content` to `jobs/<slug>/<filename>`; return that path."""
        folder = self._jobs_dir / slug
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        path.write_text(content, encoding="utf-8")
        return path

    def write_leads(self, content: str) -> Path:
        """Write the leads document to `jobs/leads.md`; return that path."""
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        path = self._jobs_dir / "leads.md"
        path.write_text(content, encoding="utf-8")
        return path

    @property
    def _jobs_dir(self) -> Path:
        return self._dir / "jobs"
