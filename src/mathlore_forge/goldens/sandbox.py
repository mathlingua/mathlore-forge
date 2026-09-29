"""Sandbox management and filesystem diffing for test runs."""

from __future__ import annotations

import difflib
import filecmp
import shutil
from dataclasses import dataclass
from pathlib import Path

from mathlore_forge.goldens.models import ScaffoldConfig


@dataclass
class FileDiffSummary:
    """Summary of changes between initial scaffold and final workspace state."""

    created_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    unified_diff: str


class Sandbox:
    """Manages an isolated directory environment for an agent to run."""

    def __init__(self, root_dir: Path | str):
        self.root_dir = Path(root_dir).resolve()
        self.workspace_dir = self.root_dir / "workspace"
        self.initial_dir = self.root_dir / "initial_scaffold"

    def setup(self, scaffold: ScaffoldConfig, base_dir: Path | None = None) -> Path:
        """Sets up the workspace with the specified scaffold content."""
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir)

        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.initial_dir.mkdir(parents=True, exist_ok=True)

        # 1. Materialize scaffold into workspace
        scaffold.materialize(self.workspace_dir, base_dir=base_dir)

        # 2. Make an exact copy in initial_dir to preserve the baseline
        shutil.copytree(self.workspace_dir, self.initial_dir, dirs_exist_ok=True)

        return self.workspace_dir

    def compute_changes(self) -> FileDiffSummary:
        """Compares workspace_dir against initial_dir and returns diffs."""
        initial_files: dict[str, Path] = {}
        for p in self.initial_dir.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(self.initial_dir))
                initial_files[rel] = p

        current_files: dict[str, Path] = {}
        for p in self.workspace_dir.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(self.workspace_dir))
                current_files[rel] = p

        created: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        diff_chunks: list[str] = []

        # Find created and modified files
        for rel, cur_path in sorted(current_files.items()):
            if rel not in initial_files:
                created.append(rel)
                cur_text = cur_path.read_text(encoding="utf-8", errors="replace")
                diff = difflib.unified_diff(
                    [],
                    cur_text.splitlines(keepends=True),
                    fromfile="/dev/null",
                    tofile=f"b/{rel}",
                )
                diff_chunks.extend(diff)
            else:
                init_path = initial_files[rel]
                if not filecmp.cmp(cur_path, init_path, shallow=False):
                    modified.append(rel)
                    init_text = init_path.read_text(encoding="utf-8", errors="replace")
                    cur_text = cur_path.read_text(encoding="utf-8", errors="replace")
                    diff = difflib.unified_diff(
                        init_text.splitlines(keepends=True),
                        cur_text.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                    diff_chunks.extend(diff)

        # Find deleted files
        for rel, init_path in sorted(initial_files.items()):
            if rel not in current_files:
                deleted.append(rel)
                init_text = init_path.read_text(encoding="utf-8", errors="replace")
                diff = difflib.unified_diff(
                    init_text.splitlines(keepends=True),
                    [],
                    fromfile=f"a/{rel}",
                    tofile="/dev/null",
                )
                diff_chunks.extend(diff)

        unified = "".join(diff_chunks)
        return FileDiffSummary(
            created_files=created,
            modified_files=modified,
            deleted_files=deleted,
            unified_diff=unified,
        )

    def cleanup(self) -> None:
        """Deletes the sandbox root directory."""
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir, ignore_errors=True)
