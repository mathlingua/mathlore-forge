"""Command-line interface for Mathlore Forge."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from mathlore_forge.agents.mathlingua_agent import MathlinguaAgent, create_mathlingua_agent
from mathlore_forge.config import load_config
from mathlore_forge.goldens.cli import app as goldens_app
from mathlore_forge.mlg.client import MlgClient

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


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
