"""Command Line Interface for Mathlore Forge."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from mathlore_forge.config import AppConfig
from mathlore_forge.db.schema import TodoStatus
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.flywheel.goldens import GoldenManager
from mathlore_forge.mlg.client import MlgClient
from mathlore_forge.telemetry.viewer import TraceViewer
from mathlore_forge.workflows.cycle import MathloreForgeWorkflow, WorkflowOptions

app = typer.Typer(
    name="mathlore-forge",
    help="Durable, self-improving AI forge system for Mathlore written in Mathlingua",
    no_args_is_help=True,
)
traces_app = typer.Typer(name="traces", help="OpenTelemetry trace management and execution inspection")
app.add_typer(traces_app, name="traces")

console = Console()


@app.command()
def run(
    steer: Optional[str] = typer.Option(None, "--steer", "-s", help="Steer the agent on what type of things to add"),
    interactive: bool = typer.Option(True, "--interactive/--auto", help="Interactive human-in-the-loop vs Autonomous execution"),
    max_iterations: int = typer.Option(1, "--max-iterations", "-n", help="Max cycles to loop plan -> write in auto mode"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Run Mathlore generation cycle (plan -> review -> write -> verify -> learn)."""
    cfg = AppConfig.load(config_file)
    console.print(Panel(
        f"[bold cyan]Mathlore Forge[/bold cyan]\n"
        f"Mode: [bold]{'Interactive' if interactive else 'Auto'}[/bold]\n"
        f"Max Iterations: [bold]{max_iterations}[/bold]\n"
        f"Steering: [italic]{steer or 'None (Autonomous curriculum flow)'}[/italic]\n"
        f"Mathlore Repo: {cfg.paths.mathlore_repo}\n"
        f"Database: {cfg.dbos_system_database_url}",
        title="Starting Forge",
        border_style="cyan",
    ))

    workflow = MathloreForgeWorkflow(cfg)
    try:
        current_interactive = interactive
        for it in range(1, max_iterations + 1):
            if max_iterations > 1:
                console.print(f"\n[bold magenta]=== Starting Cycle {it}/{max_iterations} ===[/bold magenta]")

            options = WorkflowOptions(
                steering_prompt=steer or "",
                interactive=current_interactive,
                max_iterations=max_iterations,
                iteration_id=f"cycle_{it}_{int(Path().stat().st_mtime if Path().exists() else 0)}",
            )
            result = workflow.run_cycle(options)
            current_interactive = result.interactive

            if not result.successful:
                console.print(f"[bold red]Cycle {it} completed with errors.[/bold red]")
                if not current_interactive:
                    break
            else:
                console.print(f"[bold green]Cycle {it} completed successfully![/bold green]")
                console.print(f"Authored {result.authored_items_count} item(s).")
                if result.golden_test_id:
                    console.print(f"Recorded golden regression test: [cyan]{result.golden_test_id}[/cyan]")
    finally:
        workflow.shutdown()


