"""End-to-end unit tests for TestRunner."""

import asyncio
from pathlib import Path
from mathlore_forge.goldens.models import (
    CompilerExpectation,
    Expectations,
    FileExpectation,
    GoldenTestCase,
    ScaffoldConfig,
    ToolCallExpectation,
    TrajectoryExpectations,
)
from mathlore_forge.goldens.runner import MockAgentAdapter, TestRunner
from mathlore_forge.goldens.session import SessionManager
from mathlore_forge.goldens.trajectory import Trajectory


def test_runner_with_mock_agent(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    session_mgr = SessionManager(runs_dir=runs_dir)

    def mock_script(workspace: Path, traj: Trajectory):
        target = workspace / "content" / "algebra.mlg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(r"[\group]" + "\nDefines: G\n", encoding="utf-8")
        traj.record_tool_call(
            name="write_content_file",
            args={"file_path": "content/algebra.mlg"},
            result="Success",
            duration_ms=10.0,
        )

    adapter = MockAgentAdapter(action_script=mock_script)
    runner = TestRunner(session_manager=session_mgr)

    test_case = GoldenTestCase(
        id="test-mock-run",
        name="Mock Test Run",
        prompt="Write algebra group",
        scaffold=ScaffoldConfig(
            files={"notes.txt": "Notes"},
            include_default_mlg_json=False,
        ),
        expectations=Expectations(
            compiler=CompilerExpectation(enabled=False),
            files_created=["content/algebra.mlg"],
            file_assertions=[
                FileExpectation(path="content/algebra.mlg", contains=["Defines: G"])
            ],
            trajectory=TrajectoryExpectations(
                tools=[ToolCallExpectation(name="write_content_file", must_call=True)]
            ),
        ),
    )

    session, report = asyncio.run(runner.run_test(test_case, adapter=adapter))

    assert session.meta.session_id == "session-1"
    assert session.meta.status == "PASSED"
    assert report.passed is True
    assert (Path(session.meta.session_dir) / "trajectory.json").exists()
    assert (Path(session.meta.session_dir) / "trajectory.md").exists()
    assert (Path(session.meta.session_dir) / "changes.diff").exists()
    assert (Path(session.meta.session_dir) / "report.json").exists()
    assert (Path(session.meta.workspace_dir) / "content" / "algebra.mlg").exists()
