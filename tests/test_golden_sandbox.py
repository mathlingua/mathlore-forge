"""Unit tests for sandbox isolation and unified diff computation."""

from pathlib import Path
from mathlore_forge.goldens.models import ScaffoldConfig
from mathlore_forge.goldens.sandbox import Sandbox


def test_sandbox_setup_and_diff(tmp_path: Path):
    sandbox = Sandbox(tmp_path)
    scaffold = ScaffoldConfig(
        files={
            "content/stay.mlg": "Original stay content\n",
            "content/edit.mlg": "Original line 1\nOriginal line 2\n",
            "content/del.mlg": "To be deleted\n",
        }
    )
    workspace = sandbox.setup(scaffold)
    assert (workspace / "content" / "stay.mlg").exists()

    # Modify workspace
    (workspace / "content" / "created.mlg").write_text("Newly created\n", encoding="utf-8")
    (workspace / "content" / "edit.mlg").write_text("Original line 1\nEdited line 2\n", encoding="utf-8")
    (workspace / "content" / "del.mlg").unlink()

    # Compute changes
    diff_summary = sandbox.compute_changes()
    assert diff_summary.created_files == ["content/created.mlg"]
    assert diff_summary.modified_files == ["content/edit.mlg"]
    assert diff_summary.deleted_files == ["content/del.mlg"]
    assert "+Edited line 2" in diff_summary.unified_diff
    assert "-Original line 2" in diff_summary.unified_diff
