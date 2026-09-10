"""Data models and schemas for the Mathlore metadata store."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TodoStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED_GAP = "BLOCKED_GAP"
    FAILED = "FAILED"


class PhaseType(str, Enum):
    HIGH_LEVEL_PLAN = "high_level_plan"
    DETAILED_PLAN = "detailed_plan"
    AUTHORING = "authoring"


# SQLAlchemy ORM Models
class SectionModel(Base):
    __tablename__ = "sections"

    path = Column(String(255), primary_key=True)
    title = Column(String(255), nullable=True)
    purpose = Column(Text, nullable=True)
    what_covered = Column(Text, nullable=True)
    prerequisites = Column(Text, nullable=True)
    is_directory = Column(Boolean, default=False)
    defined_commands = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TodoItemModel(Base):
    __tablename__ = "todo_items"

    id = Column(String(128), primary_key=True)
    iteration_id = Column(String(128), nullable=False)
    section_path = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    kind = Column(String(64), nullable=False)
    purpose = Column(Text, nullable=True)
    what_to_cover = Column(Text, nullable=True)
    citations = Column(Text, nullable=True)
    status = Column(String(32), default=TodoStatus.TODO.value)
    source_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FeedbackModel(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    iteration_id = Column(String(128), nullable=False)
    phase = Column(String(64), nullable=False)
    user_feedback = Column(Text, nullable=False)
    agent_reflection = Column(Text, nullable=True)
    learned_rule = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GapModel(Base):
    __tablename__ = "gaps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False)
    concept = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    attempted_representation = Column(Text, nullable=True)
    user_guidance = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GoldenModel(Base):
    __tablename__ = "goldens"

    id = Column(String(128), primary_key=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    plan_summary = Column(Text, nullable=False)
    expected_symbols = Column(Text, nullable=True)
    expected_source = Column(Text, nullable=True)
    citations = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Pydantic Schemas for Application Logic
class SectionRecord(BaseModel):
    path: str
    title: str | None = None
    purpose: str | None = None
    what_covered: str | None = None
    prerequisites: str | None = None
    is_directory: bool = False
    defined_commands: list[str] = Field(default_factory=list)
    order_index: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TodoItemRecord(BaseModel):
    id: str
    iteration_id: str
    section_path: str
    title: str
    kind: str
    purpose: str | None = None
    what_to_cover: str | None = None
    citations: list[dict[str, Any]] | str | None = None
    status: TodoStatus = TodoStatus.TODO
    source_code: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackRecord(BaseModel):
    id: int | None = None
    iteration_id: str
    phase: PhaseType
    user_feedback: str
    agent_reflection: str | None = None
    learned_rule: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GapRecord(BaseModel):
    id: int | None = None
    item_id: str
    concept: str
    description: str
    attempted_representation: str | None = None
    user_guidance: str | None = None
    resolved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoldenRecord(BaseModel):
    id: str
    name: str
    prompt: str
    plan_summary: str
    expected_symbols: list[str] = Field(default_factory=list)
    expected_source: str | None = None
    citations: list[str] = Field(default_factory=list)
    file_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
