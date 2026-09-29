"""Tests for Mathlingua Agent configuration and subagent creation."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from google.antigravity import Agent
from google.antigravity import types as agy_types

from mathlore_forge.agents.mathlingua_agent import (
    MathlinguaAgent,
    create_mathlingua_agent,
    create_mathlingua_subagent_config,
)


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.content_root = Path(self.tmpdir.name).resolve()
        # Create minimal structure for content root
        (self.content_root / "content").mkdir(parents=True, exist_ok=True)
        (self.content_root / "mlg.json").write_text('{"name": "TestMathlore"}', encoding="utf-8")

        # Clear env vars if set to ensure clean tests
        self._orig_root = os.environ.pop("MATHLINGUA_CONTENT_ROOT", None)
        self._orig_repo = os.environ.pop("MATHLORE_REPO", None)

    def tearDown(self):
        if self._orig_root:
            os.environ["MATHLINGUA_CONTENT_ROOT"] = self._orig_root
        if self._orig_repo:
            os.environ["MATHLORE_REPO"] = self._orig_repo
        self.tmpdir.cleanup()

    def test_missing_content_root_raises_error(self):
        """Verifies agent fails fast without searching the filesystem if content_root is omitted."""
        with self.assertRaises(ValueError) as ctx:
            create_mathlingua_agent(content_root=None)
        self.assertIn("content_root must be explicitly specified", str(ctx.exception))

    def test_create_mathlingua_agent(self):
        agent = create_mathlingua_agent(
            content_root=self.content_root,
            model="gemini-3.8-flash",
        )
        self.assertIsInstance(agent, Agent)

        # Inspect agent config
        cfg = agent._config
        self.assertIsNotNone(cfg)

        # 1. Tools verification: ensure mlg tooling and authoring tools are registered
        tool_names = [getattr(t, "__name__", str(t)) for t in cfg.tools]
        self.assertIn("run_mlg", tool_names)
        self.assertIn("mlg_check", tool_names)
        self.assertIn("mlg_structure", tool_names)
        self.assertIn("insert_item_after", tool_names)
        self.assertIn("read_content_file", tool_names)
        self.assertIn("write_content_file", tool_names)

        # 2. Skills paths verification
        self.assertTrue(len(cfg.skills_paths) > 0)
        # Check that mathlore-author-content skill is included
        skills_str = " ".join(cfg.skills_paths)
        self.assertIn("mathlore-author-content", skills_str)

        # 3. Workspaces verification: strictly restricted to content root
        self.assertEqual(cfg.workspaces, [str(self.content_root)])

    def test_create_subagent_config(self):
        sub_cfg = create_mathlingua_subagent_config(
            content_root=self.content_root,
            name="custom_math_author",
        )
        self.assertIsInstance(sub_cfg, agy_types.SubagentConfig)
        self.assertEqual(sub_cfg.name, "custom_math_author")
        self.assertIn("Mathlingua", sub_cfg.description)

        tool_names = [getattr(t, "__name__", str(t)) for t in sub_cfg.tools]
        self.assertIn("run_mlg", tool_names)
        self.assertIn("insert_item_after", tool_names)

    def test_mathlingua_agent_wrapper(self):
        math_agent = MathlinguaAgent(
            content_root=self.content_root,
        )
        self.assertEqual(math_agent.content_root, self.content_root)
        self.assertIsNotNone(math_agent.agent)
        self.assertIsNotNone(math_agent.toolkit)
        self.assertIsNotNone(math_agent.mlg_client)


if __name__ == "__main__":
    unittest.main()
