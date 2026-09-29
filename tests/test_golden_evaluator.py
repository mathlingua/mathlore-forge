"""Unit tests for Evaluator and trajectory assertions."""

from pathlib import Path
from mathlore_forge.goldens.evaluator import Evaluator
from mathlore_forge.goldens.models import (
    CompilerExpectation,
    Expectations,
    FileExpectation,
    GoldenTestCase,
    SubagentExpectation,
    ToolCallExpectation,
    TrajectoryExpectations,
)
from mathlore_forge.goldens.sandbox import FileDiffSummary
from mathlore_forge.goldens.trajectory import Trajectory


def test_evaluator_assertions(tmp_path: Path):
    evaluator = Evaluator()

    # Create dummy workspace file
    doc_path = tmp_path / "content" / "doc.mlg"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(r"[\group]" + "\nDefines: G\nDocumented:\n. called: 'group'\n", encoding="utf-8")

    # Setup trajectory
    trajectory = Trajectory()
    trajectory.record_tool_call(name="find_item_by_id", args={"item_id": "abc"})
    trajectory.record_tool_call(name="insert_item_after", args={"after_id": "abc", "content": "Defines: G"})
    trajectory.record_subagent_call(name="prose_writer", prompt="Write description")

    test_case = GoldenTestCase(
        id="test-eval",
        name="Test Evaluation",
        prompt="Insert group",
        expectations=Expectations(
            compiler=CompilerExpectation(enabled=False),  # Skip live compiler check in this unit test
            files_modified=["content/doc.mlg"],
            file_assertions=[
                FileExpectation(
                    path="content/doc.mlg",
                    contains=[r"[\group]", "Defines: G"],
                    not_contains=["TODO"],
                )
            ],
            trajectory=TrajectoryExpectations(
                tools=[
                    ToolCallExpectation(name="insert_item_after", must_call=True),
                ],
                forbidden_tools=["delete_everything"],
                subagents=[
                    SubagentExpectation(name="prose_writer", must_run=True),
                ],
                forbidden_subagents=["rogue_subagent"],
            ),
        ),
    )

    diff = FileDiffSummary(
        created_files=[],
        modified_files=["content/doc.mlg"],
        deleted_files=[],
        unified_diff="+Defines: G",
    )

    report = evaluator.evaluate(test_case, tmp_path, diff, trajectory)
    assert report.passed is True
    assert len(report.failure_messages) == 0
