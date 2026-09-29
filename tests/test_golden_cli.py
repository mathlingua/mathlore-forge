"""Unit tests for the mlg-golden CLI."""

from pathlib import Path
from typer.testing import CliRunner
from mathlore_forge.goldens.cli import app

runner = CliRunner()


def test_cli_list_tests(tmp_path: Path):
    result = runner.invoke(app, ["tests", "--tests-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No golden test cases found" in result.stdout


def test_cli_new_test_scaffolding(tmp_path: Path):
    result = runner.invoke(app, ["new", "my-new-test", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    test_dir = tmp_path / "my-new-test"
    assert test_dir.is_dir()
    assert (test_dir / "test.yaml").is_file()
    assert (test_dir / "scaffold" / "mlg.json").is_file()
    assert (test_dir / "scaffold" / "content" / "math.mlg").is_file()


def test_cli_runs_and_clean(tmp_path: Path):
    # Runs on empty directory
    result = runner.invoke(app, ["runs", "--runs-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No sessions found" in result.stdout

    # Clean with no options
    result = runner.invoke(app, ["clean", "--runs-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Specify --all" in result.stdout
