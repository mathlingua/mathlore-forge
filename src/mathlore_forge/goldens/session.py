"""Session management for golden test runs with increasing numeric IDs."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from mathlore_forge.goldens.sandbox import Sandbox


class SessionMeta(BaseModel):
    """Metadata recorded for each test run session."""

    session_id: str = Field(description="Formatted identifier, e.g. 'session-1'.")
    session_number: int = Field(description="Increasing sequential integer.")
    test_id: str = Field(description="Identifier of the test case executed.")
    test_name: str = Field(description="Human readable name of the test.")
    status: str = Field(default="RUNNING", description="PASSED, FAILED, ERROR, or RUNNING.")
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: str | None = None
    duration_seconds: float = 0.0
    session_dir: str = Field(description="Absolute path to the session directory.")
    workspace_dir: str = Field(description="Absolute path to the agent workspace.")
    auto_cleaned: bool = False
    error_message: str | None = None
    created_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)


class Session:
    """Represents an active or completed test run session."""

    def __init__(self, session_dir: Path, meta: SessionMeta):
        self.session_dir = session_dir
        self.meta = meta
        self.sandbox = Sandbox(session_dir)

    def save_meta(self) -> None:
        """Persists the session metadata to meta.json."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        meta_file = self.session_dir / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(self.meta.model_dump(mode="json"), f, indent=2, default=str)

    def finish(
        self,
        status: str,
        duration_seconds: float,
        error_message: str | None = None,
        created_files: list[str] | None = None,
        modified_files: list[str] | None = None,
        deleted_files: list[str] | None = None,
    ) -> None:
        """Marks the session as completed and updates metadata."""
        self.meta.status = status
        self.meta.ended_at = datetime.now(timezone.utc).isoformat()
        self.meta.duration_seconds = duration_seconds
        self.meta.error_message = error_message
        if created_files is not None:
            self.meta.created_files = created_files
        if modified_files is not None:
            self.meta.modified_files = modified_files
        if deleted_files is not None:
            self.meta.deleted_files = deleted_files
        self.save_meta()


class SessionManager:
    """Manages the lifecycle and discovery of golden test run sessions."""

    def __init__(self, runs_dir: Path | str = "./runs"):
        self.runs_dir = Path(runs_dir).resolve()
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.counter_file = self.runs_dir / ".session_counter"

    def _get_next_session_number(self) -> int:
        """Determines the next sequential session number."""
        current_max = 0

        # 1. Read from counter file if present
        if self.counter_file.is_file():
            try:
                current_max = int(self.counter_file.read_text(encoding="utf-8").strip())
            except Exception:
                current_max = 0

        # 2. Scan existing directories in case counter was removed or diverged
        session_pattern = re.compile(r"^session-(\d+)$")
        if self.runs_dir.is_dir():
            for item in self.runs_dir.iterdir():
                if item.is_dir():
                    m = session_pattern.match(item.name)
                    if m:
                        num = int(m.group(1))
                        if num > current_max:
                            current_max = num

        next_number = current_max + 1
        self.counter_file.write_text(str(next_number), encoding="utf-8")
        return next_number

    def create_session(self, test_id: str, test_name: str) -> Session:
        """Allocates a new session with an increasing numeric ID."""
        session_num = self._get_next_session_number()
        session_id = f"session-{session_num}"
        session_dir = self.runs_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        meta = SessionMeta(
            session_id=session_id,
            session_number=session_num,
            test_id=test_id,
            test_name=test_name,
            session_dir=str(session_dir.resolve()),
            workspace_dir=str((session_dir / "workspace").resolve()),
        )

        session = Session(session_dir, meta)
        session.save_meta()
        return session

    def list_sessions(self, status_filter: str | None = None) -> list[SessionMeta]:
        """Lists all prior sessions, sorted by session number ascending."""
        sessions: list[SessionMeta] = []
        if not self.runs_dir.is_dir():
            return sessions

        for item in self.runs_dir.iterdir():
            if item.is_dir():
                meta_file = item / "meta.json"
                if meta_file.is_file():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        meta = SessionMeta.model_validate(data)
                        if status_filter and meta.status.upper() != status_filter.upper():
                            continue
                        sessions.append(meta)
                    except Exception:
                        continue

        sessions.sort(key=lambda s: s.session_number)
        return sessions

    def get_session(self, session_id: str) -> SessionMeta | None:
        """Retrieves metadata for a specific session ID."""
        clean_id = session_id.strip()
        if not clean_id.startswith("session-"):
            clean_id = f"session-{clean_id}"

        session_dir = self.runs_dir / clean_id
        meta_file = session_dir / "meta.json"
        if meta_file.is_file():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    return SessionMeta.model_validate(json.load(f))
            except Exception:
                return None
        return None

    def get_session_dir(self, session_id: str) -> Path | None:
        """Returns the directory of a session if it exists."""
        clean_id = session_id.strip()
        if not clean_id.startswith("session-"):
            clean_id = f"session-{clean_id}"
        d = self.runs_dir / clean_id
        return d if d.is_dir() else None

    def clean_session(self, session_id: str) -> bool:
        """Deletes a specific session directory."""
        d = self.get_session_dir(session_id)
        if d and d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            return True
        return False

    def clean_all(
        self,
        status_filter: str | None = None,
        keep_failed: bool = False,
    ) -> int:
        """Deletes past session directories matching criteria. Returns count of deleted runs."""
        cleaned_count = 0
        sessions = self.list_sessions()
        for s in sessions:
            if keep_failed and s.status.upper() in ("FAILED", "ERROR"):
                continue
            if status_filter and s.status.upper() != status_filter.upper():
                continue

            target_dir = Path(s.session_dir)
            if target_dir.is_dir():
                shutil.rmtree(target_dir, ignore_errors=True)
                cleaned_count += 1

        return cleaned_count
