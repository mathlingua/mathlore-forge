"""Command-line interface for Mathlore Forge."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from mathlore_forge.agents.mathlingua_agent import MathlinguaAgent, create_mathlingua_agent
from mathlore_forge.config import ensure_env_loaded, load_config
from mathlore_forge.goldens.cli import app as goldens_app
from mathlore_forge.mlg.client import MlgClient

ensure_env_loaded()

app = typer.Typer(
    name="mathlore-forge",
    help="Durable, self-improving AI forge system for Mathlore written in Mathlingua.",
    no_args_is_help=True,
)
app.add_typer(goldens_app, name="goldens", help="Author, run, and inspect Mathlingua agent golden tests.")
console = Console()


@app.command()
def author(
    content_root: Path = typer.Option(
        ...,
        "--content-root",
        "-r",
        help="Root directory of the Mathlingua content collection.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    prompt: str = typer.Option(
        ...,
        "--prompt",
        "-p",
        help="Instruction describing what Mathlingua content to author.",
    ),
    file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Target .mlg file (e.g. 07_algebra/02_groups.mlg).",
    ),
    after_id: Optional[str] = typer.Option(
        None,
        "--after-id",
        "-a",
        help="UUID of the item after which the new item should be inserted.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Gemini model name to use (defaults to gemini-3.8-flash).",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Gemini API key override.",
    ),
) -> None:
    """Author Mathlingua content and update collection files."""
    console.print(f"[bold cyan]🚀 Initializing Mathlingua Agent for `{content_root}`...[/bold cyan]")

    full_prompt = prompt
    if file and after_id:
        full_prompt = f"{prompt} in file '{file}' after item with ID '{after_id}'."
    elif file:
        full_prompt = f"{prompt} in file '{file}'."

    async def _run() -> None:
        agent = create_mathlingua_agent(
            content_root=content_root,
            model=model,
            api_key=api_key,
        )
        async with agent:
            console.print(f"[bold green]✍ Prompt:[/bold green] {full_prompt}")
            response = await agent.chat(full_prompt)
            console.print("[bold green]🤖 Agent Response:[/bold green]")
            console.print(await response.text())

    asyncio.run(_run())


@app.command()
def check(
    content_root: Path = typer.Option(
        ...,
        "--content-root",
        "-r",
        help="Root directory of the Mathlingua content collection.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    paths: Optional[list[str]] = typer.Argument(
        None,
        help="Optional paths to check (e.g. 07_algebra/02_groups.mlg).",
    ),
) -> None:
    """Run `mlg check` on the collection or specific files."""
    config = load_config(content_root=content_root)
    client = MlgClient(content_root=content_root, mlg_bin=config.resolve_mlg_bin())
    report = client.check(paths=paths)
    if report.successful:
        console.print(f"[bold green]✔ {report.summary()}[/bold green]")
    else:
        console.print(f"[bold red]✘ {report.summary()}[/bold red]")


@app.command()
def structure(
    content_root: Path = typer.Option(
        ...,
        "--content-root",
        "-r",
        help="Root directory of the Mathlingua content collection.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """Inspect collection structure, TOC, and items."""
    config = load_config(content_root=content_root)
    client = MlgClient(content_root=content_root, mlg_bin=config.resolve_mlg_bin())
    out = client.structure()
    console.print(out)


@app.command()
def search(
    query: str = typer.Argument(..., help="Query string to search for."),
    content_root: Path = typer.Option(
        ...,
        "--content-root",
        "-r",
        help="Root directory of the Mathlingua content collection.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """Search items and definitions in the Mathlingua collection."""
    config = load_config(content_root=content_root)
    client = MlgClient(content_root=content_root, mlg_bin=config.resolve_mlg_bin())
    out = client.search(query=query)
    console.print(out)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host interface to bind to."),
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development."),
) -> None:
    """Start the Mathlore Forge Web Dashboard and Webhook server."""
    import uvicorn
    console.print(f"[bold green]🚀 Starting Mathlore Forge Web Dashboard on http://{host}:{port}...[/bold green]")
    uvicorn.run("mathlore_forge.web.app:app", host=host, port=port, reload=reload)


@app.command()
def plan(
    repo: str = typer.Option("mathlingua/mathlore", "--repo", "-r", help="Target repository."),
    issue: Optional[int] = typer.Option(None, "--issue", "-i", help="GitHub issue number to formulate or refine a plan for."),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Topic or proposal title if running ad-hoc without issue."),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Abstract proposal directive or description."),
    refine: Optional[str] = typer.Option(None, "--refine", help="Feedback to refine an existing proposal."),
    execute: bool = typer.Option(False, "--execute", help="Execute the approved plan and open a PR."),
) -> None:
    """Formulate, refine, or execute high-order pedagogical plans with the Curator Agent."""
    from mathlore_forge.storage.db import init_db
    from mathlore_forge.workflows.curation_flow import CurationFlow
    from mathlore_forge.workflows.github_client import GitHubClient

    async def _run() -> None:
        flow = CurationFlow()
        db_mgr = init_db()
        with db_mgr.get_session() as session:
            if execute:
                if not issue:
                    console.print("[bold red]--issue is required to execute an approved plan.[/bold red]")
                    return
                console.print(f"[bold cyan]🚀 Executing approved plan for {repo}#{issue}...[/bold cyan]")
                await flow.handle_plan_execution(repo=repo, issue_number=issue, db_session=session)
                console.print("[bold green]✔ Plan execution completed and PR submitted![/bold green]")
                return

            if refine:
                if not issue:
                    console.print("[bold red]--issue is required to refine an existing plan.[/bold red]")
                    return
                console.print(f"[bold cyan]🔍 Refining plan for {repo}#{issue} with feedback...[/bold cyan]")
                updated_plan = await flow.handle_proposal_refinement(
                    repo=repo, issue_number=issue, user_feedback=refine, db_session=session
                )
                console.print("[bold green]✔ Refined Proposal:[/bold green]")
                console.print(updated_plan)
                return

            # Formulate initial plan
            if issue is not None:
                console.print(f"[bold cyan]🏛 Formulating plan for {repo}#{issue}...[/bold cyan]")
                gh = GitHubClient()
                gh_issue = await gh.get_issue(repo, issue)
                proposal = await flow.handle_initial_proposal(
                    repo=repo,
                    issue_number=issue,
                    issue_title=gh_issue.title,
                    issue_body=gh_issue.body,
                    author=gh_issue.author,
                    db_session=session,
                )
            elif title and prompt:
                console.print(f"[bold cyan]🏛 Formulating ad-hoc architectural proposal for '{title}'...[/bold cyan]")
                proposal = await flow.curator_agent.draft_proposal(issue_title=title, issue_body=prompt)
            else:
                console.print("[bold red]Please specify either --issue, or both --title and --prompt.[/bold red]")
                return

            console.print("[bold green]✔ Proposal Generated:[/bold green]")
            console.print(proposal)

    asyncio.run(_run())


@app.command()
def worker(
    repo: str = typer.Option("mathlingua/mathlore", "--repo", "-r", help="Target repository."),
    issue: Optional[int] = typer.Option(None, "--issue", "-i", help="Issue number to author content for."),
    plan_issue: Optional[int] = typer.Option(None, "--plan-issue", help="Issue number to curate an architectural plan for."),
    execute_plan: Optional[int] = typer.Option(None, "--execute-plan", help="Issue number whose approved plan should be executed."),
    pr: Optional[int] = typer.Option(None, "--pr", help="Pull request number to address review comments for."),
    flywheel_pr: Optional[int] = typer.Option(None, "--flywheel-pr", help="PR number to run flywheel reflection on and merge."),
) -> None:
    """Execute a long-running agent worker task (ideal for GCP Cloud Run Jobs)."""
    from mathlore_forge.storage.db import init_db
    from mathlore_forge.workflows.authoring_flow import AuthoringFlow
    from mathlore_forge.workflows.curation_flow import CurationFlow
    from mathlore_forge.workflows.flywheel_flow import FlywheelFlow
    from mathlore_forge.workflows.review_flow import ReviewFlow

    db_mgr = init_db()
    with db_mgr.get_session() as session:
        if issue is not None:
            console.print(f"[bold cyan]🤖 Starting Authoring Worker for {repo}#{issue}...[/bold cyan]")
            flow = AuthoringFlow()
            asyncio.run(flow.execute(repo=repo, issue_number=issue, db_session=session))
        elif plan_issue is not None:
            console.print(f"[bold cyan]🏛 Starting Curator Planning Worker for {repo}#{plan_issue}...[/bold cyan]")
            curation_flow = CurationFlow()
            from mathlore_forge.workflows.github_client import GitHubClient
            gh = GitHubClient()
            gh_issue = asyncio.run(gh.get_issue(repo, plan_issue))
            asyncio.run(
                curation_flow.handle_initial_proposal(
                    repo=repo,
                    issue_number=plan_issue,
                    issue_title=gh_issue.title,
                    issue_body=gh_issue.body,
                    author=gh_issue.author,
                    db_session=session,
                )
            )
        elif execute_plan is not None:
            console.print(f"[bold cyan]🚀 Starting Plan Execution Worker for {repo}#{execute_plan}...[/bold cyan]")
            curation_flow = CurationFlow()
            asyncio.run(curation_flow.handle_plan_execution(repo=repo, issue_number=execute_plan, db_session=session))
        elif pr is not None:
            console.print(f"[bold cyan]🔍 Starting Review Resolution Worker for {repo}#{pr}...[/bold cyan]")
            flow = ReviewFlow()
            asyncio.run(flow.execute(repo=repo, pr_number=pr, db_session=session))
        elif flywheel_pr is not None:
            console.print(f"[bold magenta]🔄 Starting Flywheel Self-Improvement for {repo}#{flywheel_pr}...[/bold magenta]")
            flow = FlywheelFlow()
            asyncio.run(flow.execute(mathlore_repo=repo, pr_number=flywheel_pr, db_session=session))
        else:
            console.print("[bold red]Please specify --issue, --plan-issue, --execute-plan, --pr, or --flywheel-pr.[/bold red]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
