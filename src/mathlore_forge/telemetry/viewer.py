"""Trace viewer and live monitoring UI using Rich."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from rich.console import Console
from rich.table import Table
from rich.tree import Tree


class TraceViewer:
    """Provides CLI visualization for live monitoring and historical trace inspection."""

    def __init__(self, traces_dir: Path | str = "./traces"):
        self.traces_dir = Path(traces_dir)
        self.console = Console()

    def list_traces(self) -> list[dict[str, Any]]:
        """List all completed traces in the traces directory."""
        if not self.traces_dir.exists():
            return []

        trace_files = sorted(self.traces_dir.glob("trace_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        summaries = []

        for tf in trace_files:
            trace_id = tf.stem.replace("trace_", "")
            spans = []
            has_error = False
            total_duration = 0.0
            first_start = None
            root_span_name = "Unknown"

            try:
                with open(tf, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        span = json.loads(line)
                        spans.append(span)
                        if span.get("status") == "ERROR":
                            has_error = True
                        if span.get("parent_id") is None:
                            root_span_name = span.get("name", root_span_name)
                            total_duration = span.get("duration_seconds", 0.0)
                            first_start = span.get("start_time")

                start_formatted = (
                    datetime.fromtimestamp(first_start).strftime("%Y-%m-%d %H:%M:%S")
                    if first_start
                    else "Unknown"
                )

                summaries.append({
                    "trace_id": trace_id,
                    "root_task": root_span_name,
                    "spans_count": len(spans),
                    "duration_seconds": round(total_duration, 2),
                    "start_time": start_formatted,
                    "has_error": has_error,
                    "file_path": str(tf),
                })
            except Exception:
                continue

        return summaries

    def print_trace_list(self) -> None:
        traces = self.list_traces()
        if not traces:
            self.console.print("[yellow]No execution traces found in traces directory.[/yellow]")
            return

        table = Table(title="Mathlore Forge Past Executions", header_style="bold cyan")
        table.add_column("Trace ID", style="dim")
        table.add_column("Root Task", style="bold")
        table.add_column("Start Time", style="blue")
        table.add_column("Duration (s)", justify="right")
        table.add_column("Spans", justify="right")
        table.add_column("Status", justify="center")

        for t in traces:
            status_style = "[red]FAILED[/red]" if t["has_error"] else "[green]SUCCESS[/green]"
            table.add_row(
                t["trace_id"][:12] + "...",
                t["root_task"],
                t["start_time"],
                str(t["duration_seconds"]),
                str(t["spans_count"]),
                status_style,
            )

        self.console.print(table)

    def print_trace_tree(self, trace_id_prefix: str) -> None:
        """Find trace by ID prefix and render its hierarchical span tree."""
        matches = list(self.traces_dir.glob(f"trace_{trace_id_prefix}*.jsonl"))
        if not matches:
            self.console.print(f"[red]No trace matching prefix '{trace_id_prefix}' found.[/red]")
            return

        trace_file = matches[0]
        spans: list[dict[str, Any]] = []
        with open(trace_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    spans.append(json.loads(line))

        if not spans:
            self.console.print("[yellow]Trace file is empty.[/yellow]")
            return

        # Find root spans
        root_spans = [s for s in spans if s.get("parent_id") is None]
        if not root_spans:
            root_spans = [spans[0]]

        tree = Tree(f"[bold cyan]Execution Trace: {trace_file.stem}[/bold cyan]")
        for root in root_spans:
            self._add_span_to_tree(tree, root, spans)

        self.console.print(tree)

    def _add_span_to_tree(self, parent_tree: Tree, current_span: dict[str, Any], all_spans: list[dict[str, Any]]) -> None:
        name = current_span.get("name", "span")
        dur = round(current_span.get("duration_seconds", 0.0), 2)
        status = current_span.get("status", "OK")
        status_color = "red" if status == "ERROR" else "green"

        node_label = f"[{status_color}][{status}][/{status_color}] [bold]{name}[/bold] ({dur}s)"

        # Add attributes summary if present
        attrs = current_span.get("attributes", {})
        if attrs:
            attr_strings = [f"{k}={v}" for k, v in attrs.items() if not str(k).startswith("_")]
            if attr_strings:
                node_label += f" [dim]({', '.join(attr_strings[:3])})[/dim]"

        span_node = parent_tree.add(node_label)

        # Add events as leaf notes
        for ev in current_span.get("events", []):
            ev_name = ev.get("name")
            ev_attrs = ev.get("attributes", {})
            span_node.add(f"[magenta]Event:[/magenta] {ev_name} [dim]{json.dumps(ev_attrs)}[/dim]")

        # Recurse for children
        span_id = current_span.get("context", {}).get("span_id")
        children = [s for s in all_spans if s.get("parent_id") == span_id]
        for child in children:
            self._add_span_to_tree(span_node, child, all_spans)
