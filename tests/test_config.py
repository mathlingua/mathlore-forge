"""Tests for configuration management."""

from pathlib import Path
from mathlore_forge.config import AppConfig


def test_app_config_defaults(tmp_path: Path):
    cfg = AppConfig.load(tmp_path / "nonexistent.yaml")
    assert cfg.paths.db_path == "mathlore_forge.sqlite"
    assert cfg.execution.mode == "interactive"
    assert cfg.execution.max_iterations == 3
    assert cfg.guardrails.enforce_citations is True
    assert cfg.guardrails.flag_mathlingua_gaps is True


def test_env_overrides(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DBOS_SYSTEM_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")
    cfg = AppConfig.load(tmp_path / "nonexistent.yaml")
    assert cfg.dbos_system_database_url == "sqlite:///test.db"
    assert cfg.gemini_api_key == "test-key-12345"
