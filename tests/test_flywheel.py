"""Tests for FeedbackLearner and GoldenManager."""

from pathlib import Path
from mathlore_forge.db.schema import PhaseType
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.flywheel.goldens import GoldenManager
from mathlore_forge.flywheel.learner import FeedbackLearner


def test_flywheel_feedback_learner(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    store = MathloreStore(f"sqlite:///{db_file}")
    flywheel_dir = tmp_path / "flywheel"
    skills_dir = tmp_path / "skills"

    learner = FeedbackLearner(store, flywheel_dir, skills_dir)
    learner.process_feedback(
        iteration_id="test_iter",
        phase=PhaseType.HIGH_LEVEL_PLAN,
        user_feedback="Ensure all set operations have explicit domains.",
        context_summary="Review of set union",
    )

    rules = store.get_learned_rules(phase=PhaseType.HIGH_LEVEL_PLAN)
    assert len(rules) == 1
    assert "explicit domains" in rules[0]

    # Verify skill file updated
    skill_file = skills_dir / "mathlore-learned-guidelines" / "SKILL.md"
    assert skill_file.exists()
    assert "explicit domains" in skill_file.read_text(encoding="utf-8")


def test_golden_manager(tmp_path: Path):
    db_file = tmp_path / "test.sqlite"
    store = MathloreStore(f"sqlite:///{db_file}")
    goldens_dir = tmp_path / "goldens"

    gm = GoldenManager(store, goldens_dir)
    rec = gm.record_golden(
        session_id="session_123",
        name="Test Golden Case",
        prompt="Define partial order",
        plan_summary="Add reflexivity, antisymmetry, and transitivity",
        expected_symbols=["\\partial.order"],
        generated_source="Defines: \\partial.order on X ...",
        citations=["Halmos, Naive Set Theory"],
    )

    assert rec.id.startswith("golden_")
    goldens = store.get_goldens()
    assert len(goldens) == 1
    assert goldens[0].name == "Test Golden Case"
