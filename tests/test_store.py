"""Tests for MathloreStore database models and operations."""

from pathlib import Path
from mathlore_forge.db.schema import (
    FeedbackRecord,
    GapRecord,
    PhaseType,
    TodoItemRecord,
    TodoStatus,
)
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.mlg.client import CollectionStructure, DirectoryStructure, FileStructure, ItemStructure


def test_store_init_and_sync(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    store = MathloreStore(f"sqlite:///{db_file}")

    mock_structure = CollectionStructure(
        title="Test Collection",
        directories=[
            DirectoryStructure(path="content/00_test", title="Test Chapter", has_preface=False)
        ],
        files=[
            FileStructure(
                path="content/00_test/00_test.mlg",
                title="Test File",
                items=[ItemStructure(id="item-1", kind="Defines", heading="Test Def", definition_keys=["\\test"])],
            )
        ],
    )

    sections = store.sync_from_collection_structure(mock_structure)
    assert len(sections) == 2

    retrieved = store.get_sections()
    assert len(retrieved) == 2
    file_sec = next(s for s in retrieved if not s.is_directory)
    assert file_sec.defined_commands == ["\\test"]


def test_store_todo_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    store = MathloreStore(f"sqlite:///{db_file}")

    item = TodoItemRecord(
        id="item-test-1",
        iteration_id="cycle_1",
        section_path="content/00_test/00_test.mlg",
        title="Equivalence Relation",
        kind="Defines",
        purpose="Define equivalence relations",
        what_to_cover="reflexivity, symmetry, transitivity",
        citations=[{"author": "Halmos", "title": "Naive Set Theory"}],
    )
    store.add_todo_items([item])

    todos = store.get_todo_items(iteration_id="cycle_1", status=TodoStatus.TODO)
    assert len(todos) == 1
    assert todos[0].title == "Equivalence Relation"

    store.update_todo_status("item-test-1", TodoStatus.DONE, source_code="Defines: ...")
    done_items = store.get_todo_items(status=TodoStatus.DONE)
    assert len(done_items) == 1
    assert done_items[0].source_code == "Defines: ..."


def test_store_feedback_and_gaps(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    store = MathloreStore(f"sqlite:///{db_file}")

    fb = FeedbackRecord(
        iteration_id="cycle_1",
        phase=PhaseType.HIGH_LEVEL_PLAN,
        user_feedback="Make sure to cover partial orders first.",
        learned_rule="[PLANNING] Always cover partial orders before lattices.",
    )
    store.add_feedback(fb)

    rules = store.get_learned_rules()
    assert len(rules) == 1
    assert "partial orders" in rules[0]

    gap = GapRecord(
        item_id="item-test-1",
        concept="Grothendieck Universe",
        description="Mathlingua currently lacks syntax for higher universes.",
    )
    store.record_gap(gap)
    unresolved = store.get_unresolved_gaps()
    assert len(unresolved) == 1
    assert unresolved[0].concept == "Grothendieck Universe"
