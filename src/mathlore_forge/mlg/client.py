"""Python wrapper client for the `mlg` CLI binary."""

import json
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field


class Diagnostic(BaseModel):
    message: str
    path: str | None = None
    row: int | None = None
    column: int | None = None
    level: str = "error"


class CheckReport(BaseModel):
    successful: bool
    issue_count: int = Field(default=0, alias="issueCount")
    files_checked: int = Field(default=0, alias="filesChecked")
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    raw_output: str = ""

    model_config = {"populate_by_name": True}


def decode_hex_command(hex_str: str) -> str | None:
    """Decodes a hex-encoded UTF-8 command key into a Mathlingua command string."""
    try:
        return bytes.fromhex(hex_str).decode("utf-8")
    except Exception:
        return None


class ItemStructure(BaseModel):
    id: str
    kind: str
    heading: str | None = None
    definition_keys: list[str] = Field(default_factory=list, alias="definitionKeys")
    commands: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class FileStructure(BaseModel):
    path: str
    title: str | None = None
    defined_commands: list[str] = Field(default_factory=list, alias="definedCommands")
    items: list[ItemStructure] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def all_commands(self) -> list[str]:
        """Returns all defined command signatures for this file, decoding if needed."""
        cmds: list[str] = []
        for cmd in self.defined_commands:
            if cmd and cmd not in cmds:
                cmds.append(cmd)
        for item in self.items:
            for cmd in item.commands:
                if cmd and cmd not in cmds:
                    cmds.append(cmd)
            for k in item.definition_keys:
                decoded = decode_hex_command(k)
                if decoded and decoded not in cmds:
                    cmds.append(decoded)
                elif not decoded and k.startswith("\\") and k not in cmds:
                    cmds.append(k)
        return cmds


class DirectoryStructure(BaseModel):
    path: str
    title: str | None = None
    has_preface: bool = Field(default=False, alias="hasPreface")

    model_config = {"populate_by_name": True}


class CollectionStructure(BaseModel):
    title: str
    directories: list[DirectoryStructure] = Field(default_factory=list)
    files: list[FileStructure] = Field(default_factory=list)


class SearchMatch(BaseModel):
    file_path: str = Field(alias="filePath")
    id: str
    kind: str
    heading: str | None = None
    definition_keys: list[str] = Field(default_factory=list, alias="definitionKeys")
    match_reasons: list[str] = Field(default_factory=list, alias="matchReasons")
    snippet: str | None = None

    model_config = {"populate_by_name": True}


class SearchReport(BaseModel):
    query: str
    total_matches: int = Field(alias="totalMatches")
    matches: list[SearchMatch] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class MlgClient:
    """Client for executing `mlg` commands on a Mathlingua collection."""

    def __init__(self, mlg_bin: Path | str, repo_path: Path | str):
        self.mlg_bin = Path(mlg_bin).resolve()
        self.repo_path = Path(repo_path).resolve()

    def _run_cmd(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [str(self.mlg_bin)] + args
        return subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=False,
        )

    def check(self, paths: list[str] | None = None) -> CheckReport:
        """Run `mlg check --json` optionally filtering to specific paths."""
        args = ["check", "--json"]
        if paths:
            args.extend(paths)

        proc = self._run_cmd(args)
        if proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                return CheckReport.model_validate(data)
            except Exception:
                pass

        # Fallback if json parse fails
        diagnostics = []
        if proc.stderr:
            for line in proc.stderr.strip().splitlines():
                if line.strip():
                    diagnostics.append(Diagnostic(message=line.strip()))
        return CheckReport(
            successful=(proc.returncode == 0),
            issue_count=len(diagnostics),
            files_checked=0,
            diagnostics=diagnostics,
            raw_output=proc.stdout + proc.stderr,
        )

    def structure(self) -> CollectionStructure:
        """Run `mlg structure --json` to get the repo layout and items."""
        proc = self._run_cmd(["structure", "--json"])
        if proc.returncode != 0:
            raise RuntimeError(f"`mlg structure` failed: {proc.stderr or proc.stdout}")
        data = json.loads(proc.stdout)
        return CollectionStructure.model_validate(data)

    def search(self, query: str) -> SearchReport:
        """Run `mlg search <query> --json` across definitions and items."""
        proc = self._run_cmd(["search", query, "--json"])
        if proc.returncode != 0:
            raise RuntimeError(f"`mlg search` failed: {proc.stderr or proc.stdout}")
        data = json.loads(proc.stdout)
        return SearchReport.model_validate(data)

    def format(self) -> bool:
        """Run `mlg format` to reformat source files."""
        proc = self._run_cmd(["format"])
        return proc.returncode == 0
