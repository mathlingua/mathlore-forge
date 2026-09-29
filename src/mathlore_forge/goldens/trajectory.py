"""Trajectory recording and formatting for agent runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


def _current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


class ToolCallRecord(BaseModel):
    """Log record of a single tool execution."""

    id: str = Field(description="Unique call identifier.")
    name: str = Field(description="Tool name.")
    args: dict[str, Any] = Field(default_factory=dict, description="Input arguments.")
    result: Any = Field(default=None, description="Result returned by tool.")
    error: str | None = Field(default=None, description="Error message if tool raised exception.")
    started_at: str = Field(default_factory=_current_iso_time)
    ended_at: str = Field(default_factory=_current_iso_time)
    duration_ms: float = Field(default=0.0)


class SubagentCallRecord(BaseModel):
    """Log record of a subagent invocation."""

    id: str = Field(description="Unique subagent run identifier.")
    name: str = Field(description="Subagent name or type.")
    prompt: str = Field(default="", description="Prompt or task passed to subagent.")
    args: dict[str, Any] = Field(default_factory=dict, description="Additional arguments.")
    result: Any = Field(default=None, description="Output returned by subagent.")
    started_at: str = Field(default_factory=_current_iso_time)
    ended_at: str = Field(default_factory=_current_iso_time)
    duration_ms: float = Field(default=0.0)


class TurnRecord(BaseModel):
    """Log record of an interaction turn."""

    turn_index: int = 0
    user_prompt: str = ""
    thoughts: list[str] = Field(default_factory=list)
    assistant_response: str = ""
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    subagent_calls: list[SubagentCallRecord] = Field(default_factory=list)


class Trajectory(BaseModel):
    """Complete trajectory recording of an agent execution."""

    turns: list[TurnRecord] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    subagent_calls: list[SubagentCallRecord] = Field(default_factory=list)
    thoughts: list[str] = Field(default_factory=list)
    final_output: str = ""
    total_duration_seconds: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def record_tool_call(
        self,
        name: str,
        args: dict[str, Any] | None = None,
        result: Any = None,
        error: str | None = None,
        duration_ms: float = 0.0,
        call_id: str | None = None,
    ) -> ToolCallRecord:
        """Records a completed tool execution."""
        record = ToolCallRecord(
            id=call_id or f"call-{len(self.tool_calls) + 1}",
            name=name,
            args=args or {},
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        self.tool_calls.append(record)
        return record

    def record_subagent_call(
        self,
        name: str,
        prompt: str = "",
        args: dict[str, Any] | None = None,
        result: Any = None,
        duration_ms: float = 0.0,
        subagent_id: str | None = None,
    ) -> SubagentCallRecord:
        """Records a subagent invocation."""
        record = SubagentCallRecord(
            id=subagent_id or f"subagent-{len(self.subagent_calls) + 1}",
            name=name,
            prompt=prompt,
            args=args or {},
            result=result,
            duration_ms=duration_ms,
        )
        self.subagent_calls.append(record)
        return record

    def record_thought(self, thought: str) -> None:
        """Records an intermediate thought or reasoning step."""
        cleaned = thought.strip()
        if cleaned:
            self.thoughts.append(cleaned)

    # -------------------------------------------------------------------------
    # Query Helpers
    # -------------------------------------------------------------------------

    def get_tool_names(self) -> list[str]:
        return [c.name for c in self.tool_calls]

    def has_tool_call(self, name: str) -> bool:
        return any(c.name == name for c in self.tool_calls)

    def get_tool_calls(self, name: str) -> list[ToolCallRecord]:
        return [c for c in self.tool_calls if c.name == name]

    def count_tool_calls(self, name: str) -> int:
        return sum(1 for c in self.tool_calls if c.name == name)

    def get_subagent_names(self) -> list[str]:
        return [s.name for s in self.subagent_calls]

    def has_subagent_run(self, name: str) -> bool:
        return any(s.name == name for s in self.subagent_calls)

    def count_subagent_runs(self, name: str) -> int:
        return sum(1 for s in self.subagent_calls if s.name == name)

    # -------------------------------------------------------------------------
    # Serialization and Formatting
    # -------------------------------------------------------------------------

    def save_json(self, path: Path | str) -> None:
        """Saves the trajectory as a structured JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)

    def to_markdown(self) -> str:
        """Generates a human-readable markdown transcript of the trajectory."""
        lines: list[str] = [
            "# Agent Execution Trajectory",
            "",
            f"- **Total Duration**: {self.total_duration_seconds:.2f}s",
            f"- **Total Tool Calls**: {len(self.tool_calls)}",
            f"- **Subagents Run**: {len(self.subagent_calls)}",
            "",
        ]

        if self.token_usage:
            lines.append("## Token Usage")
            for k, v in self.token_usage.items():
                lines.append(f"- **{k}**: {v:,}")
            lines.append("")

        if self.thoughts:
            lines.append("## Reasoning Thoughts")
            for i, thought in enumerate(self.thoughts, start=1):
                lines.append(f"> **Thought {i}**:")
                for sub in thought.splitlines():
                    lines.append(f"> {sub}")
                lines.append("")

        if self.tool_calls:
            lines.append("## Tool Calls")
            for i, call in enumerate(self.tool_calls, start=1):
                status_icon = "❌" if call.error else "✅"
                lines.append(f"### {status_icon} Call {i}: `{call.name}` ({call.duration_ms:.1f}ms)")
                if call.args:
                    lines.append("```json")
                    lines.append(json.dumps(call.args, indent=2, default=str))
                    lines.append("```")
                if call.error:
                    lines.append(f"**Error**: `{call.error}`")
                elif call.result is not None:
                    if isinstance(call.result, (dict, list)):
                        lines.append(f"**Result**:\n```json\n{json.dumps(call.result, indent=2, default=str)}\n```")
                    else:
                        lines.append(f"**Result**:\n```text\n{call.result}\n```")
                lines.append("")

        if self.subagent_calls:
            lines.append("## Subagents")
            for i, sub in enumerate(self.subagent_calls, start=1):
                lines.append(f"### Subagent {i}: `{sub.name}` ({sub.duration_ms:.1f}ms)")
                if sub.prompt:
                    lines.append(f"**Prompt**: {sub.prompt}")
                if sub.result is not None:
                    if isinstance(sub.result, (dict, list)):
                        lines.append(f"**Output**:\n```json\n{json.dumps(sub.result, indent=2, default=str)}\n```")
                    else:
                        lines.append(f"**Output**:\n```text\n{sub.result}\n```")
                lines.append("")

        if self.final_output:
            lines.append("## Final Output")
            lines.append(self.final_output)
            lines.append("")

        return "\n".join(lines)

    def save_markdown(self, path: Path | str) -> None:
        """Saves a human-readable markdown transcript."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_markdown(), encoding="utf-8")
