"""Reflection and self-improvement agent for the Mathlore Forge flywheel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence
import yaml

from google.antigravity import (
    Agent,
    AgentBehavior,
    CapabilitiesConfig,
    LocalAgentConfig,
    types,
)
from google.antigravity.hooks import policy

from mathlore_forge.config import MathloreConfig, load_config

REFLECTION_SYSTEM_INSTRUCTIONS = """\
You are an expert meta-learning and self-improvement agent for Mathlore Forge.
Your role is to analyze review comments made by the human mathematician Dominic Kramer, \
extract generalizable mathematical authoring rules, and formulate improvements for Mathlore Forge.

### Your Objectives:
1. **Rule Synthesis**: Extract concrete, actionable authoring guidelines from the review comments.
   - What went wrong or was suboptimal in the initial agent authoring?
   - How should future authoring turns avoid this mistake?
2. **Skill Update**: Formulate the addition to `skills/mathlore-learned-guidelines/SKILL.md`.
3. **Golden Test Synthesis**: Design a new golden test case (`test.yaml` and `scaffold/`) \
   that exercises this exact authoring scenario and verifies compliance.

Return your analysis in valid JSON matching this schema:
```json
{
  "rule_tag": "TAG_NAME",
  "guideline_text": "Clear rule description...",
  "golden_test_id": "04_descriptive_name",
  "golden_test_name": "Test Name",
  "golden_test_description": "Description of what this tests...",
  "prompt": "Prompt given to the authoring agent...",
  "expected_mlg_content": "Mathlingua snippet that satisfies the rule...",
  "target_file": "content/07_algebra/02_groups.mlg"
}
```
"""


class ReflectionAgent:
    """Agent that reflects on review feedback and synthesizes forge improvements."""

    def __init__(self, config: MathloreConfig | None = None):
        self.config = config or load_config()
        self.last_usage: Any = None
        self.last_conversation_id: str | None = None

    def create_agent(self) -> Agent:
        capabilities = CapabilitiesConfig(
            agent_behavior=AgentBehavior.AUTONOMOUS,
            enable_subagents=False,
        )
        agent_config = LocalAgentConfig(
            system_instructions=REFLECTION_SYSTEM_INSTRUCTIONS,
            model=self.config.models.reflection,
            capabilities=capabilities,
            policies=[policy.allow_all()],
        )
        return Agent(agent_config)

    async def analyze_feedback(self, comments: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Analyzes review comments and extracts structured learning points."""
        comments_json = json.dumps(list(comments), indent=2)
        prompt = (
            f"Here are the review comments left by Dominic Kramer on a recent Mathlore PR:\n\n"
            f"```json\n{comments_json}\n```\n\n"
            f"Please analyze these comments and synthesize a new learned guideline and a golden test case."
        )

        agent = self.create_agent()
        async with agent:
            response = await agent.chat(prompt)
            raw_text = await response.text()
            self.last_conversation_id = getattr(agent, "conversation_id", None)
            if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                self.last_usage = agent.conversation.total_usage

        # Parse JSON from response
        try:
            # Extract json code block if present
            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_str = raw_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = raw_text.strip()
            return json.loads(json_str)
        except Exception:
            # Fallback structure if LLM didn't format pure JSON
            return {
                "rule_tag": "LEARNED_RULE",
                "guideline_text": raw_text[:200].strip(),
                "golden_test_id": f"learned_{len(comments)}_rule",
                "golden_test_name": "Learned Guideline Test",
                "golden_test_description": "Auto-synthesized test from review feedback",
                "prompt": "Author the corrected mathlingua item adhering to feedback.",
                "expected_mlg_content": "",
                "target_file": "content/mathlore.mlg",
            }

    def apply_learning_to_forge(
        self,
        forge_root: Path | str,
        learning: dict[str, Any],
    ) -> list[Path]:
        """Applies the synthesized guideline to skills and creates a new golden test case."""
        forge_path = Path(forge_root).resolve()
        modified_files: list[Path] = []

        # 1. Update skills/mathlore-learned-guidelines/SKILL.md
        skill_file = forge_path / "skills" / "mathlore-learned-guidelines" / "SKILL.md"
        if skill_file.is_file():
            content = skill_file.read_text(encoding="utf-8")
            tag = learning.get("rule_tag", "GUIDELINE")
            text = learning.get("guideline_text", "")
            new_rule = f"\n- [{tag}] {text}\n"
            if text not in content:
                content += new_rule
                skill_file.write_text(content, encoding="utf-8")
                modified_files.append(skill_file)

        # 2. Synthesize new golden test case under golden_tests/
        test_id = learning.get("golden_test_id", "learned_test")
        test_dir = forge_path / "golden_tests" / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        scaffold_dir = test_dir / "scaffold"
        scaffold_dir.mkdir(parents=True, exist_ok=True)

        # Create test.yaml
        test_spec = {
            "id": test_id,
            "name": learning.get("golden_test_name", "Learned Rule Test"),
            "description": learning.get("golden_test_description", ""),
            "tags": ["flywheel", "learned"],
            "prompt": learning.get("prompt", ""),
            "scaffold": {
                "from_dir": "scaffold",
                "include_default_mlg_json": True,
            },
            "expectations": {
                "compiler": {"clean": True},
                "files_modified": [learning.get("target_file", "content/07_algebra/01_monoids.mlg")],
            },
        }

        test_yaml_path = test_dir / "test.yaml"
        with open(test_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(test_spec, f, sort_keys=False)
        modified_files.append(test_yaml_path)

        # Create minimal scaffold content file
        target_rel = learning.get("target_file", "content/07_algebra/01_monoids.mlg")
        scaffold_file = scaffold_dir / target_rel
        scaffold_file.parent.mkdir(parents=True, exist_ok=True)
        if not scaffold_file.exists():
            scaffold_file.write_text(
                r"[\monoid]" + "\n" + r"Defines: M" + "\n" + r"means: '\something'" + "\n\n",
                encoding="utf-8",
            )
            modified_files.append(scaffold_file)

        return modified_files
