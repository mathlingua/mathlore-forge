"""Git workspace and repository tools for Mathlore Forge."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence


class GitCommandError(RuntimeError):
    """Raised when a git command returns a non-zero exit code."""
    pass


class GitWorkspace:
    """Manages an isolated git workspace for agent authoring and patching."""

    def __init__(self, workspace_dir: Path | str, repo_url: str | None = None):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.repo_url = repo_url

    def run_git(self, args: Sequence[str], check: bool = True) -> str:
        """Executes a git command inside the workspace directory."""
        cmd = ["git", "-C", str(self.workspace_dir), *args]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if check and proc.returncode != 0:
            raise GitCommandError(
                f"Git command failed: {' '.join(cmd)}\n"
                f"Exit code: {proc.returncode}\n"
                f"STDOUT: {proc.stdout}\n"
                f"STDERR: {proc.stderr}"
            )
        return proc.stdout.strip()

    @classmethod
    def clone(
        cls,
        repo_url: str,
        target_dir: Path | str,
        branch: str | None = None,
        depth: int | None = None,
    ) -> GitWorkspace:
        """Clones a remote repository into a target directory."""
        target_path = Path(target_dir).resolve()
        if target_path.exists():
            shutil.rmtree(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = ["git", "clone"]
        if depth:
            cmd.extend(["--depth", str(depth)])
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([repo_url, str(target_path)])

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitCommandError(f"Failed to clone {repo_url}: {proc.stderr}")

        return cls(workspace_dir=target_path, repo_url=repo_url)

    @classmethod
    def init_from_existing(cls, existing_dir: Path | str, target_dir: Path | str) -> GitWorkspace:
        """Copies an existing repository into a clean isolated directory for safe agent modification."""
        existing_path = Path(existing_dir).resolve()
        target_path = Path(target_dir).resolve()
        if target_path.exists():
            shutil.rmtree(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(existing_path, target_path, symlinks=True)
        return cls(workspace_dir=target_path)

    def checkout_branch(self, branch_name: str, create: bool = False, start_point: str | None = None) -> str:
        """Checks out a branch, optionally creating it."""
        args = ["checkout"]
        if create:
            args.extend(["-B", branch_name])
            if start_point:
                args.append(start_point)
        else:
            args.append(branch_name)
        return self.run_git(args)

    def current_branch(self) -> str:
        """Returns the current branch name."""
        return self.run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    def status(self) -> str:
        """Returns git status in short porcelain format."""
        return self.run_git(["status", "--porcelain"])

    def has_changes(self) -> bool:
        """Checks whether the workspace has modified, added, or deleted files."""
        return bool(self.status())

    def get_diff(self, base_ref: str | None = None) -> str:
        """Returns git diff patch of uncommitted or committed changes relative to base_ref."""
        if base_ref:
            return self.run_git(["diff", base_ref])
        return self.run_git(["diff", "HEAD"])

    def add_all(self) -> str:
        """Stages all changes."""
        return self.run_git(["add", "-A"])

    def commit(
        self,
        message: str,
        author_name: str = "Mathlore Forge Bot",
        author_email: str = "forge@mathlore.org",
    ) -> str:
        """Commits staged changes."""
        self.add_all()
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = author_email
        env["GIT_COMMITTER_NAME"] = author_name
        env["GIT_COMMITTER_EMAIL"] = author_email

        cmd = ["git", "-C", str(self.workspace_dir), "commit", "-m", message]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc.returncode != 0 and "nothing to commit" not in proc.stdout:
            raise GitCommandError(f"Commit failed: {proc.stderr or proc.stdout}")
        return proc.stdout.strip()

    def push(self, remote: str = "origin", branch: str | None = None, force: bool = False) -> str:
        """Pushes current branch to remote."""
        target_branch = branch or self.current_branch()
        args = ["push", remote, target_branch]
        if force:
            args.append("--force")
        return self.run_git(args)
