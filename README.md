# Quiver

A job-search harness agent built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk).
Quiver finds job leads, intakes and verifies job descriptions, produces honest
match analyses, tailors résumés, and drafts application emails.

## Why "harness"

The model is one part; everything around it — verification, review gates,
a single source of truth, tool wiring — is the *harness*. Quiver's defining
feature is its **honesty harness**: guardrails that stop the agent from
inventing facts, inflating claims, or trusting an unverified job description.

## Status

P0 — scaffold. See [`docs/plan.md`](docs/plan.md) for the full P0–P7 roadmap.

## Setup

```bash
uv sync
```

Quiver authenticates through your **logged-in Claude Code CLI** — no API key needed
(the Agent SDK runs the CLI headlessly and reuses its session). Run `claude` once to
confirm you're logged in. To override with a direct Anthropic API key instead, copy
`.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Usage

```bash
uv run quiver --version
uv run quiver smoke              # verify SDK connectivity (makes a live call)
```

## Development

```bash
uv run ruff check .
uv run mypy
uv run pytest          # all tests, offline
uv run quiver smoke    # live SDK connectivity check (on demand)
```

Architecture: Clean Architecture (domain → application → infrastructure → CLI),
BDD-driven (`.feature` first).
