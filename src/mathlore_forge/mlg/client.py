"""Client for interacting with the `mlg` Mathlingua command-line interface."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class DiagnosticLocation(BaseModel):
    kind: str | None = None
    path: str | None = None
    absolute_path: str | None = Field(default=None, alias="absolutePath")
    line: int | None = None
    column: int | None = None

    model_config = {"populate_by_name": True}


class Diagnostic(BaseModel):
    level: str = "error"
    message: str = ""
    origin: str | None = None
    location: DiagnosticLocation | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnostic:
        loc_data = data.get("location") or {}
        span = loc_data.get("span") or {}
        start = span.get("start") or {}
        location = DiagnosticLocation(
            kind=loc_data.get("kind"),
            path=loc_data.get("path"),
            absolute_path=loc_data.get("absolutePath"),
            line=start.get("line"),
            column=start.get("column"),
        )
        return cls(
            level=data.get("level", "error"),
            message=data.get("message", ""),
            origin=data.get("origin"),
            location=location,
        )

    def format_line(self) -> str:
        """Formats the diagnostic into a concise human-readable message."""
        loc_str = ""
        if self.location:
            p = self.location.path or ""
            line = self.location.line
            col = self.location.column
            if line is not None and col is not None:
                loc_str = f"[{p}:{line}:{col}] "
            elif line is not None:
                loc_str = f"[{p}:{line}] "
            elif p:
                loc_str = f"[{p}] "
        prefix = f"[{self.level.upper()}] " if self.level else ""
        return f"{prefix}{loc_str}{self.message}"


class CheckReport(BaseModel):
    successful: bool
    issue_count: int = Field(default=0, alias="issueCount")
    files_checked: int = Field(default=0, alias="filesChecked")
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    raw_output: str = ""

    model_config = {"populate_by_name": True}

    def summary(self) -> str:
        """Generates a readable summary of the check result."""
        if self.successful and self.issue_count == 0:
            return f"Clean check: 0 errors across {self.files_checked} file(s)."
        diag_lines = [d.format_line() for d in self.diagnostics]
        return f"Check failed ({self.issue_count} issue(s) in {self.files_checked} file(s)):\n" + "\n".join(diag_lines)


class MlgClient:
    """Wrapper client for executing `mlg` commands within a Mathlingua collection."""

    def __init__(self, content_root: Path | str, mlg_bin: Path | str = "mlg"):
        self.content_root = Path(content_root).resolve()
        self.mlg_bin = str(mlg_bin)

    def run_raw(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Executes an `mlg` CLI invocation in the collection root."""
        cmd = [self.mlg_bin] + args
        try:
            return subprocess.run(
                cmd,
                cwd=str(self.content_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as err:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=127,
                stdout="",
                stderr=f"mlg binary not found at '{self.mlg_bin}': {err}",
            )

    def check(self, paths: list[str] | None = None, json_output: bool = True) -> CheckReport:
        """Runs `mlg check` to inspect syntax and semantic correctness.

        Note: When `formatOnCheck: true` is configured in `mlg.json`, `mlg check`
        also automatically formats `.mlg` files and assigns UUIDs to items lacking `Id:`.
        """
        args = ["check"]
        if json_output:
            args.append("--json")
        if paths:
            args.extend(paths)

        proc = self.run_raw(args)
        if json_output and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                diagnostics_raw = data.get("diagnostics", [])
                diagnostics = [Diagnostic.from_dict(d) for d in diagnostics_raw]
                return CheckReport(
                    successful=data.get("successful", proc.returncode == 0),
                    issue_count=data.get("issueCount", len(diagnostics)),
                    files_checked=data.get("filesChecked", 0),
                    diagnostics=diagnostics,
                    raw_output=proc.stdout,
                )
            except Exception:
                pass

        # Fallback if non-JSON or JSON parse failed
        diagnostics = []
        raw_text = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        for line in raw_text.strip().splitlines():
            line_str = line.strip()
            if line_str and not line_str.startswith("{"):
                diagnostics.append(Diagnostic(message=line_str, level="error" if proc.returncode != 0 else "info"))

        return CheckReport(
            successful=(proc.returncode == 0),
            issue_count=len(diagnostics),
            files_checked=len(paths) if paths else 1,
            diagnostics=diagnostics,
            raw_output=raw_text,
        )

    def structure(self, json_output: bool = True) -> str:
        """Runs `mlg structure` to inspect collection layout, TOC, and item IDs."""
        args = ["structure"]
        if json_output:
            args.append("--json")
        proc = self.run_raw(args)
        if proc.returncode != 0 and not proc.stdout:
            return f"Error running `mlg structure` (exit code {proc.returncode}): {proc.stderr}"
        return proc.stdout or proc.stderr

    def search(self, query: str, json_output: bool = True) -> str:
        """Runs `mlg search <query>` to search definitions and symbols."""
        args = ["search", query]
        if json_output:
            args.append("--json")
        proc = self.run_raw(args)
        if proc.returncode != 0 and not proc.stdout:
            return f"Error running `mlg search` (exit code {proc.returncode}): {proc.stderr}"
        return proc.stdout or proc.stderr

    def format(self) -> str:
        """Runs `mlg format` to reformat `.mlg` files in the collection."""
        proc = self.run_raw(["format"])
        if proc.returncode != 0:
            return f"Error running `mlg format` (exit code {proc.returncode}): {proc.stderr}"
        return proc.stdout or "Files reformatted successfully."

    def version(self) -> str:
        """Returns the Mathlingua version string."""
        proc = self.run_raw(["--version"])
        return proc.stdout.strip() or proc.stderr.strip()
