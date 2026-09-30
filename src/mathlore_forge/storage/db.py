"""SQLAlchemy database models and session management for Mathlore Forge."""

from __future__ import annotations

from datetime import datetime, timezone
import enum
import json
from pathlib import Path
from typing import Any, Generator, Sequence

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    desc,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


class RunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    ADDRESSING_COMMENTS = "ADDRESSING_COMMENTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunType(str, enum.Enum):
    INITIAL_AUTHORING = "INITIAL_AUTHORING"
    ADDRESS_COMMENTS = "ADDRESS_COMMENTS"
    FLYWHEEL_IMPROVEMENT = "FLYWHEEL_IMPROVEMENT"
    CURATION_PLANNING = "CURATION_PLANNING"
    PLAN_EXECUTION = "PLAN_EXECUTION"
    MANUAL = "MANUAL"


class IssueRecord(Base):
    """Represents a GitHub issue tracked by Mathlore Forge."""

    __tablename__ = "forge_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo: Mapped[str] = mapped_column(String(255), index=True, default="mathlingua/mathlore")
    issue_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(255), default="DominicKramer")
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")
    plan_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_status: Mapped[str | None] = mapped_column(String(50), default=None)  # PLANNING, AWAITING_APPROVAL, APPROVED, EXECUTING, COMPLETED
    plan_revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    pull_requests: Mapped[list[PullRequestRecord]] = relationship("PullRequestRecord", back_populates="issue")
    runs: Mapped[list[AgentRunRecord]] = relationship("AgentRunRecord", back_populates="issue")


class PullRequestRecord(Base):
    """Represents a GitHub Pull Request created or managed by Forge."""

    __tablename__ = "forge_pull_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo: Mapped[str] = mapped_column(String(255), index=True)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    branch_name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    issue_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("forge_issues.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")  # OPEN, AWAITING_REVIEW, APPROVED, MERGED, CLOSED
    pr_url: Mapped[str] = mapped_column(String(512), default="")
    review_rounds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    issue: Mapped[IssueRecord | None] = relationship("IssueRecord", back_populates="pull_requests")
    runs: Mapped[list[AgentRunRecord]] = relationship("AgentRunRecord", back_populates="pull_request")
    comments: Mapped[list[ReviewCommentRecord]] = relationship("ReviewCommentRecord", back_populates="pull_request")


class AgentRunRecord(Base):
    """Represents a single execution run of an Antigravity agent."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # run_uuid
    run_type: Mapped[RunType] = mapped_column(Enum(RunType), default=RunType.INITIAL_AUTHORING)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.QUEUED, index=True)
    repo: Mapped[str] = mapped_column(String(255), default="mathlingua/mathlore")
    issue_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("forge_issues.id"), nullable=True)
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("forge_pull_requests.id"), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    prompt: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_patch: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token and performance telemetry
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    candidates_tokens: Mapped[int] = mapped_column(Integer, default=0)
    thoughts_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    issue: Mapped[IssueRecord | None] = relationship("IssueRecord", back_populates="runs")
    pull_request: Mapped[PullRequestRecord | None] = relationship("PullRequestRecord", back_populates="runs")
    trajectory: Mapped[TrajectoryRecord | None] = relationship("TrajectoryRecord", back_populates="run", uselist=False)


class TrajectoryRecord(Base):
    """Stores full execution trajectory JSON for deep inspection."""

    __tablename__ = "trajectories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.id"), unique=True, index=True)
    trajectory_json: Mapped[str] = mapped_column(Text, default="{}")
    markdown_summary: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    run: Mapped[AgentRunRecord] = relationship("AgentRunRecord", back_populates="trajectory")


class ReviewCommentRecord(Base):
    """Stores review comments left by Dominic Kramer and their resolution status."""

    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pr_id: Mapped[int] = mapped_column(Integer, ForeignKey("forge_pull_requests.id"), index=True)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    comment_github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    author: Mapped[str] = mapped_column(String(255), default="DominicKramer")
    body: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diff_hunk: Mapped[str | None] = mapped_column(Text, nullable=True)
    addressed: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    pull_request: Mapped[PullRequestRecord] = relationship("PullRequestRecord", back_populates="comments")


class Database:
    """Database connection and session factory manager."""

    def __init__(self, db_url: str = "sqlite:///mathlore_forge.sqlite"):
        self.db_url = db_url
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        pool_kwargs = {}
        if db_url == "sqlite:///:memory:":
            from sqlalchemy.pool import StaticPool
            pool_kwargs = {"poolclass": StaticPool}
        self.engine = create_engine(db_url, connect_args=connect_args, **pool_kwargs)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        """Creates all database tables defined in Base."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Returns a new database session."""
        return self.session_factory()


_GLOBAL_DB: Database | None = None


def init_db(db_url: str | None = None) -> Database:
    """Initializes the global database instance and tables."""
    global _GLOBAL_DB
    url = db_url or "sqlite:///mathlore_forge.sqlite"
    _GLOBAL_DB = Database(url)
    _GLOBAL_DB.create_tables()
    return _GLOBAL_DB


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    global _GLOBAL_DB
    if _GLOBAL_DB is None:
        init_db()
    assert _GLOBAL_DB is not None
    session = _GLOBAL_DB.get_session()
    try:
        yield session
    finally:
        session.close()
