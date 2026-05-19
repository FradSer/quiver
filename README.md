# Quiver ![Python 3.13](https://img.shields.io/badge/python-3.13-blue) ![Status: Complete](https://img.shields.io/badge/status-complete-brightgreen)

[![Built with Claude Agent SDK](https://img.shields.io/badge/built_with-Claude_Agent_SDK-orange)](https://code.claude.com/docs/en/agent-sdk) [![Tests](https://img.shields.io/badge/tests-64_passing-brightgreen)](#development)

**English** | [简体中文](README.zh-CN.md)

A job-search harness agent built on the Claude Agent SDK. Quiver finds job leads, intakes and verifies job descriptions, produces honest match analyses, tailors resumes, and drafts application emails.

## Why "harness"

The model is one part; everything around it — verification, review gates, a single source of truth, tool wiring — is the harness. Quiver's defining feature is its **honesty harness**: guardrails that stop the agent from inventing facts, inflating claims, or trusting an unverified job description.

How it works:

- The intake agent annotates every job posting with a `verification_status` (verified, pasted, reconstructed). Only verified and pasted descriptions are trusted.
- The reviewer agent is a fact-check gate — it catches overclaims in resumes and emails before they ship.
- The profile file is read-only — no agent can modify the source of truth.
- GitHub star counts come from the `gh` CLI at runtime, never from the model's memory.

## Setup

```bash
uv sync
```

Quiver authenticates through your logged-in Claude Code CLI — no API key needed. The Agent SDK runs the CLI headlessly and reuses its session. Run `claude` once to confirm you're logged in.

To use a direct Anthropic API key instead, copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Configuration

All paths and personal information are configurable via `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | _(none)_ | Direct API key; omit to reuse Claude Code CLI session |
| `QUIVER_KNOWLEDGE_DIR` | `~/Documents/Work Research` | Knowledge base directory (profile + artifacts) |
| `QUIVER_PROFILE_FILENAME` | `profile.md` | Profile filename inside the knowledge directory |

## Commands

```bash
quiver --version          # print version
quiver smoke              # verify SDK connectivity (live call)
quiver intake <file|url>  # parse a job description into a structured posting
quiver analyze            # produce a match report against your profile
quiver tailor             # generate a tailored resume for a posting
quiver email              # draft an application email
quiver review <artifact>  # fact-check an artifact for overclaims
quiver scout              # search for job leads via web
quiver run <file|url>     # full pipeline: intake -> analyze -> tailor -> email
quiver eval               # run golden-case evaluation (live calls)
```

## Architecture

Clean Architecture, four layers with dependencies pointing inward:

```
domain/          pure value objects and interfaces — zero external imports
application/     orchestration over domain interfaces — no infrastructure imports
infrastructure/  Claude Agent SDK, filesystem, GitHub CLI adapters
cli.py           composition root — wiring only, no business logic
```

Six sub-agents handle distinct responsibilities:

| Agent | Role |
|-------|------|
| **Scout** | Searches the web for job leads |
| **Intake** | Parses job descriptions into structured postings |
| **Analyst** | Produces match reports against the candidate profile |
| **Reviewer** | Fact-checks artifacts for honesty and overclaims |
| **Tailor** | Generates tailored resumes |
| **Writer** | Drafts application emails |

An evaluation harness (`evaluation/`) exercises the real agents against golden cases to catch regressions in the honesty checks.

## Development

```bash
uv run pytest            # all tests, offline (64 tests)
uv run ruff check .      # lint
uv run mypy              # type check (strict mode)
uv run quiver smoke      # live SDK connectivity check
uv run quiver eval       # golden-case evaluation, writes eval-report.md
```

BDD-driven: a `.feature` scenario comes first, then a RED test, then the implementation. Feature files live in `tests/features/`.

## Project status

All phases (P0–P8) are complete. See [`docs/plan.md`](docs/plan.md) for the full roadmap.
