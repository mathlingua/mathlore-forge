"""Antigravity agent lifecycle hooks for telemetry, trajectory recording, and cancellation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Callable
from google.antigravity import types
from google.antigravity.hooks import hooks

from mathlore_forge.goldens.trajectory import Trajectory


class TrajectoryTelemetryHooks:
    """Manages telemetry, trajectory recording, and cancellation for an Antigravity agent session."""

    def __init__(
        self,
        trajectory: Trajectory | None = None,
        event_callback: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.trajectory = trajectory or Trajectory()
        self.event_callback = event_callback
        self._current_tool_start_times: dict[str, float] = {}
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Flags that the turn should be cancelled."""
        self._cancel_requested = True

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        if self.event_callback:
            try:
                res = self.event_callback(payload)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass

    def get_hooks(self) -> list[Any]:
        """Returns the list of hook functions to register on LocalAgentConfig."""

        @hooks.on_session_start
        async def on_session_start() -> None:
            self._emit("session_start", {})

        @hooks.on_session_end
        async def on_session_end() -> None:
            self._emit("session_end", {})

        @hooks.pre_turn
        async def pre_turn(prompt: str) -> types.HookResult:
            if self._cancel_requested:
                return types.HookResult(allow=False, reason="Run cancelled by user.")
            self._emit("turn_start", {"prompt": prompt})
            return types.HookResult(allow=True)

        @hooks.post_turn
        async def post_turn(response: str) -> None:
            self._emit("turn_end", {"response": response})

        @hooks.pre_tool_call_decide
        async def pre_tool(data: types.ToolCall) -> types.HookResult:
            if self._cancel_requested:
                return types.HookResult(allow=False, reason="Run cancelled by user.")
            call_id = getattr(data, "id", None) or f"call_{time.time_ns()}"
            self._current_tool_start_times[call_id] = time.perf_counter()
            self._emit("tool_start", {"tool": data.name, "args": getattr(data, "args", {})})
            return types.HookResult(allow=True)

        @hooks.post_tool_call
        async def post_tool(data: Any) -> None:
            tool_name = getattr(data, "name", "tool")
            args = getattr(data, "args", {})
            result = getattr(data, "result", data)
            call_id = getattr(data, "id", "call")
            start = self._current_tool_start_times.pop(call_id, time.perf_counter())
            duration_ms = (time.perf_counter() - start) * 1000

            self.trajectory.record_tool_call(
                name=tool_name,
                args=args,
                result=result,
                duration_ms=duration_ms,
            )
            self._emit("tool_end", {"tool": tool_name, "duration_ms": duration_ms})

        @hooks.on_tool_error
        async def on_tool_error(error: Exception) -> None:
            self._emit("tool_error", {"error": str(error)})

        return [
            on_session_start,
            on_session_end,
            pre_turn,
            post_turn,
            pre_tool,
            post_tool,
            on_tool_error,
        ]
