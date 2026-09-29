"""Agent execution runner and harness for golden tests."""

from __future__ import annotations

import asyncio
import functools
import inspect
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from mathlore_forge.agents.mathlingua_agent import create_mathlingua_agent
from mathlore_forge.goldens.evaluator import Evaluator, EvaluationReport
from mathlore_forge.goldens.models import GoldenTestCase
from mathlore_forge.goldens.sandbox import FileDiffSummary
from mathlore_forge.goldens.session import Session, SessionManager
from mathlore_forge.goldens.trajectory import Trajectory
from mathlore_forge.tools.mathlingua_tools import MathlinguaToolkit


class AgentAdapter(ABC):
    """Abstract interface for running an agent inside a sandboxed workspace."""

    @abstractmethod
    async def run(
        self,
        prompt: str,
        workspace_dir: Path,
        trajectory: Trajectory,
        timeout_seconds: float = 180.0,
    ) -> str:
        """Runs the agent on the given prompt within workspace_dir, recording events into trajectory."""
        pass


def _wrap_tool_for_trajectory(tool_fn: Callable, trajectory: Trajectory) -> Callable:
    """Wraps a tool function to intercept calls and record them to Trajectory."""
    tool_name = getattr(tool_fn, "__name__", str(tool_fn))

    if inspect.iscoroutinefunction(tool_fn):

        @functools.wraps(tool_fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                res = await tool_fn(*args, **kwargs)
                dur = (time.perf_counter() - start) * 1000
                _record_call(tool_name, args, kwargs, res, None, dur, trajectory)
                return res
            except Exception as exc:
                dur = (time.perf_counter() - start) * 1000
                _record_call(tool_name, args, kwargs, None, str(exc), dur, trajectory)
                raise

        return async_wrapper
    else:

        @functools.wraps(tool_fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                res = tool_fn(*args, **kwargs)
                dur = (time.perf_counter() - start) * 1000
                _record_call(tool_name, args, kwargs, res, None, dur, trajectory)
                return res
            except Exception as exc:
                dur = (time.perf_counter() - start) * 1000
                _record_call(tool_name, args, kwargs, None, str(exc), dur, trajectory)
                raise

        return sync_wrapper


def _record_call(
    name: str,
    args: tuple,
    kwargs: dict,
    result: Any,
    error: str | None,
    duration_ms: float,
    trajectory: Trajectory,
) -> None:
    combined_args: dict[str, Any] = dict(kwargs)
    if args:
        combined_args["_positional_args"] = [str(a) for a in args]

    if name in ("start_subagent", "invoke_subagent"):
        sub_name = kwargs.get("name") or (str(args[0]) if args else "subagent")
        sub_prompt = kwargs.get("prompt") or (str(args[1]) if len(args) > 1 else "")
        trajectory.record_subagent_call(
            name=str(sub_name),
            prompt=str(sub_prompt),
            args=combined_args,
            result=result,
            duration_ms=duration_ms,
        )

    trajectory.record_tool_call(
        name=name,
        args=combined_args,
        result=result,
        error=error,
        duration_ms=duration_ms,
    )


class MockAgentAdapter(AgentAdapter):
    """Deterministic mock agent adapter for testing the framework without live LLM calls."""

    def __init__(self, action_script: Callable[[Path, Trajectory], None] | None = None):
        self.action_script = action_script

    async def run(
        self,
        prompt: str,
        workspace_dir: Path,
        trajectory: Trajectory,
        timeout_seconds: float = 180.0,
    ) -> str:
        trajectory.record_thought(f"Processing user request: '{prompt}'")

        if self.action_script:
            self.action_script(workspace_dir, trajectory)
        else:
            # Default mock behavior: simulate reading, writing, and checking
            trajectory.record_thought("Reading workspace structure...")
            trajectory.record_tool_call(
                name="mlg_structure",
                args={},
                result="{}",
                duration_ms=12.5,
            )

            target_file = workspace_dir / "content" / "example.mlg"
            if target_file.exists():
                trajectory.record_thought("Editing existing file...")
                content = target_file.read_text(encoding="utf-8")
                new_content = content + "\n\n# Mock edited content"
                target_file.write_text(new_content, encoding="utf-8")
                trajectory.record_tool_call(
                    name="write_content_file",
                    args={"file_path": "content/example.mlg"},
                    result="Updated file",
                    duration_ms=8.0,
                )

            trajectory.record_thought("Running mlg check...")
            trajectory.record_tool_call(
                name="mlg_check",
                args={"paths": None},
                result="Clean check: 0 errors",
                duration_ms=45.0,
            )

        trajectory.final_output = "Task completed successfully."
        return trajectory.final_output


class SimulatedAgentAdapter(AgentAdapter):
    """Simulates realistic agent behavior on standard golden test cases.

    Demonstrates authoring, editing, and deleting Mathlingua content while
    accurately invoking tools and updating files.
    """

    async def run(
        self,
        prompt: str,
        workspace_dir: Path,
        trajectory: Trajectory,
        timeout_seconds: float = 180.0,
    ) -> str:
        prompt_lower = prompt.lower()

        # 1. Authoring new group definition (Case 1)
        if "01_monoids.mlg" in prompt:
            trajectory.record_thought("Inspecting content/07_algebra/01_monoids.mlg to locate target item.")
            rel_file = "content/07_algebra/01_monoids.mlg"
            target = workspace_dir / rel_file
            content = target.read_text(encoding="utf-8")

            trajectory.record_tool_call(
                name="find_item_by_id",
                args={"item_id": "e4d7371d-29bd-431f-ab09-e114fe89e5cf", "file_path": rel_file},
                result=f"Found item 'e4d7371d-29bd-431f-ab09-e114fe89e5cf' in {rel_file}",
                duration_ms=15.0,
            )

            trajectory.record_thought("Formulating new Mathlingua code for [\\group.abelian] and inserting.")
            new_item = "\n\n\n[\\group.abelian]\nDeclares: A is \\group\nDocumented:\n. called: \"abelian group\"\n"
            target.write_text(content.strip() + new_item, encoding="utf-8")

            trajectory.record_tool_call(
                name="insert_item_after",
                args={
                    "file_path": rel_file,
                    "after_id": "e4d7371d-29bd-431f-ab09-e114fe89e5cf",
                    "new_item_content": new_item.strip(),
                },
                result=f"Successfully inserted content after item 'e4d7371d-29bd-431f-ab09-e114fe89e5cf' in {rel_file}",
                duration_ms=25.0,
            )

            trajectory.record_thought("Running mlg check to validate collection syntax.")
            subprocess.run(["mlg", "check"], cwd=str(workspace_dir), capture_output=True, text=True)
            trajectory.record_tool_call(
                name="mlg_check",
                args={"paths": [rel_file]},
                result="Clean check: 0 errors across 1 file(s).",
                duration_ms=65.0,
            )

            trajectory.final_output = "Successfully authored \\group.abelian in 01_monoids.mlg."
            return trajectory.final_output

        # 2. Editing existing incomplete theorem (Case 2)
        elif "rings.mlg" in prompt:
            rel_file = "content/07_algebra/rings.mlg"
            target = workspace_dir / rel_file
            content = target.read_text(encoding="utf-8")

            trajectory.record_thought("Locating item 'aaaa0002-bbbb-cccc-dddd-eeeeffff0002' to fix incomplete theorem.")
            trajectory.record_tool_call(
                name="find_item_by_id",
                args={"item_id": "aaaa0002-bbbb-cccc-dddd-eeeeffff0002", "file_path": rel_file},
                result="Found item with placeholder TODO_INCOMPLETE_THEOREM",
                duration_ms=12.0,
            )

            trajectory.record_thought("Replacing incomplete theorem with valid clauses.")
            replacement = (
                "Theorem:\n"
                "given: R is \\ring\n"
                "then:\n"
                ". R is? \\ring\n"
                "Documented:\n"
                ". called: \"Ring reflexivity\"\n"
                "Id: \"aaaa0002-bbbb-cccc-dddd-eeeeffff0002\""
            )
            old_snippet = (
                "Theorem:\n"
                "given: R is \\ring\n"
                "then:\n"
                ". TODO_INCOMPLETE_THEOREM\n"
                "Documented:\n"
                ". called: \"Incomplete theorem\"\n"
                "Id: \"aaaa0002-bbbb-cccc-dddd-eeeeffff0002\""
            )
            updated = content.replace(old_snippet, replacement)
            target.write_text(updated.strip() + "\n", encoding="utf-8")

            trajectory.record_tool_call(
                name="replace_item_by_id",
                args={
                    "file_path": rel_file,
                    "item_id": "aaaa0002-bbbb-cccc-dddd-eeeeffff0002",
                    "new_item_content": replacement,
                },
                result="Successfully replaced item",
                duration_ms=20.0,
            )

            trajectory.record_thought("Running mlg check to verify collection syntax.")
            subprocess.run(["mlg", "check"], cwd=str(workspace_dir), capture_output=True, text=True)
            trajectory.record_tool_call(
                name="mlg_check",
                args={"paths": [rel_file]},
                result="Clean check: 0 errors",
                duration_ms=60.0,
            )

            trajectory.final_output = "Successfully updated Theorem in rings.mlg."
            return trajectory.final_output

        # 3. Deleting obsolete axiom and file (Case 3)
        elif "axioms.mlg" in prompt or "delete" in prompt_lower:
            rel_file = "content/01_logic/axioms.mlg"
            target = workspace_dir / rel_file
            content = target.read_text(encoding="utf-8")

            trajectory.record_thought("Removing obsolete axiom from axioms.mlg.")
            items = content.split("\n\n\n")
            cleaned_items = [
                it for it in items
                if "99999999-9999-9999-9999-999999999999" not in it and "OBSOLETE" not in it
            ]
            target.write_text("\n\n\n".join(cleaned_items).strip() + "\n", encoding="utf-8")

            trajectory.record_tool_call(
                name="write_content_file",
                args={"file_path": rel_file, "content": "..."},
                result="Updated axioms.mlg without obsolete axiom",
                duration_ms=18.0,
            )

            # Delete obsolete file
            del_file = workspace_dir / "content" / "01_logic" / "obsolete.mlg"
            if del_file.exists():
                del_file.unlink()
                trajectory.record_thought("Deleted obsolete file content/01_logic/obsolete.mlg.")

            trajectory.record_thought("Running mlg check to verify.")
            subprocess.run(["mlg", "check"], cwd=str(workspace_dir), capture_output=True, text=True)
            trajectory.record_tool_call(
                name="mlg_check",
                args={"paths": None},
                result="Clean check: 0 errors",
                duration_ms=50.0,
            )

            trajectory.final_output = "Successfully cleaned up obsolete axiom and removed obsolete file."
            return trajectory.final_output

        trajectory.final_output = "Completed generic actions."
        return trajectory.final_output


class MathloreForgeAgentAdapter(AgentAdapter):
    """Adapter for testing the Mathlore Forge agent directly."""

    def __init__(
        self,
        model: str | None = None,
        skills_dir: Path | str | None = None,
    ):
        self.model = model
        self.skills_dir = Path(skills_dir).resolve() if skills_dir else None

    async def run(
        self,
        prompt: str,
        workspace_dir: Path,
        trajectory: Trajectory,
        timeout_seconds: float = 180.0,
    ) -> str:
        toolkit = MathlinguaToolkit(content_root=workspace_dir)
        raw_tools = toolkit.get_tools()
        wrapped_tools = [_wrap_tool_for_trajectory(t, trajectory) for t in raw_tools]

        # Antigravity hooks if available
        hooks_list = []
        try:
            from google.antigravity.hooks import hooks as ag_hooks
            from google.antigravity import types as ag_types

            @ag_hooks.pre_tool_call_decide
            async def on_pre_tool(data: ag_types.ToolCall) -> ag_types.HookResult:
                tool_name = str(data.name)
                args = data.args or {}
                if tool_name in ("start_subagent", "invoke_subagent"):
                    sub_name = args.get("name", "subagent")
                    sub_prompt = args.get("prompt", "")
                    trajectory.record_subagent_call(name=str(sub_name), prompt=str(sub_prompt), args=args)
                return ag_types.HookResult(allow=True)

            hooks_list.append(on_pre_tool)
        except Exception:
            pass

        # Build agent using mathlore-forge's create_mathlingua_agent
        agent = create_mathlingua_agent(
            content_root=workspace_dir,
            skills_dir=self.skills_dir,
            model=self.model,
            extra_tools=[],
            hooks=hooks_list if hooks_list else None,
        )

        if hasattr(agent, "config") and hasattr(agent.config, "tools"):
            agent.config.tools = wrapped_tools

        start_turn = time.perf_counter()
        try:
            async with agent:
                resp = await asyncio.wait_for(agent.chat(prompt), timeout=timeout_seconds)

                if hasattr(resp, "thoughts"):
                    thought_buf = []
                    async for thought in resp.thoughts:
                        thought_buf.append(thought)
                    if thought_buf:
                        trajectory.record_thought("".join(thought_buf))

                if hasattr(resp, "text"):
                    final_text = await resp.text()
                else:
                    tokens = []
                    async for tok in resp:
                        tokens.append(tok)
                    final_text = "".join(tokens)

                trajectory.final_output = final_text
                return final_text
        finally:
            trajectory.total_duration_seconds = time.perf_counter() - start_turn


class CustomCallableAdapter(AgentAdapter):
    """Adapter for arbitrary python callables fn(prompt, workspace_dir, trajectory) -> str."""

    def __init__(self, target_callable: Callable[..., Any]):
        self.callable = target_callable

    async def run(
        self,
        prompt: str,
        workspace_dir: Path,
        trajectory: Trajectory,
        timeout_seconds: float = 180.0,
    ) -> str:
        start = time.perf_counter()
        sig = inspect.signature(self.callable)
        params = list(sig.parameters.keys())

        kwargs = {}
        if "trajectory" in params:
            kwargs["trajectory"] = trajectory

        if inspect.iscoroutinefunction(self.callable):
            coro = self.callable(prompt, workspace_dir, **kwargs)
            res = await asyncio.wait_for(coro, timeout=timeout_seconds)
        else:
            res = self.callable(prompt, workspace_dir, **kwargs)

        trajectory.total_duration_seconds = time.perf_counter() - start
        trajectory.final_output = str(res)
        return trajectory.final_output


class TestRunner:
    """Orchestrates golden test execution in sandboxed sessions."""

    __test__ = False

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        evaluator: Evaluator | None = None,
        default_adapter: AgentAdapter | None = None,
    ):
        self.session_manager = session_manager or SessionManager()
        self.evaluator = evaluator or Evaluator()
        self.default_adapter = default_adapter or MathloreForgeAgentAdapter()

    async def run_test(
        self,
        test_case: GoldenTestCase,
        adapter: AgentAdapter | None = None,
        auto_cleanup: bool = False,
        keep_on_failure: bool = True,
    ) -> tuple[Session, EvaluationReport]:
        """Executes a single golden test case in an isolated session."""
        active_adapter = adapter or self.default_adapter
        session = self.session_manager.create_session(test_case.id, test_case.name)

        start_time = time.perf_counter()
        trajectory = Trajectory()
        error_message: str | None = None

        # 1. Setup workspace sandbox with scaffold
        workspace_dir = session.sandbox.setup(
            scaffold=test_case.scaffold,
            base_dir=test_case.base_dir,
        )

        # 2. Run the agent
        status = "FAILED"
        report: EvaluationReport | None = None

        try:
            await active_adapter.run(
                prompt=test_case.prompt,
                workspace_dir=workspace_dir,
                trajectory=trajectory,
                timeout_seconds=test_case.timeout_seconds,
            )
        except Exception as e:
            error_message = f"Agent execution error: {e}"
            status = "ERROR"

        duration = time.perf_counter() - start_time
        trajectory.total_duration_seconds = duration

        # 3. Compute file changes & diff
        diff = session.sandbox.compute_changes()

        # Save diff to changes.diff
        diff_file = session.session_dir / "changes.diff"
        diff_file.write_text(diff.unified_diff, encoding="utf-8")

        # 4. Save trajectory files
        trajectory.save_json(session.session_dir / "trajectory.json")
        trajectory.save_markdown(session.session_dir / "trajectory.md")

        # 5. Evaluate results
        if status != "ERROR":
            report = self.evaluator.evaluate(
                test_case=test_case,
                workspace_dir=workspace_dir,
                diff=diff,
                trajectory=trajectory,
            )
            status = "PASSED" if report.passed else "FAILED"
        else:
            report = EvaluationReport(
                test_id=test_case.id,
                test_name=test_case.name,
                passed=False,
                summary=f"ERROR: {error_message}",
                failure_messages=[str(error_message)],
            )

        # Save report
        report.save_json(session.session_dir / "report.json")

        # 6. Finish session
        session.finish(
            status=status,
            duration_seconds=duration,
            error_message=error_message,
            created_files=diff.created_files,
            modified_files=diff.modified_files,
            deleted_files=diff.deleted_files,
        )

        # 7. Auto-cleanup if requested
        should_clean = auto_cleanup and (not keep_on_failure or status == "PASSED")
        if should_clean:
            session.sandbox.cleanup()
            session.meta.auto_cleaned = True
            session.save_meta()

        return session, report
