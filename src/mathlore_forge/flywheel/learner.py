"""Synthesizes user feedback into learned rules and updates skill guidelines."""

import json
from pathlib import Path
from typing import Any
from mathlore_forge.db.schema import FeedbackRecord, PhaseType
from mathlore_forge.db.store import MathloreStore


class FeedbackLearner:
    """Extracts lessons from user feedback and maintains the continuous improvement flywheel."""

    def __init__(self, store: MathloreStore, flywheel_dir: Path | str = "./flywheel", skills_dir: Path | str = "./skills"):
        self.store = store
        self.flywheel_dir = Path(flywheel_dir)
        self.skills_dir = Path(skills_dir)
        self.flywheel_dir.mkdir(parents=True, exist_ok=True)
        self.rules_file = self.flywheel_dir / "rules.json"

        # Create dynamic learned rules skill directory
        self.learned_skill_dir = self.skills_dir / "mathlore-learned-guidelines"
        self.learned_skill_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_skill_manifest()

    def _ensure_skill_manifest(self) -> None:
        skill_md = self.learned_skill_dir / "SKILL.md"
        if not skill_md.exists():
            skill_md.write_text(
                "---\n"
                "name: mathlore-learned-guidelines\n"
                "description: Continuously improved rules, preferences, and guidelines learned from user feedback across planning and authoring sessions.\n"
                "---\n\n"
                "# Learned Mathlore Guidelines\n\n"
                "These guidelines reflect corrections and style preferences accumulated from user interactions.\n",
                encoding="utf-8",
            )

    def process_feedback(
        self,
        iteration_id: str,
        phase: PhaseType,
        user_feedback: str,
        context_summary: str = "",
    ) -> FeedbackRecord:
        """Distills user feedback into a rule, records it in DB, and updates flywheel skills."""
        cleaned_feedback = user_feedback.strip()
        reflection = f"User critique in {phase.value}: '{cleaned_feedback}'. Context: {context_summary}"
        rule = f"[{phase.value.upper()}] {cleaned_feedback}"

        feedback_rec = FeedbackRecord(
            iteration_id=iteration_id,
            phase=phase,
            user_feedback=cleaned_feedback,
            agent_reflection=reflection,
            learned_rule=rule,
        )

        # Save to DB
        saved_rec = self.store.add_feedback(feedback_rec)

        # Update flywheel/rules.json
        self._append_rule_file(saved_rec)

        # Update dynamic skill file
        self._update_skill_doc()

        return saved_rec

    def _append_rule_file(self, rec: FeedbackRecord) -> None:
        rules_list: list[dict[str, Any]] = []
        if self.rules_file.exists():
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    rules_list = json.load(f)
            except Exception:
                rules_list = []

        rules_list.append({
            "id": rec.id,
            "iteration_id": rec.iteration_id,
            "phase": rec.phase.value,
            "user_feedback": rec.user_feedback,
            "learned_rule": rec.learned_rule,
            "created_at": rec.created_at.isoformat(),
        })

        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(rules_list, f, indent=2)

    def _update_skill_doc(self) -> None:
        """Regenerates the learned skill documentation with all active rules."""
        rules = self.store.get_learned_rules()
        skill_md = self.learned_skill_dir / "SKILL.md"

        content = (
            "---\n"
            "name: mathlore-learned-guidelines\n"
            "description: Continuously improved rules, preferences, and guidelines learned from user feedback across planning and authoring sessions.\n"
            "---\n\n"
            "# Learned Mathlore Guidelines\n\n"
            "The following rules were learned from past user feedback and must be adhered to:\n\n"
        )

        for idx, rule in enumerate(rules, 1):
            content += f"{idx}. {rule}\n"

        skill_md.write_text(content, encoding="utf-8")

    def get_prompt_context(self, phase: PhaseType | None = None) -> str:
        """Returns formatted string of learned rules for system prompt injection."""
        rules = self.store.get_learned_rules(phase=phase)
        if not rules:
            return ""

        lines = ["\n### Learned User Rules & Quality Guidelines:"]
        for r in rules[-10:]:  # Keep recent top 10 rules
            lines.append(f"- {r}")
        return "\n".join(lines)