@app.command()
def sync(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Synchronize layout and content structure from Mathlore repo into metadata store."""
    cfg = AppConfig.load(config_file)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")

    console.print(f"[bold cyan]Syncing layout from {cfg.paths.mathlore_repo}...[/bold cyan]")
    structure = client.structure()
    sections = store.sync_from_collection_structure(structure)
    console.print(f"[green]Successfully synced {len(sections)} sections ({len(structure.directories)} directories, {len(structure.files)} files).[/green]")


@app.command()
def status(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """View the current Mathlore layout, TODO items queue, and flagged language gaps."""
    cfg = AppConfig.load(config_file)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")

    # Sections table
    sections = store.get_sections()
    if not sections or not any(s.defined_commands for s in sections if not s.is_directory):
        # Auto-sync on first status call or to backfill defined_commands
        client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
        structure = client.structure()
        sections = store.sync_from_collection_structure(structure)
    sec_table = Table(title="Mathlore Layout & Content Sections", header_style="bold cyan")
    sec_table.add_column("Path", style="dim", overflow="fold")
    sec_table.add_column("Title", style="bold", overflow="fold")
    sec_table.add_column("Type", justify="center")
    sec_table.add_column("Definition Commands", overflow="fold")

    for s in sections:
        if s.is_directory:
            cmds_display = "[dim]—[/dim]"
        elif s.defined_commands:
            cmds_display = ", ".join(f"[cyan]{escape(c)}[/cyan]" for c in s.defined_commands)
        else:
            cmds_display = "[dim](none)[/dim]"

        sec_table.add_row(
            s.path,
            s.title or "<untitled>",
            "Directory" if s.is_directory else "File",
            cmds_display,
        )
    console.print(sec_table)

    # TODO queue table
    todos = store.get_todo_items()
    if todos:
        todo_table = Table(title="\nTODO Items Queue", header_style="bold yellow")
        todo_table.add_column("ID", style="dim")
        todo_table.add_column("Title", style="bold")
        todo_table.add_column("Kind", style="blue")
        todo_table.add_column("Section")
        todo_table.add_column("Status", justify="center")

        for t in todos:
            status_style = {
                TodoStatus.TODO: "[yellow]TODO[/yellow]",
                TodoStatus.IN_PROGRESS: "[blue]IN_PROGRESS[/blue]",
                TodoStatus.DONE: "[green]DONE[/green]",
                TodoStatus.BLOCKED_GAP: "[red]BLOCKED_GAP[/red]",
                TodoStatus.FAILED: "[red]FAILED[/red]",
            }.get(t.status, str(t.status.value))
            todo_table.add_row(t.id, t.title, t.kind, t.section_path, status_style)
        console.print(todo_table)

    # Flagged gaps
    gaps = store.get_unresolved_gaps()
    if gaps:
        gap_table = Table(title="\nFlagged Mathlingua Language Gaps", header_style="bold red")
        gap_table.add_column("ID", style="dim")
        gap_table.add_column("Concept", style="bold red")
        gap_table.add_column("Description")
        gap_table.add_column("Item ID")

        for g in gaps:
            gap_table.add_row(str(g.id), g.concept, g.description, g.item_id)
        console.print(gap_table)


@traces_app.command("list")
def traces_list(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """List historical OpenTelemetry execution traces."""
    cfg = AppConfig.load(config_file)
    viewer = TraceViewer(traces_dir=cfg.paths.traces_dir)
    viewer.print_trace_list()


@traces_app.command("show")
def traces_show(
    trace_id: str = typer.Argument(..., help="Trace ID or prefix to display"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Display the full span tree, events, and timings for a specific execution trace."""
    cfg = AppConfig.load(config_file)
    viewer = TraceViewer(traces_dir=cfg.paths.traces_dir)
    viewer.print_trace_tree(trace_id)


@app.command()
def eval(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Run regression evaluation against all recorded golden test cases."""
    cfg = AppConfig.load(config_file)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    goldens = GoldenManager(store, cfg.paths.goldens_dir)

    console.print("[bold cyan]Running Golden Case Regression Evaluation...[/bold cyan]\n")
    results = goldens.run_eval(client)

    if results.total_cases == 0:
        console.print("[yellow]No golden test cases found. Complete a successful run to generate one.[/yellow]")
        return

    table = Table(title="Golden Test Regression Results", header_style="bold cyan")
    table.add_column("Case ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Compiler", justify="center")
    table.add_column("Symbols", justify="center")
    table.add_column("Citations", justify="center")
    table.add_column("Result", justify="center")

    for r in results.case_results:
        res_label = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(
            r.case_id,
            r.name,
            "[green]CLEAN[/green]" if r.compiler_clean else "[red]FAIL[/red]",
            "[green]OK[/green]" if r.symbols_verified else "[red]FAIL[/red]",
            "[green]OK[/green]" if r.citations_verified else "[red]FAIL[/red]",
            res_label,
        )

    console.print(table)
    summary_color = "green" if results.failed_cases == 0 else "red"
    console.print(
        f"\n[{summary_color}]Total: {results.total_cases} | Passed: {results.passed_cases} | Failed: {results.failed_cases}[/{summary_color}]"
    )


@app.command()
def flywheel(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Display learned rules and user feedback history accumulated by the flywheel."""
    cfg = AppConfig.load(config_file)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")

    feedbacks = store.get_all_feedback()
    if not feedbacks:
        console.print("[yellow]No user feedback or learned rules recorded yet.[/yellow]")
        return

    table = Table(title="Flywheel Learned Rules & Style Principles", header_style="bold cyan")
    table.add_column("Phase", style="blue")
    table.add_column("Learned Rule", style="bold green")
    table.add_column("User Feedback", style="dim")
    table.add_column("Recorded At", style="dim")

    for f in feedbacks:
        table.add_row(
            f.phase.value,
            f.learned_rule or "<no rule extracted>",
            f.user_feedback,
            f.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
