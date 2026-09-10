"""Tests for DBOS workflow steps and durability."""

from pathlib import Path
from mathlore_forge.config import AppConfig
from mathlore_forge.workflows.cycle import (
    dbos_step_0_sync_layout,
    dbos_step_8_persist_todo,
    dbos_step_record_golden,
    dbos_step_verify_collection,
)
from mathlore_forge.db.store import MathloreStore


def test_dbos_step_0_sync_layout(tmp_path: Path):
    cfg = AppConfig.load()
    cfg.dbos_system_database_url = f"sqlite:///{tmp_path / 'dbos_test.sqlite'}"
    cfg.paths.db_path = str(tmp_path / "dbos_test.sqlite")

    result = dbos_step_0_sync_layout(cfg.model_dump())
    assert result["title"] == "Mathlore"
    assert result["directories_count"] > 0
    assert result["files_count"] > 0
    assert result["sections_count"] > 0


def test_dbos_step_8_persist_todo(tmp_path: Path):
    cfg = AppConfig.load()
    cfg.dbos_system_database_url = f"sqlite:///{tmp_path / 'dbos_test.sqlite'}"
    cfg.paths.db_path = str(tmp_path / "dbos_test.sqlite")

    detailed_plan = {
        "summary": "Plan for partial order properties",
        "items": [
            {
                "id": "todo-step-1",
                "section_path": "content/02_relations.mlg",
                "title": "Antisymmetric Relation",
                "kind": "Defines",
                "purpose": "Define antisymmetry of relations",
                "what_to_cover": "If x R y and y R x then x = y",
                "citations": [{"author": "Halmos", "title": "Naive Set Theory"}],
            }
        ],
    }

    item_ids = dbos_step_8_persist_todo(cfg.model_dump(), detailed_plan, "test_cycle")
    assert item_ids == ["todo-step-1"]

    store = MathloreStore(cfg.dbos_system_database_url)
    todos = store.get_todo_items(iteration_id="test_cycle")
    assert len(todos) == 1
    assert todos[0].title == "Antisymmetric Relation"


def test_dbos_step_record_golden_and_verify(tmp_path: Path):
    cfg = AppConfig.load()
    cfg.dbos_system_database_url = f"sqlite:///{tmp_path / 'dbos_test.sqlite'}"
    cfg.paths.db_path = str(tmp_path / "dbos_test.sqlite")
    cfg.paths.goldens_dir = tmp_path / "goldens"

    golden_id = dbos_step_record_golden(
        cfg.model_dump(),
        "iter_123",
        "Define strict partial order",
        "Introduce irreflexive and transitive relations",
        "Defines: \\strict.partial.order ...",
    )
    assert golden_id.startswith("golden_")

    verified = dbos_step_verify_collection(cfg.model_dump())
    assert verified is True


def test_prompt_user_decision_approval(monkeypatch):
    from mathlore_forge.workflows.cycle import _prompt_user_decision
    from rich.prompt import Prompt

    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "y")
    approved, fb, switch_auto = _prompt_user_decision("Approve?")
    assert approved is True
    assert fb == ""
    assert switch_auto is False

    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "yes")
    approved, fb, switch_auto = _prompt_user_decision("Approve?")
    assert approved is True
    assert switch_auto is False


def test_prompt_user_decision_auto_modes(monkeypatch):
    from mathlore_forge.workflows.cycle import _prompt_user_decision
    from rich.prompt import Prompt

    for auto_input in ["a", "auto", "all", "yes to all", "yall", "run on auto", "ok run on auto now"]:
        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: auto_input)
        approved, fb, switch_auto = _prompt_user_decision("Approve?")
        assert approved is True
        assert fb == ""
        assert switch_auto is True


def test_prompt_user_decision_feedback(monkeypatch):
    from mathlore_forge.workflows.cycle import _prompt_user_decision
    from rich.prompt import Prompt

    # Testing prompt flow when selecting 'f' then entering feedback
    calls = ["f", "add more theorems"]
    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: calls.pop(0))
    approved, fb, switch_auto = _prompt_user_decision("Approve?")
    assert approved is False
    assert fb == "add more theorems"
    assert switch_auto is False

    # Testing direct critique typed at prompt
    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "tighten definition conditions")
    approved, fb, switch_auto = _prompt_user_decision("Approve?")
    assert approved is False
    assert fb == "tighten definition conditions"
    assert switch_auto is False

