"""Command-line interface for running and managing Mathlingua agent golden tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from mathlore_forge.goldens.author import scaffold_new_test_case
from mathlore_forge.goldens.loader import discover_test_cases, load_test_case_from_path
from mathlore_forge.goldens.runner import (
    AgentAdapter,
    MathloreForgeAgentAdapter,
    MockAgentAdapter,
    SimulatedAgentAdapter,
    TestRunner,
)
from mathlore_forge.goldens.session import SessionManager

app = typer.Typer(
    name="goldens",
    help="CLI for authoring, running, and inspecting Mathlingua agent golden tests.",
    add_completion=False,
)
console = Console()


def _resolve_adapter(agent_choice: str, model: str | None = None) -> AgentAdapter:
    """Instantiates the requested agent adapter."""
    choice = agent_choice.strip().lower()
    if choice == "mock":
        return MockAgentAdapter()
    elif choice == "simulated":
        return SimulatedAgentAdapter()
    elif choice in ("forge", "mathlore-forge", "default"):
        return MathloreForgeAgentAdapter(model=model)
    elif ":" in agent_choice:
        # Custom import "module.path:factory_function"
        mod_name, func_name = agent_choice.split(":", 1)
        import importlib
        mod = importlib.import_module(mod_name)
        factory = getattr(mod, func_name)
        # If factory returns an AgentAdapter directly or callable
        if getattr(factory, "run", None):
            return factory
        return factory()
    else:
        # Default fallback
        return MathloreForgeAgentAdapter(model=model)


@app.command("run")
def run_tests_cmd(
    patterns: Annotated[
        Optional[list[str]],
        typer.Argument(help="Optional test IDs or substring patterns to run."),
    ] = None,
    tests_dir: Annotated[
        Path,
        typer.Option("--tests-dir", "-t", help="Directory containing golden test cases."),
    ] = Path("./golden_tests"),
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", "-r", help="Directory where run sessions and workspaces are stored."),
    ] = Path("./runs"),
    agent: Annotated[
        str,
        typer.Option("--agent", "-a", help="Agent adapter to test ('forge', 'simulated', 'mock', or 'mod:func')."),
    ] = "forge",
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="LLM model override for the agent."),
    ] = None,
    auto_cleanup: Annotated[
        bool,
        typer.Option("--auto-cleanup", help="Automatically delete sandbox on successful run."),
    ] = False,
    keep_on_failure: Annotated[
        bool,
        typer.Option("--keep-on-failure", help="Preserve sandbox workspace when a test fails."),
    ] = True,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", help="Filter test cases by tag."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show verbose output including assertion details."),
    ] = False,
) -> None:
    """Runs golden tests against an agent in isolated sandboxes."""
    cases = discover_test_cases(root_dir=tests_dir, patterns=patterns, tags=tag)
    if not cases:
        console.print(f"[yellow]No golden tests found matching criteria in '{tests_dir}'.[/yellow]")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold cyan]Running {len(cases)} Golden Test(s)[/bold cyan]\n"
            f"[dim]Agent:[/dim] [bold]{agent}[/bold] | [dim]Runs Directory:[/dim] {runs_dir}",
            border_style="cyan",
        )
    )

    session_mgr = SessionManager(runs_dir=runs_dir)
    adapter = _resolve_adapter(agent, model=model)
    runner = TestRunner(session_manager=session_mgr)

    total = len(cases)
    passed_count = 0
    failed_count = 0

    for idx, test_case in enumerate(cases, start=1):
        console.print(f"\n[bold][{idx}/{total}] Test: {test_case.id}[/bold] - {test_case.name}")
        console.print(f"  [dim]Prompt:[/dim] {test_case.prompt}")

        session, report = asyncio.run(
            runner.run_test(
                test_case=test_case,
                adapter=adapter,
                auto_cleanup=auto_cleanup,
                keep_on_failure=keep_on_failure,
            )
        )

        status_style = "green" if session.meta.status == "PASSED" else "red"
        console.print(
            f"  [dim]Session ID:[/dim] [bold]{session.meta.session_id}[/bold] "
            f"| [dim]Status:[/dim] [{status_style}][bold]{session.meta.status}[/bold][/{status_style}] "
            f"| [dim]Duration:[/dim] {session.meta.duration_seconds:.2f}s"
        )
        console.print(f"  [dim]Workspace:[/dim] [link=file://{session.meta.workspace_dir}]{session.meta.workspace_dir}[/link]")

        if report.passed:
            passed_count += 1
        else:
            failed_count += 1
            if report.failure_messages:
                console.print("  [bold red]Failures:[/bold red]")
                for fail in report.failure_messages:
                    console.print(f"    ❌ {fail}")

        if verbose or not report.passed:
            # Display assertions breakdown table
            table = Table(title=f"Assertions ({session.meta.session_id})", show_header=True)
            table.add_column("Category", style="cyan")
            table.add_column("Assertion", style="white")
            table.add_column("Status", justify="center")
            table.add_column("Details", style="dim")

            for a in report.assertions:
                icon = "[green]✓ PASS[/green]" if a.passed else "[red]✗ FAIL[/red]"
                table.add_row(a.category, a.name, icon, a.message or str(a.actual))

            console.print(table)

    console.print(
        f"\n[bold]Test Run Complete[/bold]: "
        f"[green]{passed_count} Passed[/green], "
        f"[red]{failed_count} Failed[/red] (Total: {total})"
    )

    if failed_count > 0:
        raise typer.Exit(code=1)


@app.command("runs")
def list_runs_cmd(
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", "-r", help="Runs directory."),
    ] = Path("./runs"),
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filter by status (PASSED, FAILED, ERROR)."),
    ] = None,
    last: Annotated[
        Optional[int],
        typer.Option("--last", "-n", help="Limit to last N sessions."),
    ] = None,
) -> None:
    """Lists prior test run sessions, their status, and directory locations."""
    mgr = SessionManager(runs_dir=runs_dir)
    sessions = mgr.list_sessions(status_filter=status)

    if not sessions:
        console.print(f"[dim]No sessions found in '{runs_dir}'.[/dim]")
        return

    if last and last > 0:
        sessions = sessions[-last:]

    table = Table(title="Prior Golden Test Runs", show_header=True)
    table.add_column("Session ID", style="bold cyan")
    table.add_column("Test ID", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Files Changed", justify="center")
    table.add_column("Workspace Directory", style="dim")

    for s in sessions:
        status_style = "green" if s.status == "PASSED" else ("red" if s.status in ("FAILED", "ERROR") else "yellow")
        changed = len(s.created_files) + len(s.modified_files) + len(s.deleted_files)
        table.add_row(
            s.session_id,
            s.test_id,
            f"[{status_style}]{s.status}[/{status_style}]",
            f"{s.duration_seconds:.1f}s",
            str(changed),
            s.workspace_dir,
        )

    console.print(table)


@app.command("show")
def show_run_cmd(
    session_id: Annotated[str, typer.Argument(help="Session ID (e.g. 'session-1' or '1').")],
    runs_dir: Annotated[Path, typer.Option("--runs-dir", "-r")] = Path("./runs"),
) -> None:
    """Inspects detailed outcomes and file locations of a specific session."""
    mgr = SessionManager(runs_dir=runs_dir)
    session = mgr.get_session(session_id)
    if not session:
        console.print(f"[red]Session '{session_id}' not found in '{runs_dir}'.[/red]")
        raise typer.Exit(code=1)

    s_dir = Path(session.session_dir)
    status_style = "green" if session.status == "PASSED" else "red"

    panel_content = (
        f"[bold]Session ID:[/bold] {session.session_id}\n"
        f"[bold]Test:[/bold] {session.test_id} ({session.test_name})\n"
        f"[bold]Status:[/bold] [{status_style}]{session.status}[/{status_style}]\n"
        f"[bold]Duration:[/bold] {session.duration_seconds:.2f}s\n"
        f"[bold]Started:[/bold] {session.started_at}\n\n"
        f"[bold cyan]Locations:[/bold cyan]\n"
        f"- [bold]Session Dir:[/bold] {session.session_dir}\n"
        f"- [bold]Workspace Dir:[/bold] [link=file://{session.workspace_dir}]{session.workspace_dir}[/link]\n"
        f"- [bold]Diff Patch:[/bold] {s_dir / 'changes.diff'}\n"
        f"- [bold]Trajectory JSON:[/bold] {s_dir / 'trajectory.json'}\n"
        f"- [bold]Trajectory Markdown:[/bold] {s_dir / 'trajectory.md'}\n"
        f"- [bold]Report JSON:[/bold] {s_dir / 'report.json'}"
    )

    console.print(Panel(panel_content, title=f"Run Details: {session.session_id}", border_style="cyan"))

    # Show file changes
    if session.created_files or session.modified_files or session.deleted_files:
        console.print("\n[bold]Files Changed:[/bold]")
        for f in session.created_files:
            console.print(f"  [green]+ created:[/green] {f}")
        for f in session.modified_files:
            console.print(f"  [yellow]~ modified:[/yellow] {f}")
        for f in session.deleted_files:
            console.print(f"  [red]- deleted:[/red] {f}")


@app.command("diff")
def diff_cmd(
    session_id: Annotated[str, typer.Argument(help="Session ID (e.g. 'session-1' or '1').")],
    runs_dir: Annotated[Path, typer.Option("--runs-dir", "-r")] = Path("./runs"),
) -> None:
    """Shows the unified diff of changes made by the agent in a session."""
    mgr = SessionManager(runs_dir=runs_dir)
    s_dir = mgr.get_session_dir(session_id)
    if not s_dir:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        raise typer.Exit(code=1)

    diff_file = s_dir / "changes.diff"
    if not diff_file.is_file() or not diff_file.read_text(encoding="utf-8").strip():
        console.print("[dim]No file changes recorded in this session.[/dim]")
        return

    syntax = Syntax(diff_file.read_text(encoding="utf-8"), "diff", theme="monokai", line_numbers=True)
    console.print(syntax)


@app.command("trajectory")
def trajectory_cmd(
    session_id: Annotated[str, typer.Argument(help="Session ID (e.g. 'session-1' or '1').")],
    runs_dir: Annotated[Path, typer.Option("--runs-dir", "-r")] = Path("./runs"),
) -> None:
    """Shows the recorded execution trajectory (thoughts, tools, subagents) for a session."""
    mgr = SessionManager(runs_dir=runs_dir)
    s_dir = mgr.get_session_dir(session_id)
    if not s_dir:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        raise typer.Exit(code=1)

    md_file = s_dir / "trajectory.md"
    if md_file.is_file():
        from rich.markdown import Markdown
        console.print(Markdown(md_file.read_text(encoding="utf-8")))
    else:
        console.print("[dim]No trajectory markdown found for this session.[/dim]")


@app.command("clean")
def clean_cmd(
    session_id: Annotated[
        Optional[str],
        typer.Option("--session", "-s", help="Clean a specific session ID."),
    ] = None,
    all_runs: Annotated[
        bool,
        typer.Option("--all", help="Delete all run sessions."),
    ] = False,
    passed_only: Annotated[
        bool,
        typer.Option("--passed", help="Delete only PASSED sessions."),
    ] = False,
    failed_only: Annotated[
        bool,
        typer.Option("--failed", help="Delete only FAILED / ERROR sessions."),
    ] = False,
    runs_dir: Annotated[Path, typer.Option("--runs-dir", "-r")] = Path("./runs"),
) -> None:
    """Cleans up prior run sessions and workspaces."""
    mgr = SessionManager(runs_dir=runs_dir)

    if session_id:
        if mgr.clean_session(session_id):
            console.print(f"[green]Cleaned session '{session_id}'.[/green]")
        else:
            console.print(f"[yellow]Session '{session_id}' not found.[/yellow]")
        return

    if not all_runs and not passed_only and not failed_only:
        console.print("[yellow]Specify --all, --passed, --failed, or --session <id> to clean.[/yellow]")
        return

    status_filter = None
    if passed_only:
        status_filter = "PASSED"
    elif failed_only:
        status_filter = "FAILED"

    cleaned = mgr.clean_all(status_filter=status_filter)
    console.print(f"[green]Successfully deleted {cleaned} session(s) from '{runs_dir}'.[/green]")


@app.command("tests")
def list_tests_cmd(
    tests_dir: Annotated[
        Path,
        typer.Option("--tests-dir", "-t", help="Directory containing golden tests."),
    ] = Path("./golden_tests"),
) -> None:
    """Lists all available golden test cases."""
    cases = discover_test_cases(root_dir=tests_dir)
    if not cases:
        console.print(f"[dim]No golden test cases found in '{tests_dir}'.[/dim]")
        return

    table = Table(title="Available Golden Tests", show_header=True)
    table.add_column("ID", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Tags", style="dim")
    table.add_column("Description")

    for c in cases:
        table.add_row(c.id, c.name, ", ".join(c.tags), c.description or "-")

    console.print(table)


@app.command("new")
def new_test_cmd(
    test_id: Annotated[str, typer.Argument(help="Unique ID for the new test case (e.g. '04-define-vector-space').")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Human-readable title.")] = None,
    prompt: Annotated[Optional[str], typer.Option("--prompt", "-p", help="Task prompt for the agent.")] = None,
    target_dir: Annotated[Path, typer.Option("--dir", "-d", help="Directory where test should be created.")] = Path("./golden_tests"),
) -> None:
    """Scaffolds a new golden test case with test.yaml and starter scaffold files."""
    created_dir = scaffold_new_test_case(
        target_dir=target_dir,
        test_id=test_id,
        test_name=name,
        prompt=prompt,
    )
    console.print(f"[green]✓ Successfully scaffolded golden test case at:[/green]\n  [bold]{created_dir}[/bold]")
    console.print(f"  - Edit [bold]{created_dir / 'test.yaml'}[/bold] to customize prompt and expectations.")
    console.print(f"  - Add initial files in [bold]{created_dir / 'scaffold'}[/bold].")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
