"""Tests for MlgClient interacting with mlg CLI."""

from mathlore_forge.config import AppConfig
from mathlore_forge.mlg.client import MlgClient


def test_mlg_client_check():
    cfg = AppConfig.load()
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    report = client.check()
    assert report.successful is True
    assert report.issue_count == 0


def test_mlg_client_structure():
    cfg = AppConfig.load()
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    structure = client.structure()
    assert structure.title == "Mathlore"
    assert len(structure.directories) > 0
    assert len(structure.files) > 0
    all_cmds = [cmd for f in structure.files for cmd in f.defined_commands]
    assert len(all_cmds) > 0
    assert any("\\set" in cmd for cmd in all_cmds)


def test_mlg_client_search():
    cfg = AppConfig.load()
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    search_rep = client.search("relation")
    assert search_rep.total_matches > 0
    assert len(search_rep.matches) > 0
