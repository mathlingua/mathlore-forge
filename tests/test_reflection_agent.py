"""Tests for the Reflection Agent and Flywheel learning."""

from pathlib import Path
import tempfile
import yaml

from mathlore_forge.agents.reflection_agent import ReflectionAgent


def test_apply_learning_to_forge():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)

        # Scaffold mock forge directory structure
        skills_dir = root / "skills" / "mathlore-learned-guidelines"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skills_dir / "SKILL.md"
        skill_file.write_text("# Learned Guidelines\n\n1. Initial rule\n", encoding="utf-8")

        golden_dir = root / "golden_tests"
        golden_dir.mkdir(parents=True, exist_ok=True)

        learning = {
            "rule_tag": "PRECONDITIONS_WHEN",
            "guideline_text": "Always put preconditions inside when: rather than satisfies:.",
            "golden_test_id": "04_test_preconditions",
            "golden_test_name": "Test Preconditions Rule",
            "golden_test_description": "Verifies when: is used for assumptions",
            "prompt": "Define a normed division ring",
            "target_file": "content/07_algebra/03_rings.mlg",
        }

        agent = ReflectionAgent()
        modified = agent.apply_learning_to_forge(root, learning)

        # Verify SKILL.md was updated
        updated_skill = skill_file.read_text(encoding="utf-8")
        assert "PRECONDITIONS_WHEN" in updated_skill
        assert "Always put preconditions inside when:" in updated_skill

        # Verify golden test was synthesized
        test_yaml = root / "golden_tests" / "04_test_preconditions" / "test.yaml"
        assert test_yaml.is_file()

        with open(test_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["id"] == "04_test_preconditions"
        assert data["name"] == "Test Preconditions Rule"
        assert "flywheel" in data["tags"]
