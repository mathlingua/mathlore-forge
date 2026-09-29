"""Unit tests for golden test data models."""

from pathlib import Path
from mathlore_forge.goldens.models import (
    CompilerExpectation,
    Expectations,
    FileExpectation,
    GoldenTestCase,
    ScaffoldConfig,
    ToolCallExpectation,
)


def test_scaffold_materialize_inline(tmp_path: Path):
    scaffold = ScaffoldConfig(
        files={
            "content/test.mlg": "Title: Test",
            "notes/readme.txt": "Notes",
        },
        include_default_mlg_json=True,
    )
    scaffold.materialize(tmp_path)

    assert (tmp_path / "content" / "test.mlg").read_text() == "Title: Test"
    assert (tmp_path / "notes" / "readme.txt").read_text() == "Notes"
    assert (tmp_path / "mlg.json").exists()


def test_golden_test_case_validation():
    case = GoldenTestCase(
        id="test-01",
        name="Sample Test",
        prompt="Write something",
        expectations=Expectations(
            files_created=["content/new.mlg"],
            compiler=CompilerExpectation(clean=True),
        ),
    )
    assert case.id == "test-01"
    assert case.expectations.compiler.clean is True
    assert "content/new.mlg" in case.expectations.files_created
