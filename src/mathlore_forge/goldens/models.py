"""Data models and schemas for Mathlingua golden tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

DEFAULT_MLG_JSON = """{
  "name": "MathloreTest",
  "version": "0",
  "margin": 80,
  "formatOnCheck": true,
  "outputDir": "docs"
}
"""


class ScaffoldConfig(BaseModel):
    """Configuration for setting up the initial workspace state before an agent runs."""

    from_dir: str | None = Field(
        default=None,
        description="Relative path to directory containing initial files (e.g. 'scaffold/').",
    )
    files: dict[str, str] = Field(
        default_factory=dict,
        description="Inline map of relative file path to file content.",
    )
    include_default_mlg_json: bool = Field(
        default=True,
        description="Whether to automatically add a valid mlg.json if one is not present.",
    )

    def materialize(self, target_dir: Path, base_dir: Path | None = None) -> None:
        """Copies or writes all scaffolding files into the target directory."""
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy files from from_dir if specified
        if self.from_dir:
            source_dir = Path(self.from_dir)
            if not source_dir.is_absolute() and base_dir:
                source_dir = (base_dir / source_dir).resolve()

            if source_dir.is_dir():
                for item in source_dir.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(source_dir)
                        dest = target_dir / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(item.read_bytes())

        # 2. Write inline files (may override copied files)
        for rel_path, content in self.files.items():
            dest = target_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        # 3. Add default mlg.json if missing and requested
        mlg_json_path = target_dir / "mlg.json"
        if self.include_default_mlg_json and not mlg_json_path.exists():
            mlg_json_path.write_text(DEFAULT_MLG_JSON, encoding="utf-8")


class FileExpectation(BaseModel):
    """Expectations for a specific file in the workspace after the agent completes."""

    path: str = Field(description="Relative path of the file in the workspace.")
    should_exist: bool = Field(default=True, description="Whether the file should exist.")
    contains: list[str] = Field(
        default_factory=list, description="Substrings that must be present in the file."
    )
    not_contains: list[str] = Field(
        default_factory=list, description="Substrings that must NOT be present in the file."
    )
    matches_regex: list[str] = Field(
        default_factory=list, description="Regex patterns that must match in the file content."
    )
    not_matches_regex: list[str] = Field(
        default_factory=list, description="Regex patterns that must NOT match in the file content."
    )
    exact_content: str | None = Field(
        default=None, description="Exact expected content of the file (stripped)."
    )
    min_lines: int | None = Field(default=None, description="Minimum number of lines.")
    max_lines: int | None = Field(default=None, description="Maximum number of lines.")


class CompilerExpectation(BaseModel):
    """Expectations regarding the `mlg check` compiler results."""

    enabled: bool = Field(
        default=True, description="Whether compiler check is performed."
    )
    clean: bool = Field(
        default=True, description="Whether mlg check must complete with 0 errors/diagnostics."
    )
    max_errors: int | None = Field(
        default=None, description="Maximum number of acceptable compiler errors."
    )
    paths: list[str] | None = Field(
        default=None, description="Specific file paths to check. If None, checks entire collection."
    )


class ToolCallExpectation(BaseModel):
    """Expectation for tool invocations in the agent's trajectory."""

    name: str = Field(description="Name of the tool (e.g. 'insert_item_after', 'mlg_check').")
    must_call: bool = Field(default=True, description="Whether this tool must be called at least once.")
    min_calls: int | None = Field(default=None, description="Minimum number of calls required.")
    max_calls: int | None = Field(default=None, description="Maximum number of calls allowed.")
    with_args: dict[str, Any] | None = Field(
        default=None,
        description="Key/value pairs that must appear in at least one call's arguments.",
    )


class SubagentExpectation(BaseModel):
    """Expectation for sub-agent invocations in the agent's trajectory."""

    name: str = Field(description="Name or role of the subagent.")
    must_run: bool = Field(default=True, description="Whether this subagent must be invoked.")
    min_runs: int | None = Field(default=None, description="Minimum number of times run.")
    max_runs: int | None = Field(default=None, description="Maximum number of times run.")


class TrajectoryExpectations(BaseModel):
    """Expectations for the agent's entire trajectory and behavior."""

    tools: list[ToolCallExpectation] = Field(
        default_factory=list, description="Specific tool call expectations."
    )
    subagents: list[SubagentExpectation] = Field(
        default_factory=list, description="Subagent expectations."
    )
    forbidden_tools: list[str] = Field(
        default_factory=list, description="Tool names that must never be called."
    )
    forbidden_subagents: list[str] = Field(
        default_factory=list, description="Subagent names that must never be invoked."
    )
    min_total_tool_calls: int | None = Field(
        default=None, description="Minimum total tool calls across all tools."
    )
    max_total_tool_calls: int | None = Field(
        default=None, description="Maximum total tool calls across all tools."
    )


class Expectations(BaseModel):
    """Aggregated verification expectations for a golden test."""

    compiler: CompilerExpectation = Field(default_factory=CompilerExpectation)
    files_created: list[str] = Field(
        default_factory=list, description="Files that must be newly created by the agent."
    )
    files_modified: list[str] = Field(
        default_factory=list, description="Existing files that must be modified by the agent."
    )
    files_deleted: list[str] = Field(
        default_factory=list, description="Files that must be deleted by the agent."
    )
    file_assertions: list[FileExpectation] = Field(
        default_factory=list, description="Detailed content assertions on specific files."
    )
    trajectory: TrajectoryExpectations = Field(default_factory=TrajectoryExpectations)


class GoldenTestCase(BaseModel):
    """Specification of a golden test case for a Mathlingua agent."""

    id: str = Field(description="Unique identifier for the test case (e.g. '01_add_group_definition').")
    name: str = Field(description="Short human-readable title.")
    description: str = Field(default="", description="Detailed explanation of what the test tests.")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization/filtering.")
    prompt: str = Field(description="The prompt/instruction given to the agent.")
    scaffold: ScaffoldConfig = Field(default_factory=ScaffoldConfig)
    expectations: Expectations = Field(default_factory=Expectations)
    timeout_seconds: float = Field(
        default=180.0, description="Maximum execution timeout in seconds."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary additional metadata."
    )
    base_dir: Path | None = Field(
        default=None,
        exclude=True,
        description="Filesystem location where this test was loaded from.",
    )
