"""Quiver command-line interface — the composition root. Wiring only."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

from quiver import __version__
from quiver.application.analyst import AnalysisError, AnalystService
from quiver.application.intake import IntakeService, JdUnavailableError
from quiver.application.pipeline import Pipeline, PipelineGateError
from quiver.application.reviewer import ReviewError, ReviewerService
from quiver.application.scout import ScoutService
from quiver.application.tailor import TailorError, TailorService
from quiver.application.writer import WriterError, WriterService
from quiver.domain.models import MatchRating, ReviewResult, leads_to_markdown
from quiver.evaluation.runner import EvalRunner
from quiver.infrastructure.sdk_runner import ClaudeAgentRunner
from quiver.infrastructure.store import FileSystemArtifactStore

from rich.console import Console
from rich.status import Status
from rich.panel import Panel
from rich.theme import Theme

# Custom theme for Quiver
theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
    "highlight": "magenta",
})
console = Console(theme=theme)

# Load .env before any command resolves env-configured paths.
load_dotenv()

app = typer.Typer(
    help="Quiver — a job-search harness agent built on the Claude Agent SDK.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the Quiver version and exit.",
    ),
    knowledge_dir: Path = typer.Option(
        None,
        "--dir",
        envvar="QUIVER_KNOWLEDGE_DIR",
        help="Knowledge base directory (overrides .env).",
        dir_okay=True,
        file_okay=False,
    ),
    profile_file: str = typer.Option(
        None,
        "--profile",
        envvar="QUIVER_PROFILE_FILENAME",
        help="Profile filename inside knowledge directory (overrides .env).",
    ),
) -> None:
    """Quiver — a job-search harness agent."""
    # Ensure any passed-in options are set in the environment so services can pick them up
    if knowledge_dir:
        import os
        os.environ["QUIVER_KNOWLEDGE_DIR"] = str(knowledge_dir)
    if profile_file:
        import os
        os.environ["QUIVER_PROFILE_FILENAME"] = profile_file


def _read_jd(text: str | None) -> str:
    return text if text is not None else sys.stdin.read()


def _review_filename(artifact: str) -> str:
    """`resume.md` -> `resume.review.md`."""
    return f"{artifact.removesuffix('.md')}.review.md"


def _echo_review(label: str, review: ReviewResult) -> None:
    if review.is_clean:
        typer.echo(f"  {label} review: clean — no honesty issues found")
        return
    typer.echo(f"  {label} review: {len(review.issues)} issue(s) flagged", err=True)
    for issue in review.issues:
        typer.echo(f"    - {issue.claim} — {issue.problem}", err=True)


@app.command()
def smoke(
    prompt: str = typer.Argument(
        "Reply with the single word: pong.",
        help="The prompt to send through the SDK.",
    ),
) -> None:
    """Verify Claude Agent SDK connectivity with a trivial prompt."""
    reply = asyncio.run(ClaudeAgentRunner().run(prompt)).strip()
    if not reply:
        typer.echo("smoke: FAILED — empty completion", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"smoke: OK — {reply}")


@app.command()
def intake(
    text: str | None = typer.Argument(None, help="Job description text. Omit to read stdin."),
    url: str | None = typer.Option(None, "--url", help="Fetch the JD from this URL."),
) -> None:
    """Turn a job description into a structured posting under jobs/<slug>/."""
    service = IntakeService(ClaudeAgentRunner())
    store = FileSystemArtifactStore()
    try:
        with console.status("[bold blue]Intaking job description...") as status:
            posting = asyncio.run(service.from_url(url) if url else service.from_text(_read_jd(text)))
    except JdUnavailableError as exc:
        console.print(f"[error]intake failed:[/error] {exc}")
        console.print("[info]Tip: paste the JD text directly — job boards are often JS apps.[/info]")
        raise typer.Exit(code=1) from exc
    path = store.save_job_posting(posting)
    console.print(Panel(
        f"[success]intake OK[/success] — {posting.company} / {posting.title}\n"
        f"  [info]verification:[/info] {posting.verification_status.value}\n"
        f"  [info]written:[/info] {path}",
        title="Intake Complete",
        expand=False
    ))
    console.print(f"\n[bold]Next step:[/bold] `quiver analyze {posting.slug}`")


@app.command()
def analyze(
    slug: str = typer.Argument(..., help="Slug of an intaken job (jobs/<slug>/)."),
) -> None:
    """Analyze the candidate against an intaken job; write match-report.md."""
    if ".." in slug or "/" in slug:
        console.print(f"[error]Invalid slug:[/error] {slug}", err=True)
        raise typer.Exit(code=1)
    store = FileSystemArtifactStore()
    try:
        posting = store.load_job_posting(slug)
    except FileNotFoundError as exc:
        console.print(f"[error]no intaken job at slug '{slug}'[/error] — run `quiver intake` first", err=True)
        raise typer.Exit(code=1) from exc
    profile = store.load_profile()
    try:
        with console.status(f"[bold blue]Analyzing match for {posting.company}...") as status:
            report = asyncio.run(AnalystService(ClaudeAgentRunner()).analyze(profile, posting))
    except AnalysisError as exc:
        console.print(f"[error]analysis failed:[/error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    path = store.write_artifact(slug, "match-report.md", report.to_markdown())
    strong = sum(1 for a in report.assessments if a.rating is MatchRating.STRONG)
    console.print(Panel(
        f"[success]analyze OK[/success] — {posting.company} / {posting.title}\n"
        f"  [info]{len(report.assessments)}[/info] requirements assessed, [success]{strong}[/success] rated strong\n"
        f"  [info]written:[/info] {path}",
        title="Analysis Complete",
        expand=False
    ))
    console.print(f"\n[bold]Next step:[/bold] `quiver tailor {slug}` OR `quiver email {slug}`")


@app.command()
def tailor(
    slug: str = typer.Argument(..., help="Slug of an analyzed job (needs match-report.md)."),
) -> None:
    """Write a job-tailored résumé to jobs/<slug>/resume.md."""
    store = FileSystemArtifactStore()
    try:
        posting = store.load_job_posting(slug)
        report_md = store.read_artifact(slug, "match-report.md")
    except FileNotFoundError as exc:
        typer.echo(f"missing intake/analysis for '{slug}' — run intake then analyze", err=True)
        raise typer.Exit(code=1) from exc
    profile = store.load_profile()
    try:
        resume = asyncio.run(TailorService(ClaudeAgentRunner()).tailor(profile, posting, report_md))
    except TailorError as exc:
        typer.echo(f"tailor failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    path = store.write_artifact(slug, "resume.md", resume.markdown)
    typer.echo(f"tailor OK — written: {path}")


@app.command()
def email(
    slug: str = typer.Argument(..., help="Slug of an analyzed job (needs match-report.md)."),
) -> None:
    """Draft an application email to jobs/<slug>/email.md."""
    store = FileSystemArtifactStore()
    try:
        posting = store.load_job_posting(slug)
        report_md = store.read_artifact(slug, "match-report.md")
    except FileNotFoundError as exc:
        typer.echo(f"missing intake/analysis for '{slug}' — run intake then analyze", err=True)
        raise typer.Exit(code=1) from exc
    profile = store.load_profile()
    try:
        draft = asyncio.run(WriterService(ClaudeAgentRunner()).write(profile, posting, report_md))
    except WriterError as exc:
        typer.echo(f"email failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    path = store.write_artifact(slug, "email.md", draft.to_markdown())
    typer.echo(f"email OK — written: {path}")


@app.command()
def review(
    slug: str = typer.Argument(..., help="Slug of a job."),
    filename: str = typer.Argument("match-report.md", help="Artifact file to review."),
) -> None:
    """Fact-check an artifact against the profile; write <artifact>.review.md."""
    store = FileSystemArtifactStore()
    try:
        artifact = store.read_artifact(slug, filename)
    except FileNotFoundError as exc:
        typer.echo(f"no artifact '{filename}' for '{slug}'", err=True)
        raise typer.Exit(code=1) from exc
    profile = store.load_profile()
    try:
        result = asyncio.run(ReviewerService(ClaudeAgentRunner()).review(profile, artifact))
    except ReviewError as exc:
        typer.echo(f"review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    path = store.write_artifact(slug, _review_filename(filename), result.to_markdown())
    typer.echo(f"review OK — written: {path}")
    _echo_review(filename, result)


@app.command()
def scout() -> None:
    """Search the web for job leads matching the profile; write jobs/leads.md."""
    store = FileSystemArtifactStore()
    profile = store.load_profile()
    leads = asyncio.run(ScoutService(ClaudeAgentRunner()).discover(profile))
    path = store.write_leads(leads_to_markdown(leads))
    typer.echo(f"scout OK — {len(leads)} lead(s) found")
    typer.echo(f"  written: {path}")


@app.command()
def run(
    text: str | None = typer.Argument(None, help="Job description text. Omit to read stdin."),
    url: str | None = typer.Option(None, "--url", help="Fetch the JD from this URL."),
) -> None:
    """Run the full pipeline: intake -> analyze -> tailor -> email, gated by the reviewer."""
    store = FileSystemArtifactStore()
    runner = ClaudeAgentRunner()
    pipeline = Pipeline(
        intake=IntakeService(runner),
        analyst=AnalystService(runner),
        tailor=TailorService(runner),
        writer=WriterService(runner),
        reviewer=ReviewerService(runner),
    )
    try:
        with console.status("[bold blue]Running full pipeline (this may take a minute)...") as status:
            if url:
                # Intake happens first to get the JD
                intake_service = IntakeService(runner)
                posting = asyncio.run(intake_service.from_url(url))
                result = asyncio.run(pipeline.run_with_posting(posting, store.load_profile(), store=store))
            else:
                result = asyncio.run(pipeline.run(_read_jd(text), store.load_profile(), store=store))
    except PipelineGateError as exc:
        console.print(f"[error]run BLOCKED[/error] — {exc.stage} gate flagged honesty issues", err=True)
        for name, review in exc.reviews:
            _echo_review(name, review)
        console.print("\n[warning]No artifacts written. Fix the profile or inputs, then re-run.[/warning]", err=True)
        raise typer.Exit(code=1) from exc
    except (JdUnavailableError, AnalysisError, TailorError, WriterError, ReviewError) as exc:
        console.print(f"[error]pipeline failed:[/error] {exc}", err=True)
        raise typer.Exit(code=1) from exc
    slug = result.posting.slug
    store.save_job_posting(result.posting)
    store.write_artifact(slug, "match-report.md", result.report.to_markdown())
    store.write_artifact(slug, "resume.md", result.resume.markdown)
    store.write_artifact(slug, "email.md", result.email.to_markdown())
    store.write_artifact(slug, "match-report.review.md", result.report_review.to_markdown())
    store.write_artifact(slug, "resume.review.md", result.resume_review.to_markdown())
    store.write_artifact(slug, "email.review.md", result.email_review.to_markdown())
    console.print(Panel(
        f"[success]run OK[/success] — {result.posting.company} / {result.posting.title}\n"
        f"  [info]artifacts:[/info] jobs/{slug}/ (jd, match-report, resume, email, + reviews)\n"
        f"  [success]all three review gates passed — clean[/success]",
        title="Pipeline Complete",
        expand=False
    ))


@app.command(name="eval")
def evaluate(
    repeat: int = typer.Option(1, "--repeat", min=1, help="Run each eval case N times."),
) -> None:
    """Run the live evaluation harness against the real agents; write eval-report.md."""
    runner = ClaudeAgentRunner()
    eval_runner = EvalRunner(
        intake=IntakeService(runner),
        analyst=AnalystService(runner),
        reviewer=ReviewerService(runner),
        tailor=TailorService(runner),
    )
    report = asyncio.run(eval_runner.run(repeat=repeat))
    out = Path("eval-report.md")
    out.write_text(report.to_markdown(), encoding="utf-8")
    typer.echo(report.summary())
    typer.echo(f"  written: {out}")
    if report.verdict_failed:
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the `quiver` console script."""
    app()
