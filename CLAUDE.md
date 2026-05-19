# Quiver — project guide

Quiver is a job-search harness agent on the Claude Agent SDK. Roadmap: `docs/plan.md`.

## Architecture

Clean Architecture; dependencies point inward only:
- `domain/` — pure value objects + interfaces (`ports.py`). Zero imports from outer layers.
- `application/` — orchestration over domain interfaces. Never imports infrastructure.
- `infrastructure/` — Claude Agent SDK, web, `gh`, filesystem adapters.
- `cli.py` — composition root. Wiring only, no business logic.

## Conventions

- BDD-driven: a `.feature` scenario before new behavior → RED test → GREEN → REFACTOR.
- `~/Documents/Work Research/` is the knowledge base + output area; `frad-lee-profile.md`
  is the read-only source of truth.
- Honesty harness: never state a fact without traceable evidence; flag unverified JDs;
  GitHub numbers come from the `verify_github` tool, never guessed.
- Python: uv. Use `uv add` / `uv remove`; never hand-edit `pyproject.toml` dependencies.
- Lint/type: `ruff` + `mypy` (strict on `src`).
- 鉴权：claude-agent-sdk 的 `query()` 默认无头运行 Claude Code CLI 并复用其登录会话——无需 API key。

## Commands

- `uv run pytest` — all tests, offline
- `uv run ruff check .` / `uv run mypy`
- `uv run quiver smoke` — live SDK connectivity check (on demand)
